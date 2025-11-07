# services/extract_lib.py
# -*- coding: utf-8 -*-

# --- Headless Matplotlib (SEM GUI) — tem que vir antes de importar matplotlib ---
import os
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib
matplotlib.use("Agg", force=True)

# --- Imports padrão ---
from pathlib import Path
import shutil
import numpy as np
import librosa
import librosa.display

# Matplotlib, sem pyplot (evita estado global / GUI)
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


# ======================================================================
# KERNEL HEADLESS PARA SALVAR IMAGEM EM DISCO (sem usar pyplot)
# ======================================================================
def save_spec_as_image(spec_data, file_path, sr, y_axis=None, figsize=(4, 4), dpi=100):
    """
    Salva a imagem do espectrograma (sem eixos/bordas), 100% headless (Agg).
    """
    fig = Figure(figsize=figsize, dpi=dpi)
    canvas = FigureCanvas(fig)

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    librosa.display.specshow(spec_data, sr=sr, ax=ax, y_axis=y_axis)

    # Usa o writer de arquivo do Figure (sem pyplot)
    fig.savefig(file_path, bbox_inches="tight", pad_inches=0)
    # Nada de plt.close — não usamos pyplot


# ======================================================================
# KERNEL HEADLESS PARA GERAR RGB EM MEMÓRIA (pro multimodal)
# ======================================================================
def render_spec_to_rgb_np(spec_data, sr, y_axis=None, figsize=(4, 4), dpi=100):
    """
    Renderiza o espectrograma headless (Agg) e devolve RGB (H, W, 3) uint8.
    Usa print_to_buffer() (compatível com várias versões do Matplotlib).
    """
    fig = Figure(figsize=figsize, dpi=dpi)
    canvas = FigureCanvas(fig)

    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()
    librosa.display.specshow(spec_data, sr=sr, ax=ax, y_axis=y_axis)

    canvas.draw()
    # Retorna buffer RGBA + (width, height)
    buf, (w, h) = canvas.print_to_buffer()
    rgba = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
    rgb = rgba[:, :, :3].copy()  # descarta alpha
    return rgb


# ======================================================================
# EXTRAÇÃO EM MEMÓRIA (para o KerasMultimodal): dd_mfcc_img, chroma_img, zcr, rms
# ======================================================================
def extract_features_np(audio_path, target_sr=22050, n_fft=2048, hop=512, n_mfcc_dd=13):
    """
    Retorna:
      dd_mfcc_img_rgb: (H,W,3) uint8  [mesma estética do save_spec_as_image]
      chroma_img_rgb : (H,W,3) uint8
      zcr           : (T,) float
      rms           : (T,) float
    """
    # Carrega com SR original e reamostra para target_sr (mantendo mono=True)
    signal, sr = librosa.load(audio_path, sr=None)
    if sr != target_sr:
        signal = librosa.resample(signal, orig_sr=sr, target_sr=target_sr)
        sr = target_sr

    # 1) dd_mfcc (13 + delta^2) — igual ao pipeline de treino
    mfccs = librosa.feature.mfcc(y=signal, n_mfcc=n_mfcc_dd, sr=sr)
    delta2_mfccs = librosa.feature.delta(data=mfccs, order=2)
    dd_mfcc_img_rgb = render_spec_to_rgb_np(delta2_mfccs, sr, y_axis=None)

    # 2) chromagram (imagem)
    chromagram = librosa.feature.chroma_stft(y=signal, sr=sr)
    chroma_img_rgb = render_spec_to_rgb_np(chromagram, sr, y_axis="chroma")

    # 3) 1D (arrays)
    zcr = librosa.feature.zero_crossing_rate(y=signal)[0]
    rms = librosa.feature.rms(y=signal)[0]

    return dd_mfcc_img_rgb, chroma_img_rgb, zcr, rms


# ======================================================================
# OPCIONAL — EXTRAÇÃO EM DISCO (para gerar dataset de features/imagens)
# ======================================================================
def extract_features(audio_path, output_dir, base_name, n_mfcc_dd=13):
    """
    Para cada áudio, cria diretorio e salva:
      - dd_mfcc.jpeg
      - chromagram.jpeg
      - zcr.npy
      - rms.npy
    """
    try:
        counter = 0
        target_dir_name = base_name
        target_dir = Path(output_dir) / target_dir_name
        while target_dir.exists():
            counter += 1
            target_dir_name = f"{base_name}_{counter}"
            target_dir = Path(output_dir) / target_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processing {Path(audio_path).name} -> {target_dir_name}")

        signal, sr = librosa.load(audio_path, sr=None, mono=True)

        # dd_mfcc
        mfccs = librosa.feature.mfcc(y=signal, n_mfcc=n_mfcc_dd, sr=sr)
        delta2_mfccs = librosa.feature.delta(data=mfccs, order=2)
        save_spec_as_image(delta2_mfccs, target_dir / "dd_mfcc.jpeg", sr)

        # chroma
        chromagram = librosa.feature.chroma_stft(y=signal, sr=sr)
        save_spec_as_image(chromagram, target_dir / "chromagram.jpeg", sr, y_axis="chroma")

        # 1D
        zcr = librosa.feature.zero_crossing_rate(y=signal)[0]
        np.save(target_dir / "zcr.npy", zcr)

        rms = librosa.feature.rms(y=signal)[0]
        np.save(target_dir / "rms.npy", rms)

    except Exception as e:
        print(f"Error processing {audio_path}: {e}")


