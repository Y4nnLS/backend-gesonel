#!/usr/bin/env python3
import os
import sys
import argparse
import hashlib
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import psycopg2
import psycopg2.extras

# ---------- Duração de áudio ----------
def get_wav_basic_info(path: Path) -> Tuple[Optional[float], Optional[int], Optional[int]]:
    import wave
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            ch = wf.getnchannels()
            dur = round(frames / float(rate), 3) if rate > 0 else None
            return dur, rate, ch
    except Exception:
        return None, None, None

def get_duration_generic(path: Path) -> Tuple[Optional[float], Optional[int], Optional[int]]:
    """
    Tenta detectar a duração/sample_rate/channels:
    - WAV: stdlib wave
    - Outros: se 'mutagen' estiver instalado, usa
    """
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return get_wav_basic_info(path)
    # Outros formatos
    try:
        from mutagen import File as MutagenFile  # type: ignore
        m = MutagenFile(str(path))
        if m is not None and getattr(m, "info", None):
            info = m.info
            dur = getattr(info, "length", None)
            sr = getattr(info, "sample_rate", None) or getattr(info, "sampleRate", None)
            ch = getattr(info, "channels", None)
            return (round(float(dur), 3) if dur is not None else None,
                    int(sr) if sr else None,
                    int(ch) if ch else None)
    except Exception:
        pass
    return None, None, None

# ---------- Hash ----------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

