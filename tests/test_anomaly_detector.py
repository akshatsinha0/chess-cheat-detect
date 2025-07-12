# tests/test_anomaly_detector.py

import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ml.anomaly_detector import AnomalyDetector

class TestAnomalyDetector:
    """Test suite for the AnomalyDetector class."""
    
    @pytest.fixture
    def temp_model_path(self):
        """Create a temporary model file."""
        with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp:
            # Create a simple model and save it
            model = tf.keras.Sequential([
                tf.keras.layers.Input(shape=(1,)),
                tf.keras.layers.Dense(1, activation='sigmoid')
            ])
            model.compile(optimizer='adam', loss='binary_crossentropy')
            model.save(tmp.name)
            yield tmp.name
            # Cleanup
            os.unlink(tmp.name)
    
    @pytest.fixture
    def anomaly_detector(self, temp_model_path):
        """Create an AnomalyDetector instance."""
        return AnomalyDetector(model_path=temp_model_path, threshold=0.5)
    
    def test_initialization_with_existing_model(self, temp_model_path):
        """Test initialization with an existing model file."""
        detector = AnomalyDetector(model_path=temp_model_path)
        assert detector.model is not None
        assert detector.threshold == 0.5
    
    def test_initialization_with_missing_model(self):
        """Test initialization with a missing model file."""
        with pytest.raises(IOError, match="Model file not found"):
            AnomalyDetector(model_path="nonexistent.h5")
    
    def test_build_model(self):
        """Test model building."""
        model = AnomalyDetector.build_model(input_dim=5)
        
        assert model is not None
        assert model.input_shape == (None, 5)
        assert model.output_shape == (None, 1)
        assert len(model.layers) == 4  # Input + 3 Dense layers
    
    def test_extract_features_simple(self, anomaly_detector):
        """Test feature extraction for simple model."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        best_move = "e2e4"
        evaluation = {"value": 25, "type": "cp"}
        
        features = anomaly_detector.extract_features(fen, best_move, evaluation)
        
        assert features.shape == (1, 1)
        assert -1 <= features[0, 0] <= 1  # tanh normalized
    
    def test_extract_features_advanced_model(self):
        """Test feature extraction for advanced model with multiple inputs."""
        # Create a model expecting 13 features
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(13,)),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy')
        
        # Create detector with this model
        detector = AnomalyDetector.__new__(AnomalyDetector)
        detector.model = model
        detector.threshold = 0.5
        
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        best_move = "e2e4"
        evaluation = {"value": 25, "type": "cp"}
        
        features = detector.extract_features(fen, best_move, evaluation)
        
        assert features.shape == (1, 13)
        assert features[0, 0] != 0  # First feature should be set
    
    def test_predict_suspicion(self, anomaly_detector):
        """Test suspicion prediction."""
        # Mock the model prediction
        anomaly_detector.model.predict = Mock(return_value=np.array([[0.75]]))
        
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        best_move = "e2e4"
        evaluation = {"value": 25, "type": "cp"}
        
        score = anomaly_detector.predict_suspicion(fen, best_move, evaluation)
        
        assert isinstance(score, float)
        assert score == 0.75
        assert 0 <= score <= 1
    
    def test_predict_suspicion_edge_cases(self, anomaly_detector):
        """Test suspicion prediction with edge cases."""
        # Test with mate evaluation
        anomaly_detector.model.predict = Mock(return_value=np.array([[0.95]]))
        
        fen = "8/8/8/8/8/8/8/8 w - - 0 1"
        best_move = "None"
        evaluation = {"value": 5, "type": "mate"}
        
        score = anomaly_detector.predict_suspicion(fen, best_move, evaluation)
        
        assert isinstance(score, float)
        assert 0 <= score <= 1
    
    def test_load_dataset(self):
        """Test synthetic dataset loading."""
        X, y = AnomalyDetector.__new__(AnomalyDetector).load_dataset()
        
        assert X.shape[0] == 1000
        assert y.shape[0] == 1000
        assert X.shape[1] == 1
        assert np.all((y == 0) | (y == 1))
    
    @patch('tensorflow.keras.models.Sequential.fit')
    def test_train_and_save(self, mock_fit):
        """Test model training and saving."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, 'test_model.keras')
            
            # Mock training
            mock_history = MagicMock()
            mock_history.history = {'loss': [0.5, 0.3], 'accuracy': [0.7, 0.9]}
            mock_fit.return_value = mock_history
            
            # Create args object
            args = MagicMock()
            args.save = save_path
            
            # Import and run training function
            from src.ml.anomaly_detector import train_and_save
            train_and_save(args)
            
            # Check that model was saved
            assert os.path.exists(save_path)
