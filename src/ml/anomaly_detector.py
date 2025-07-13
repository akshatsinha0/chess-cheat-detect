import os
import argparse
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
class AnomalyDetector:
    def __init__(self, model_path: str, threshold: float = 0.5):
        if not os.path.isfile(model_path):
            raise IOError(f"Model file not found at {model_path}")
        self.model = tf.keras.models.load_model(model_path)
        self.threshold = threshold
    @staticmethod
    def build_model(input_dim: int) -> tf.keras.Model:
        model = models.Sequential([
            layers.Input(shape=(input_dim,), name="input_layer"),
            layers.Dense(16, activation="relu"),
            layers.Dense(8, activation="relu"),
            layers.Dense(1, activation="sigmoid")
        ])
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        return model
    def extract_features(self, fen: str, best_move: str, evaluation: dict) -> np.ndarray:
        eval_val = evaluation.get("value", 0)
        norm = np.tanh(eval_val / 100.0)
        try:
            expected_features = self.model.input_shape[1]
            if expected_features > 1:
                features = np.zeros(expected_features)
                features[0] = norm
                return features.reshape(1, -1)
        except:
            pass
        return np.array([norm]).reshape(1, -1)
    def predict_suspicion(self, fen: str, best_move: str, evaluation: dict) -> float:
        features = self.extract_features(fen, best_move, evaluation)
        score = self.model.predict(features, verbose=0)[0][0]
        return float(score)
def load_dataset() -> tuple[np.ndarray, np.ndarray]:
    X = np.random.randn(1000, 1)
    y = (X[:, 0] > 1.0).astype(int)
    return X, y
def train_and_save(args):
    X, y = load_dataset()
    model = AnomalyDetector.build_model(input_dim=X.shape[1])
    model.fit(X, y, epochs=20, batch_size=32, validation_split=0.2)
    os.makedirs(os.path.dirname(args.save), exist_ok=True)
    model.save(args.save, save_format="keras")
    print(f"Model saved to {args.save}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train or load anomaly detection model")
    parser.add_argument("--train", action="store_true", help="Run training mode")
    parser.add_argument("--save", type=str, required="--train" in os.sys.argv, help="Path to save the trained model")
    args = parser.parse_args()
    if args.train:
        train_and_save(args)
    else:
        detector = AnomalyDetector(model_path=args.save)
        print("AnomalyDetector loaded successfully")
