# src/ml/anomaly_detector.py

import os
import argparse
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

class AnomalyDetector:
    """
    Loads a trained anomaly detection model and provides a method
    to predict a cheating suspicion score between 0 and 1.
    """
    def __init__(self, model_path: str, threshold: float = 0.5):
        """
        Args:
            model_path (str): Path to the saved TensorFlow model.
            threshold (float): Score above which cheating is flagged.
        """
        if not os.path.isfile(model_path):
            raise IOError(f"Model file not found at {model_path}")
        self.model = tf.keras.models.load_model(model_path)
        self.threshold = threshold

    @staticmethod
    def build_model(input_dim: int) -> tf.keras.Model:
        """Constructs a simple neural network for anomaly detection."""
        model = models.Sequential([
            layers.Input(shape=(input_dim,)),          # Single-feature input
            layers.Dense(16, activation='relu'),
            layers.Dense(8, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam',
                      loss='binary_crossentropy',
                      metrics=['accuracy'])
        return model

    def extract_features(self, fen: str, best_move: str, evaluation: dict) -> np.ndarray:
        """
        Converts game data into a feature vector for the model.
        """
        eval_val = evaluation.get('value', 0)
        norm = np.tanh(eval_val / 100.0)              # Normalize centipawn score[4]
        return np.array([norm]).reshape(1, -1)

    def predict_suspicion(self, fen: str, best_move: str, evaluation: dict) -> float:
        """
        Returns a float score (0–1) indicating cheating likelihood.
        """
        features = self.extract_features(fen, best_move, evaluation)
        score = self.model.predict(features, verbose=0)[0][0]
        return float(score)

def load_dataset() -> (np.ndarray, np.ndarray):
    """
    Placeholder to load training data.
    Replace with real data-loading logic.
    """
    # Example synthetic data for demonstration purposes
    X = np.random.randn(1000, 1)
    y = (X[:, 0] > 1.0).astype(int)
    return X, y

def train_and_save(args):
    """
    Trains the anomaly detection model and saves it to disk.
    """
    X, y = load_dataset()
    model = AnomalyDetector.build_model(input_dim=X.shape[1])
    model.fit(X, y,
              epochs=20,
              batch_size=32,
              validation_split=0.2)
    os.makedirs(os.path.dirname(args.save), exist_ok=True)
    model.save(args.save)                         # Saves as HDF5 by default[2]
    print(f"Model saved to {args.save}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train or load anomaly detector')  # argparse usage[1]
    parser.add_argument('--train', action='store_true', help='Run training')
    parser.add_argument('--save', type=str,
                        required='--train' in os.sys.argv,
                        help='Path to save the trained model')
    args = parser.parse_args()

    if args.train:
        train_and_save(args)
    else:
        detector = AnomalyDetector(model_path=args.save)
        print("AnomalyDetector loaded successfully")
