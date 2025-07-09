import os
import argparse
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

class AnomalyDetector:
    """
    Loads a trained anomaly detection model and predicts a cheating
    suspicion score between 0 and 1.
    """
    def __init__(self, model_path: str, threshold: float = 0.5):
        if not os.path.isfile(model_path):
            raise IOError(f"Model file not found at {model_path}")  # Ensure model exists[1]
        self.model = tf.keras.models.load_model(model_path)         # Load saved model[2]
        self.threshold = threshold

    @staticmethod
    def build_model(input_dim: int) -> tf.keras.Model:
        """
        Constructs a simple feed-forward network for anomaly detection.
        """
        model = models.Sequential([
            layers.Input(shape=(input_dim,), name="input_layer"),   # Modern Input API[3]
            layers.Dense(16, activation="relu"),
            layers.Dense(8, activation="relu"),
            layers.Dense(1, activation="sigmoid")
        ])
        model.compile(optimizer="adam",
                      loss="binary_crossentropy",
                      metrics=["accuracy"])                            # Compile settings[4]
        return model

    def extract_features(self, fen: str, best_move: str, evaluation: dict) -> np.ndarray:
        """
        Converts game data into a numerical feature vector.
        For the basic model, we use simple features.
        For advanced models, this should match the training feature set.
        """
        # Basic feature extraction for compatibility
        eval_val = evaluation.get("value", 0)
        norm = np.tanh(eval_val / 100.0)  # Normalize centipawn score
        
        # If model expects more features, pad with zeros
        # This ensures compatibility with both simple and advanced models
        try:
            expected_features = self.model.input_shape[1]
            if expected_features > 1:
                # Create a feature vector matching the expected size
                features = np.zeros(expected_features)
                features[0] = norm
                return features.reshape(1, -1)
        except:
            pass
        
        return np.array([norm]).reshape(1, -1)

    def predict_suspicion(self, fen: str, best_move: str, evaluation: dict) -> float:
        """
        Returns a float score (0–1) indicating cheating likelihood.
        """
        features = self.extract_features(fen, best_move, evaluation)
        score = self.model.predict(features, verbose=0)[0][0]       # Predict probability[6]
        return float(score)

def load_dataset() -> tuple[np.ndarray, np.ndarray]:
    """
    Placeholder to load training data. Replace with actual logic.
    """
    X = np.random.randn(1000, 1)                                 # Synthetic demo data[7]
    y = (X[:, 0] > 1.0).astype(int)                              # Synthetic labels[7]
    return X, y

def train_and_save(args):
    """
    Trains the anomaly detection model and saves it in native Keras format.
    """
    X, y = load_dataset()
    model = AnomalyDetector.build_model(input_dim=X.shape[1])
    model.fit(X, y,
              epochs=20,
              batch_size=32,
              validation_split=0.2)                              # Train with validation[8]
    os.makedirs(os.path.dirname(args.save), exist_ok=True)
    model.save(args.save, save_format="keras")                  # Save as .keras file[9]
    print(f"Model saved to {args.save}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train or load anomaly detection model")    # CLI for training/inference[10]
    parser.add_argument("--train", action="store_true",
                        help="Run training mode")
    parser.add_argument("--save", type=str,
                        required="--train" in os.sys.argv,
                        help="Path to save the trained model")
    args = parser.parse_args()

    if args.train:
        train_and_save(args)
    else:
        detector = AnomalyDetector(model_path=args.save)
        print("AnomalyDetector loaded successfully")
