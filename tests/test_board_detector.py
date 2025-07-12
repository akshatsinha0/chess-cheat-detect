# tests/test_board_detector.py

import pytest
import numpy as np
import cv2
import chess
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.detection.board_detector import BoardDetector
from src.detection.piece_recognizer import PieceRecognizer

class TestBoardDetector:
    """Test suite for the BoardDetector class."""
    
    @pytest.fixture
    def mock_video_capture(self):
        """Mock cv2.VideoCapture."""
        with patch('cv2.VideoCapture') as mock_capture:
            mock_instance = MagicMock()
            mock_capture.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def board_detector(self, mock_video_capture):
        """Create a BoardDetector instance with mocked video capture."""
        detector = BoardDetector(camera_index=0)
        return detector
    
    def test_initialization(self, board_detector):
        """Test BoardDetector initialization."""
        assert board_detector.camera_index == 0
        assert board_detector.board_size == (8, 8)
        assert board_detector.piece_recognizer is not None
    
    def test_capture_frame_success(self, board_detector, mock_video_capture):
        """Test successful frame capture."""
        # Mock successful frame capture
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_video_capture.read.return_value = (True, test_frame)
        
        frame = board_detector.capture_frame()
        
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        mock_video_capture.read.assert_called_once()
    
    def test_capture_frame_failure(self, board_detector, mock_video_capture):
        """Test frame capture failure."""
        # Mock failed frame capture
        mock_video_capture.read.return_value = (False, None)
        
        with pytest.raises(RuntimeError, match="Failed to capture frame"):
            board_detector.capture_frame()
    
    def test_preprocess(self, board_detector):
        """Test image preprocessing."""
        # Create test image
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        processed = board_detector.preprocess(test_frame)
        
        # Check that output is grayscale
        assert len(processed.shape) == 2
        assert processed.shape[:2] == test_frame.shape[:2]
    
    @patch('cv2.findChessboardCorners')
    def test_detect_board_success(self, mock_find_corners, board_detector):
        """Test successful board detection."""
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock successful corner detection
        mock_corners = np.random.rand(64, 1, 2).astype(np.float32)
        mock_find_corners.return_value = (True, mock_corners)
        
        corners = board_detector.detect_board(test_frame)
        
        assert corners is not None
        assert corners.shape == mock_corners.shape
    
    @patch('cv2.findChessboardCorners')
    def test_detect_board_failure(self, mock_find_corners, board_detector):
        """Test board detection failure."""
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock failed corner detection
        mock_find_corners.return_value = (False, None)
        
        with pytest.raises(RuntimeError, match="Chessboard not detected"):
            board_detector.detect_board(test_frame)
    
    def test_recognize_piece(self, board_detector):
        """Test piece recognition method."""
        # Create test square image
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        
        # Mock the piece recognizer
        board_detector.piece_recognizer.recognize = Mock(return_value=chess.Piece(chess.PAWN, chess.WHITE))
        
        piece = board_detector.recognize_piece(test_square)
        
        assert piece is not None
        assert piece.piece_type == chess.PAWN
        assert piece.color == chess.WHITE
    
    @patch('cv2.findChessboardCorners')
    @patch('cv2.findHomography')
    @patch('cv2.warpPerspective')
    def test_get_fen_from_image(self, mock_warp, mock_homography, mock_find_corners, board_detector):
        """Test FEN extraction from image."""
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock corner detection
        mock_corners = np.array([
            [[100, 100]], [[300, 100]], [[300, 300]], [[100, 300]]
        ], dtype=np.float32)
        mock_find_corners.return_value = (True, mock_corners)
        
        # Mock homography
        mock_homography.return_value = (np.eye(3), None)
        
        # Mock warped image
        warped_image = np.zeros((400, 400, 3), dtype=np.uint8)
        mock_warp.return_value = warped_image
        
        # Mock piece recognition to return None (empty board)
        board_detector.piece_recognizer.recognize = Mock(return_value=None)
        
        fen = board_detector.get_fen_from_image(test_frame)
        
        assert isinstance(fen, str)
        assert fen == chess.Board.empty().fen()  # Should be empty board

class TestPieceRecognizer:
    """Test suite for the PieceRecognizer class."""
    
    @pytest.fixture
    def piece_recognizer(self):
        """Create a PieceRecognizer instance."""
        return PieceRecognizer()
    
    def test_initialization(self, piece_recognizer):
        """Test PieceRecognizer initialization."""
        assert piece_recognizer.model is not None
        assert len(piece_recognizer.PIECE_CLASSES) == 13
    
    def test_build_model(self, piece_recognizer):
        """Test model building."""
        model = piece_recognizer.build_model()
        
        assert model is not None
        assert model.input_shape == (None, 50, 50, 3)
        assert model.output_shape == (None, 13)
    
    def test_preprocess_square(self, piece_recognizer):
        """Test square image preprocessing."""
        # Test with correct size
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        processed = piece_recognizer.preprocess_square(test_square)
        
        assert processed.shape == (1, 50, 50, 3)
        assert processed.dtype == np.float32
        assert np.all(processed >= 0) and np.all(processed <= 1)
        
        # Test with different size
        test_square_large = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        processed_large = piece_recognizer.preprocess_square(test_square_large)
        
        assert processed_large.shape == (1, 50, 50, 3)
    
    def test_recognize(self, piece_recognizer):
        """Test piece recognition."""
        # Create test square
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        
        # Mock model prediction
        mock_predictions = np.zeros((1, 13))
        mock_predictions[0, 1] = 0.9  # High confidence for white pawn
        piece_recognizer.model.predict = Mock(return_value=mock_predictions)
        
        piece = piece_recognizer.recognize(test_square)
        
        assert piece is not None
        assert piece.piece_type == chess.PAWN
        assert piece.color == chess.WHITE
    
    def test_recognize_empty_square(self, piece_recognizer):
        """Test recognition of empty square."""
        # Create test square
        test_square = np.zeros((50, 50, 3), dtype=np.uint8)
        
        # Mock model prediction
        mock_predictions = np.zeros((1, 13))
        mock_predictions[0, 0] = 0.95  # High confidence for empty
        piece_recognizer.model.predict = Mock(return_value=mock_predictions)
        
        piece = piece_recognizer.recognize(test_square)
        
        assert piece is None
    
    def test_recognize_low_confidence(self, piece_recognizer):
        """Test recognition with low confidence."""
        # Create test square
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        
        # Mock model prediction with low confidence
        mock_predictions = np.ones((1, 13)) / 13  # Equal probability for all
        piece_recognizer.model.predict = Mock(return_value=mock_predictions)
        
        piece = piece_recognizer.recognize(test_square)
        
        assert piece is None  # Should return None due to low confidence
