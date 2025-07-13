import pytest
import numpy as np
import cv2
import chess
from unittest.mock import Mock, patch, MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.detection.board_detector import BoardDetector
from src.detection.piece_recognizer import PieceRecognizer
class TestBoardDetector:
    @pytest.fixture
    def mock_video_capture(self):
        with patch('cv2.VideoCapture') as mock_capture:
            mock_instance = MagicMock()
            mock_capture.return_value = mock_instance
            yield mock_instance
    @pytest.fixture
    def board_detector(self, mock_video_capture):
        detector = BoardDetector(camera_index=0)
        return detector
    def test_initialization(self, board_detector):
        assert board_detector.camera_index == 0
        assert board_detector.board_size == (8, 8)
        assert board_detector.piece_recognizer is not None
    def test_capture_frame_success(self, board_detector, mock_video_capture):
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_video_capture.read.return_value = (True, test_frame)
        frame = board_detector.capture_frame()
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        mock_video_capture.read.assert_called_once()
    def test_capture_frame_failure(self, board_detector, mock_video_capture):
        mock_video_capture.read.return_value = (False, None)
        with pytest.raises(RuntimeError, match="Failed to capture frame"):
            board_detector.capture_frame()
    def test_preprocess(self, board_detector):
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        processed = board_detector.preprocess(test_frame)
        assert len(processed.shape) == 2
        assert processed.shape[:2] == test_frame.shape[:2]
    @patch('cv2.findChessboardCorners')
    def test_detect_board_success(self, mock_find_corners, board_detector):
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_corners = np.random.rand(64, 1, 2).astype(np.float32)
        mock_find_corners.return_value = (True, mock_corners)
        corners = board_detector.detect_board(test_frame)
        assert corners is not None
        assert corners.shape == mock_corners.shape
    @patch('cv2.findChessboardCorners')
    def test_detect_board_failure(self, mock_find_corners, board_detector):
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_find_corners.return_value = (False, None)
        with pytest.raises(RuntimeError, match="Chessboard not detected"):
            board_detector.detect_board(test_frame)
    def test_recognize_piece(self, board_detector):
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        board_detector.piece_recognizer.recognize = Mock(return_value=chess.Piece(chess.PAWN, chess.WHITE))
        piece = board_detector.recognize_piece(test_square)
        assert piece is not None
        assert piece.piece_type == chess.PAWN
        assert piece.color == chess.WHITE
    @patch('cv2.findChessboardCorners')
    @patch('cv2.findHomography')
    @patch('cv2.warpPerspective')
    def test_get_fen_from_image(self, mock_warp, mock_homography, mock_find_corners, board_detector):
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_corners = np.array([[[100, 100]], [[300, 100]], [[300, 300]], [[100, 300]]], dtype=np.float32)
        mock_find_corners.return_value = (True, mock_corners)
        mock_homography.return_value = (np.eye(3), None)
        warped_image = np.zeros((400, 400, 3), dtype=np.uint8)
        mock_warp.return_value = warped_image
        board_detector.piece_recognizer.recognize = Mock(return_value=None)
        fen = board_detector.get_fen_from_image(test_frame)
        assert isinstance(fen, str)
        assert fen == chess.Board.empty().fen()
class TestPieceRecognizer:
    @pytest.fixture
    def piece_recognizer(self):
        return PieceRecognizer()
    def test_initialization(self, piece_recognizer):
        assert piece_recognizer.model is not None
        assert len(piece_recognizer.PIECE_CLASSES) == 13
    def test_build_model(self, piece_recognizer):
        model = piece_recognizer.build_model()
        assert model is not None
        assert model.input_shape == (None, 50, 50, 3)
        assert model.output_shape == (None, 13)
    def test_preprocess_square(self, piece_recognizer):
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        processed = piece_recognizer.preprocess_square(test_square)
        assert processed.shape == (1, 50, 50, 3)
        assert processed.dtype == np.float32
        assert np.all(processed >= 0) and np.all(processed <= 1)
        test_square_large = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        processed_large = piece_recognizer.preprocess_square(test_square_large)
        assert processed_large.shape == (1, 50, 50, 3)
    def test_recognize(self, piece_recognizer):
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        mock_predictions = np.zeros((1, 13))
        mock_predictions[0, 1] = 0.9
        piece_recognizer.model.predict = Mock(return_value=mock_predictions)
        piece = piece_recognizer.recognize(test_square)
        assert piece is not None
        assert piece.piece_type == chess.PAWN
        assert piece.color == chess.WHITE
    def test_recognize_empty_square(self, piece_recognizer):
        test_square = np.zeros((50, 50, 3), dtype=np.uint8)
        mock_predictions = np.zeros((1, 13))
        mock_predictions[0, 0] = 0.95
        piece_recognizer.model.predict = Mock(return_value=mock_predictions)
        piece = piece_recognizer.recognize(test_square)
        assert piece is None
    def test_recognize_low_confidence(self, piece_recognizer):
        test_square = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        mock_predictions = np.ones((1, 13)) / 13
        piece_recognizer.model.predict = Mock(return_value=mock_predictions)
        piece = piece_recognizer.recognize(test_square)
        assert piece is None
