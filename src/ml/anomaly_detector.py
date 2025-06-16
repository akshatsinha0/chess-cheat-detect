# src/ml/anomaly_detector.py

import os
import numpy as np
import tensorflow as tf

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
        # Load the TensorFlow SavedModel for inference[1]
        self.model = tf.keras.models.load_model(model_path)
        self.threshold = threshold

    def extract_features(self, fen: str, best_move: str, evaluation: dict) -> np.ndarray:
        """
        Convert game data into a feature vector for the model.

        Args:
            fen (str): FEN string of current board state.
            best_move (str): Engine’s recommended move.
            evaluation (dict): Engine evaluation (e.g., {"type":"cp","value":20}).

        Returns:
            np.ndarray: 2D array shape (1, n_features) ready for prediction[2].
        """
        # Example feature: normalized centipawn evaluation
        eval_value = evaluation.get("value", 0)
        eval_norm = np.tanh(eval_value / 100.0)

        # TODO: Extend with move quality, time per move, position complexity, etc.
        return np.array([eval_norm]).reshape(1, -1)

    def predict_suspicion(self, fen: str, best_move: str, evaluation: dict) -> float:
        """
        Returns a float score (0–1) indicating cheating likelihood.

        Args:
            fen (str): Current board FEN.
            best_move (str): Stockfish’s suggested move.
            evaluation (dict): Stockfish evaluation output.

        Returns:
            float: Suspicion probability; > threshold signals potential cheating.
        """
        features = self.extract_features(fen, best_move, evaluation)
        # Model outputs a probability score for anomaly[1]
        score = self.model.predict(features, verbose=0)[0][0]
        return float(score)