# ---------- DB ----------
CREATE_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS audio_file (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rel_path         TEXT NOT NULL,
  sha256           CHAR(64) UNIQUE,
  format           VARCHAR(8),
  duration_s       NUMERIC(8,3),
  sample_rate      INT,
  channels         INT,
  dataset          VARCHAR(64),
  speaker_id       VARCHAR(64),
  emotion_label    VARCHAR(32),
  split            VARCHAR(8),
  augment_pipeline TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audio_rel_path ON audio_file(rel_path);
CREATE INDEX IF NOT EXISTS ix_audio_dataset  ON audio_file(dataset);
CREATE INDEX IF NOT EXISTS ix_audio_label    ON audio_file(emotion_label);
"""

UPSERT_SQL = """
INSERT INTO audio_file
(rel_path, sha256, format, duration_s, sample_rate, channels, dataset, speaker_id, emotion_label, split, augment_pipeline)
VALUES (%(rel_path)s, %(sha256)s, %(format)s, %(duration_s)s, %(sample_rate)s, %(channels)s,
        %(dataset)s, %(speaker_id)s, %(emotion_label)s, %(split)s, %(augment_pipeline)s)
ON CONFLICT (sha256) DO UPDATE
SET rel_path = EXCLUDED.rel_path,
    format = COALESCE(EXCLUDED.format, audio_file.format),
    duration_s = COALESCE(EXCLUDED.duration_s, audio_file.duration_s),
    sample_rate = COALESCE(EXCLUDED.sample_rate, audio_file.sample_rate),
    channels = COALESCE(EXCLUDED.channels, audio_file.channels),
    dataset = COALESCE(EXCLUDED.dataset, audio_file.dataset),
    speaker_id = COALESCE(EXCLUDED.speaker_id, audio_file.speaker_id),
    emotion_label = COALESCE(EXCLUDED.emotion_label, audio_file.emotion_label),
    split = COALESCE(EXCLUDED.split, audio_file.split),
    augment_pipeline = COALESCE(EXCLUDED.augment_pipeline, audio_file.augment_pipeline)
RETURNING id;
"""

def connect_db(dsn: str):
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    return conn

# ---------- Varredura ----------
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aac", ".wma", ".aiff", ".aif"}

def iter_audio_files(root: Path, recursive: bool):
    if recursive:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
                yield p
    else:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
                yield p

def compute_rel_path(root: Path, file_path: Path) -> str:
    file_path = file_path.resolve()
    root = root.resolve()
    try:
        rel = str(file_path.relative_to(root))
    except ValueError:
        rel = file_path.name
    return rel.replace("\\", "/")

# ---------- Inferência por nome/caminho ----------
EMOTION_MAP = {
    # EN/PT comuns
    "angry": "angry", "raiva": "angry",
    "happy": "happy", "alegria": "happy",
    "sad": "sad", "tristeza": "sad",
    "neutral": "neutral", "neutro": "neutral",
    "fear": "fear", "medo": "fear",
    "disgust": "disgust", "nojo": "disgust",
    "surprise": "surprise", "surpresa": "surprise",
}

GENDER_MAP = {
    "m": "M", "male": "M", "masc": "M",
    "f": "F", "female": "F", "fem": "F",
}

LANG_MAP = {
    # normalizações úteis
    "pt": "pt", "ptbr": "pt-BR", "pt-br": "pt-BR",
    "en": "en", "eng": "en",
    "es": "es", "spa": "es",
    "fr": "fr", "fra": "fr",
    "de": "de", "ger": "de",
    "it": "it", "ita": "it",
}

# Ex.: ptFhappy_123_awgn+pitch.wav
#     <lang><gender><emotion>_<sid>_(<augment>)?
FNAME_RE = re.compile(
    r"""^(?P<prefix>(?P<lang>[A-Za-z\-]{2,5})(?P<gender>[A-Za-z])?(?P<emotion>[A-Za-z]+))
         _(?P<sid>[A-Za-z0-9\-]+)
         (?:_(?P<augment>[^.]+))?
         (?:\.[A-Za-z0-9]+)?$""",
    re.VERBOSE
)

def normalize_lang(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    v = val.lower()
    return LANG_MAP.get(v, v)

def normalize_gender(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    v = val.lower()
    return GENDER_MAP.get(v, v.upper())

def normalize_emotion(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    v = val.lower()
    return EMOTION_MAP.get(v, v)

def parse_filename(file_path: Path) -> Dict[str, Optional[str]]:
    name = file_path.name
    m = FNAME_RE.match(name)
    if not m:
        return {
            "language": None,
            "gender": None,
            "emotion": None,
            "speaker_id": None,
            "augment": None,
        }
    lang = normalize_lang(m.group("lang"))
    gender = normalize_gender(m.group("gender"))
    emotion = normalize_emotion(m.group("emotion"))
    sid = m.group("sid")
    augment = m.group("augment")
    return {
        "language": lang,
        "gender": gender,
        "emotion": emotion,
        "speaker_id": sid,
        "augment": augment,
    }

def infer_from_path(root: Path,
                    file_path: Path,
                    split_candidates=("train", "val", "test"),
                    augmented_folder_name="augmented") -> Dict[str, Optional[str]]:
    rel_parts = compute_rel_path(root, file_path).split("/")
    dataset = rel_parts[0] if rel_parts else None

    split = None
    for part in rel_parts:
        p = part.lower()
        if p in split_candidates:
            split = p
            break

    came_from_augmented = any(p.lower() == augmented_folder_name.lower() for p in rel_parts)
    return {
        "dataset": dataset,
        "split": split,
        "from_augmented": "1" if came_from_augmented else None,
    }

def build_aug_string(parsed: Dict[str, Optional[str]], from_path: Dict[str, Optional[str]], cli_augment: Optional[str]) -> Optional[str]:
    tags = []
    if parsed.get("language"):
        tags.append(f"lang={parsed['language']}")
    if parsed.get("gender"):
        tags.append(f"gender={parsed['gender']}")

    # Combina augment do sufixo do nome + info de pasta augmented + CLI
    aug_parts = []
    if parsed.get("augment"):
        aug_parts.append(parsed["augment"])
    if from_path.get("from_augmented"):
        aug_parts.append("augmented")
    if cli_augment:
        aug_parts.append(cli_augment)
    aug_parts = [p for p in aug_parts if p]
    if aug_parts:
        tags.append("aug=" + "+".join(dict.fromkeys(a.strip() for a in "+".join(aug_parts).split("+"))))
    return ";".join(tags) if tags else cli_augment

# ---------- CLI / Main ----------
def main():
    parser = argparse.ArgumentParser(
        description="Ingestão de arquivos de áudio no Postgres (salvando rel_path e metadados)."
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""),
                        help="DSN do Postgres. Ex: postgresql://user:pass@host:5432/db")
    parser.add_argument("--audio-root", required=True,
                        help="Diretório raiz onde ficam os áudios (para montar rel_path).")
    # Defaults fornecidos podem ser sobrescritos por inferência, se --infer-from-path
    parser.add_argument("--dataset", default=None, help="Nome do dataset padrão (opcional).")
    parser.add_argument("--emotion", default=None, help="Rótulo de emoção padrão (opcional).")
    parser.add_argument("--split", default=None, help="train/val/test (opcional).")
    parser.add_argument("--speaker", default=None, help="ID do falante padrão (opcional).")
    parser.add_argument("--augment", default=None, help="Pipeline de augment (opcional).")

    parser.add_argument("--recursive", action="store_true", help="Varre subpastas recursivamente.")
    parser.add_argument("--dry-run", action="store_true", help="Não grava no banco, só mostra o que faria.")
    parser.add_argument("--create-table", action="store_true", help="Cria a tabela/índices se não existirem.")

    # Novas
    parser.add_argument("--infer-from-path", action="store_true",
                        help="Inferir dataset/split/idioma/gênero/emoção/speaker/augment do caminho e nome.")
    parser.add_argument("--split-folders", default="train,val,test",
                        help="Lista de nomes de pastas que indicam split. Ex.: train,val,test")
    parser.add_argument("--augmented-folder-name", default="augmented",
                        help="Nome da pasta que indica que o arquivo é aumentado.")
    parser.add_argument("--commit-interval", type=int, default=200,
                        help="Commit a cada N arquivos (padrão: 200).")

    args = parser.parse_args()

    if not args.database_url:
        print("Erro: informe --database-url ou variável de ambiente DATABASE_URL", file=sys.stderr)
        sys.exit(2)

    root = Path(args.audio_root)
    if not root.is_dir():
        print(f"Erro: audio-root '{root}' não é um diretório.", file=sys.stderr)
        sys.exit(2)

    split_candidates = tuple(s.strip().lower() for s in args.split_folders.split(",") if s.strip())

    conn = connect_db(args.database_url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.create_table:
                cur.execute(CREATE_TABLE_SQL)
                conn.commit()
                print("Tabela/índices verificados/criados.")

            count_total = 0
            count_upserted = 0

            for f in iter_audio_files(root, args.recursive):
                count_total += 1

                rel_path = compute_rel_path(root, f)
                sha = sha256_file(f)
                fmt = f.suffix.lower().lstrip(".")[:8] or None

                duration, sr, ch = get_duration_generic(f)

                # Defaults vindos da linha de comando
                ds = args.dataset
                emotion = args.emotion
                sid = args.speaker
                split = args.split
                aug = args.augment

                if args.infer_from_path:
                    parsed = parse_filename(f)
                    from_path = infer_from_path(root, f, split_candidates, args.augmented_folder_name)

                    # Preenchimentos com prioridade da inferência quando existir
                    if from_path.get("dataset"):
                        ds = from_path["dataset"]
                    # emoção preferencialmente do arquivo
                    if parsed.get("emotion"):
                        emotion = parsed["emotion"]
                    if parsed.get("speaker_id"):
                        sid = parsed["speaker_id"]
                    if from_path.get("split"):
                        split = from_path["split"]

                    # construir augment/tags (inclui lang/gender)
                    aug = build_aug_string(parsed, from_path, args.augment)

                row = {
                    "rel_path": rel_path,
                    "sha256": sha,
                    "format": fmt,
                    "duration_s": duration,
                    "sample_rate": sr,
                    "channels": ch,
                    "dataset": ds,
                    "speaker_id": sid,
                    "emotion_label": emotion,
                    "split": split,
                    "augment_pipeline": aug,
                }

                if args.dry_run:
                    print(f"[DRY] {rel_path}\n"
                          f"      sha256={sha[:12]}… fmt={fmt} dur={duration} sr={sr} ch={ch}\n"
                          f"      dataset={ds} split={split} speaker={sid} emotion={emotion}\n"
                          f"      augment_pipeline={aug}")
                    continue

                cur.execute(UPSERT_SQL, row)
                returned = cur.fetchone()
                if returned and returned.get("id"):
                    count_upserted += 1

                # commit em lotes
                if count_total % max(1, args.commit_interval) == 0:
                    conn.commit()
            conn.commit()

            if args.dry_run:
                print(f"\n[DRY] Arquivos varridos: {count_total}")
            else:
                print(f"\nArquivos processados: {count_total} | Registros upserted: {count_upserted}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
