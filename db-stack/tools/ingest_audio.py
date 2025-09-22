#!/usr/bin/env python3
import os
import sys
import argparse
import hashlib
from pathlib import Path
from typing import Optional, Tuple

import psycopg2
import psycopg2.extras

# ---------- Duração de áudio (opcional) ----------
def get_wav_duration(path: Path) -> Optional[float]:
    import wave
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return round(frames / float(rate), 3)
    except Exception:
        return None
    return None

def get_duration_generic(path: Path) -> Optional[float]:
    """
    Tenta detectar a duração:
    - WAV: stdlib wave
    - Outros formatos: se 'mutagen' estiver instalado, usa
    """
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return get_wav_duration(path)
    try:
        from mutagen import File as MutagenFile  # type: ignore
        m = MutagenFile(str(path))
        if m is not None and getattr(m, "info", None):
            dur = getattr(m.info, "length", None)
            if dur is not None:
                return round(float(dur), 3)
    except Exception:
        pass
    return None

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
        # Se o arquivo não está dentro do root, armazena apenas o nome
        rel = file_path.name
    return rel.replace("\\", "/")

def main():
    parser = argparse.ArgumentParser(
        description="Ingestão de arquivos de áudio no Postgres (salvando apenas rel_path e metadados)."
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""),
                        help="DSN do Postgres. Ex: postgresql://user:pass@host:5432/db")
    parser.add_argument("--audio-root", required=True,
                        help="Diretório raiz onde ficam os áudios (para montar rel_path).")
    parser.add_argument("--dataset", default=None, help="Nome do dataset padrão (opcional).")
    parser.add_argument("--emotion", default=None, help="Rótulo de emoção padrão (opcional).")
    parser.add_argument("--split", default=None, help="train/val/test (opcional).")
    parser.add_argument("--speaker", default=None, help="ID do falante padrão (opcional).")
    parser.add_argument("--augment", default=None, help="Pipeline de augment (opcional).")
    parser.add_argument("--recursive", action="store_true", help="Varre subpastas recursivamente.")
    parser.add_argument("--dry-run", action="store_true", help="Não grava no banco, só mostra o que faria.")
    parser.add_argument("--create-table", action="store_true", help="Cria a tabela/índices se não existirem.")
    args = parser.parse_args()

    if not args.database_url:
        print("Erro: informe --database-url ou variável de ambiente DATABASE_URL", file=sys.stderr)
        sys.exit(2)

    root = Path(args.audio_root)
    if not root.is_dir():
        print(f"Erro: audio-root '{root}' não é um diretório.", file=sys.stderr)
        sys.exit(2)

    conn = connect_db(args.database_url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.create_table:
                cur.execute(CREATE_TABLE_SQL)
                conn.commit()
                print("Tabela/índices verificados/criados.")

            count_total = 0
            count_new = 0
            for f in iter_audio_files(root, args.recursive):
                count_total += 1

                rel_path = compute_rel_path(root, f)
                sha = sha256_file(f)
                fmt = f.suffix.lower().lstrip(".")[:8] or None

                # Só tentamos duração; sample_rate/channels deixo None (poderia extrair de WAV via wave.getframerate/getnchannels)
                duration = get_duration_generic(f)

                row = {
                    "rel_path": rel_path,
                    "sha256": sha,
                    "format": fmt,
                    "duration_s": duration,
                    "sample_rate": None,
                    "channels": None,
                    "dataset": args.dataset,
                    "speaker_id": args.speaker,
                    "emotion_label": args.emotion,
                    "split": args.split,
                    "augment_pipeline": args.augment,
                }

                if args.dry_run:
                    print(f"[DRY] {rel_path}  sha256={sha[:12]}…  fmt={fmt}  dur={duration}")
                    continue

                cur.execute(UPSERT_SQL, row)
                returned = cur.fetchone()
                if returned and returned.get("id"):
                    count_new += 1

                # commit em lotes simples
                if count_total % 200 == 0:
                    conn.commit()
            conn.commit()

            if args.dry_run:
                print(f"\n[DRY] Arquivos varridos: {count_total}")
            else:
                print(f"\nArquivos processados: {count_total} | Registros upserted: {count_new}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
