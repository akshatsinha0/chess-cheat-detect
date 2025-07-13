import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ml.anomaly_detector import AnomalyDetector
class TestAnomalyDetector:
    @pytest.fixture
    def temp_model_path(self):
        with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp:
            model = tf.keras.Sequential([
                tf.keras.layers.Input(shape=(1,)),
                tf.keras.layers.Dense(1, activation='sigmoid')
            ])
            model.compile(optimizer='adam', loss='binary_crossentropy')
            model.save(tmp.name)
            yield tmp.name
            os.unlink(tmp.name)
    @pytest.fixture
    def anomaly_detector(self, temp_model_path):
        return AnomalyDetector(model_path=temp_model_path, threshold=0.5)
    def test_initialization_with_existing_model(self, temp_model_path):
        detector = AnomalyDetector(model_path=temp_model_path)
        assert detector.model is not None
        assert detector.threshold == 0.5
    def test_initialization_with_missing_model(self):
        with pytest.raises(IOError, match="Model file not found"):
            AnomalyDetector(model_path="nonexistent.h5")
    def test_build_model(self):
        model = AnomalyDetector.build_model(input_dim=5)
        assert model is not None
        assert model.input_shape == (None, 5)
        assert model.output_shape == (None, 1)
        assert len(model.layers) == 4
    def test_extract_features_simple(self, anomaly_detector):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        best_move = "e2e4"
        evaluation = {"value": 25, "type": "cp"}
        features = anomaly_detector.extract_features(fen, best_move, evaluation)
        assert features.shape == (1, 1)
        assert -1 <= features[0, 0] <= 1
    def test_extract_features_advanced_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(13,)),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy')
        detector = AnomalyDetector.__new__(AnomalyDetector)
        detector.model = model
        detector.threshold = 0.5
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        best_move = "e2e4"
        evaluation = {"value": 25, "type": "cp"}
        features = detector.extract_features(fen, best_move, evaluation)
        assert features.shape == (1, 13)
        assert features[0, 0] != 0
    def test_predict_suspicion(self, anomaly_detector):
        anomaly_detector.model.predict = Mock(return_value=np.array([[0.75]]))
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        best_move = "e2e4"
        evaluation = {"value": 25, "type": "cp"}
        score = anomaly_detector.predict_suspicion(fen, best_move, evaluation)
        assert isinstance(score, float)
        assert score == 0.75
        assert 0 <= score <= 1
    def test_predict_suspicion_edge_cases(self, anomaly_detector):
        anomaly_detector.model.predict = Mock(return_value=np.array([[0.95]]))
        fen = "8/8/8/8/8/8/8/8 w - - 0 1"
        best_move = "None"
        evaluation = {"value": 5, "type": "mate"}
        score = anomaly_detector.predict_suspicion(fen, best_move, evaluation)
        assert isinstance(score, float)
        assert 0 <= score <= 1
    def test_load_dataset(self):
        X, y = AnomalyDetector.__new__(AnomalyDetector).load_dataset()
        assert X.shape[0] == 1000
        assert y.shape[0] == 1000
        assert X.shape[1] == 1
        assert np.all((y == 0) | (y == 1))
    @patch('tensorflow.keras.models.Sequential.fit')
    def test_train_and_save(self, mock_fit):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, 'test_model.keras')
            mock_history = MagicMock()
            mock_history.history = {'loss': [0.5, 0.3], 'accuracy': [0.7, 0.9]}
            mock_fit.return_value = mock_history
            args = MagicMock()
            args.save = save_path
            from src.ml.anomaly_detector import train_and_save
            train_and_save(args)
            assert os.path.exists(save_path)