# ======================================================================
# Helpers p/ organização de dataset (opcional)
# ======================================================================
def parse_audio_filename(filename):
    """
    Extrai lang/gender/emotion de nomes como 'eng_F_angry_8.wav' ou
    'por_M_disgust_166_pitch_awgn_high-medium_1.wav'
    """
    LANGUAGES = {"eng", "por", "fra"}
    GENDERS = {"F", "M"}
    EMOTIONS = {"angry", "disgust", "fear", "happy", "neutral", "sadness", "surprise"}

    try:
        stem = Path(filename).stem
        parts = stem.split('_')
        if len(parts) < 3:
            return None

        lang, gender, emotion = parts[0], parts[1], parts[2]
        if lang not in LANGUAGES or gender not in GENDERS or emotion not in EMOTIONS:
            return None

        return f"{lang}_{gender}_{emotion}"
    except Exception:
        return None


def process_dataset(source_root, output_root, audio_extensions=(".wav",), n_mfcc_dd=13):
    """
    Mapeia e processa todos os áudios recursivamente, salvando features em disco.
    """
    from multiprocessing import Pool, cpu_count
    try:
        from tqdm import tqdm
        use_tqdm = True
    except Exception:
        # Se tqdm não estiver instalado, roda sem barra de progresso
        use_tqdm = False

    Path(output_root).mkdir(parents=True, exist_ok=True)
    unparsed_files = []
    tasks = []

    print("Mapping audio files...")
    for root, _, files in os.walk(source_root):
        for file in files:
            if file.lower().endswith(audio_extensions):
                base_name = parse_audio_filename(file)
                if base_name:
                    audio_path = os.path.join(root, file)
                    tasks.append((audio_path, output_root, base_name, n_mfcc_dd))
                else:
                    unparsed_files.append(file)
                    print(f"Ignored, impossible to parse '{file}'")

    print(f"Total of {len(tasks)} files to process.")
    num_workers = max(1, cpu_count() - 1)
    print(f"Initializing processing with {num_workers} workers...")

    def _worker(args):
        a, out, b, n = args
        return extract_features(a, out, b, n_mfcc_dd=n)

    if use_tqdm:
        with Pool(processes=num_workers) as pool:
            list(tqdm(pool.imap_unordered(_worker, tasks), total=len(tasks)))
    else:
        with Pool(processes=num_workers) as pool:
            pool.map(_worker, tasks)

    print("\n--- Feature extraction completed! ---")
    if unparsed_files:
        print("\nThese files couldn't be parsed and were ignored:")
        for name in unparsed_files:
            print(f"- {name}")


def sample_dataset(source_root, output_root, step=4, audio_extensions=(".wav",)):
    """
    Amostra 1 a cada 'step' arquivos por duração e copia para output_root.
    """
    Path(output_root).mkdir(parents=True, exist_ok=True)
    audio_files_with_duration = {}

    for root, _, files in os.walk(source_root):
        for file in files:
            if file.lower().endswith(audio_extensions):
                audio_path = Path(root) / file
                try:
                    duration = librosa.get_duration(path=str(audio_path))
                    audio_files_with_duration[str(audio_path)] = duration
                except Exception as e:
                    print(f"Could not process {audio_path}: {e}")

    if not audio_files_with_duration:
        print("No audio files found. Exiting.")
        return

    print("Sorting files by duration...")
    sorted_files = sorted(audio_files_with_duration.items(), key=lambda item: item[1])
    sampled_files = sorted_files[::step]
    print(f"Selected {len(sampled_files)} files for sampling (1 in every {step}).")

    for source_file_path, _duration in sampled_files:
        try:
            file_name = Path(source_file_path).name
            destination_path = Path(output_root) / file_name
            shutil.copy(source_file_path, destination_path)
        except Exception as e:
            print(f"Could not copy {source_file_path}: {e}")


# if __name__ == "__main__":
#     # Exemplo de uso do process_dataset (opcional)
#     from src.utils.utils import load_config
#     cfg = load_config()
#     process_dataset(cfg["DATASET_FOLDER"], cfg["FEATURES_DIR"])