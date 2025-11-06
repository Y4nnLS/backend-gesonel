import tensorflow as tf
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import argparse
from sklearn.metrics import classification_report, precision_score, recall_score, f1_score, accuracy_score, confusion_matrix
from tensorflow.keras.models import load_model
from tensorflow.keras.metrics import Precision, Recall, F1Score

# Import your custom modules
from src.PoCs.MultiModalTraining.data_loader_restore import get_data_loaders
from src.PoCs.MultiModalTraining.model_restore import SpecAugment  # Import your custom layer
from src.utils.utils import load_config

# --- Main Configuration ---
MODEL_PATH = 'best_model_finetuned.keras'
PLOTS_DIR = './evaluation_plots'
tf.keras.mixed_precision.set_global_policy('mixed_float16')


def comprehensive_evaluation(model, generator, le, set_name):
    """
    Performs a comprehensive evaluation with all metrics and a confusion matrix.
    (This is your function, translated to English)
    """
    os.makedirs(PLOTS_DIR, exist_ok=True)
    print(f"\n{'=' * 60}")
    print(f"COMPREHENSIVE EVALUATION - {set_name.upper()} SET")
    print(f"{'=' * 60}")

    # 1. Standard Keras Evaluation
    print("\n1. DEFAULT KERAS EVALUATION:")
    evaluation_metrics = model.evaluate(generator, verbose=0)
    metrics_dict = dict(zip(model.metrics_names, evaluation_metrics))
    for name, value in metrics_dict.items():
        print(f"   {name}: {value:.4f}")

    # 2. Collect all predictions and true labels
    print("\n2. COLLECTING PREDICTIONS...")
    y_true = []
    y_pred = []

    # Iterate over the dataset to get all predictions
    for batch_x, batch_y in generator:
        if len(batch_x) == 0:
            continue

        batch_pred = model.predict(batch_x, verbose=0)
        y_true.extend(np.argmax(batch_y, axis=1))
        y_pred.extend(np.argmax(batch_pred, axis=1))

    if not y_true:
        print("Error: No data found in the generator.")
        return None

    # 3. Detailed metrics per class
    print("\n3. DETAILED METRICS PER CLASS:")
    class_names = le.classes_
    report = classification_report(y_true, y_pred, target_names=class_names, digits=4)
    print(report)

    # 4. Aggregate metrics
    print("\n4. AGGREGATE METRICS:")
    precision_w = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    recall_w = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    f1_weighted = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    f1_macro = f1_score(y_true, y_pred, average='macro', zero_division=0)
    accuracy = accuracy_score(y_true, y_pred)

    print(f"   Precision (Weighted): {precision_w:.4f}")
    print(f"   Recall (Weighted): {recall_w:.4f}")
    print(f"   F1-Score (Weighted): {f1_weighted:.4f}")
    print(f"   F1-Score (Macro): {f1_macro:.4f}")
    print(f"   Accuracy: {accuracy:.4f}")

    # 5. Confusion Matrix
    print("\n5. CONFUSION MATRIX:")
    cm = confusion_matrix(y_true, y_pred)

    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names,
                yticklabels=class_names)
    plt.title(f'Confusion Matrix - {set_name}')
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.tight_layout()

    cm_path = os.path.join(PLOTS_DIR, f'confusion_matrix_{set_name.lower()}.png')
    plt.savefig(cm_path, dpi=300, bbox_inches='tight')
    print(f"   Confusion matrix saved to: {cm_path}")
    # plt.show() # Often disabled in scripts

    return {
        'accuracy': accuracy,
        'precision': precision_w,
        'recall': recall_w,
        'f1_weighted': f1_weighted,
        'f1_macro': f1_macro,
        'confusion_matrix': cm
    }


def main(dataset_to_evaluate):

    config = load_config()

    # --- 1. Load Model ---
    print(f"--- Loading model from {MODEL_PATH} ---")
    custom_objects = {"SpecAugment": SpecAugment}
    try:
        model = load_model(MODEL_PATH, custom_objects=custom_objects)
    except Exception as e:
        print("\n--- ERROR: Could not load model. ---")
        print(f"Failed to load: {os.path.abspath(MODEL_PATH)}")
        print(f"Error details: {e}")
        print("Ensure the model file exists and all custom layers (like SpecAugment) are imported.")
        return

    print("Model loaded successfully.")

    # --- 2. Load Data ---
    print("\n--- Loading datasets... ---")
    try:
        train_ds, val_ds, test_ds, label_encoder, _, _ = get_data_loaders(
            features_dir=config["FEATURES_DIR"],
            batch_size=config["BATCH_SIZE"]
        )
    except ValueError as e:
        print(f"Error loading data: {e}")
        return
    print("Datasets loaded.")

    # --- 3. Select Data and Run Evaluation ---
    if dataset_to_evaluate == 'test':
        generator = test_ds
        set_name = "Test (Hold-Out)"
    elif dataset_to_evaluate == 'val':
        generator = val_ds
        set_name = "Validation"
    elif dataset_to_evaluate == 'train':
        generator = train_ds
        set_name = "Training"
    else:
        print(f"Error: Unknown dataset '{dataset_to_evaluate}'. Use 'train', 'val', or 'test'.")
        return

    # --- 4. Re-compile model for evaluation ---
    # This ensures all metrics are correctly attached
    model.compile(
        loss='categorical_crossentropy',
        metrics=[
            'accuracy',
            Precision(name='precision'),
            Recall(name='recall'),
            F1Score(average='macro', name='f1_score')
        ]
    )

    # --- 5. Run the comprehensive evaluation ---
    comprehensive_evaluation(model, generator, label_encoder, set_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a full evaluation on a saved model.")
    parser.add_argument(
        "--set",
        type=str,
        default="test",
        choices=['train', 'val', 'test'],
        help="The dataset to evaluate: 'train', 'val', or 'test' (default: 'test')"
    )
    args = parser.parse_args()

    main(args.set)
