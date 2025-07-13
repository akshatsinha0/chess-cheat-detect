
import cv2
import numpy as np
import chess
from .piece_recognizer import PieceRecognizer
class BoardDetector:
    def __init__(self, camera_index=0, board_size=(8, 8), piece_model_path=None):
        self.camera_index = camera_index
        self.board_size = board_size
        self.capture = cv2.VideoCapture(self.camera_index)
        if piece_model_path is None:
            piece_model_path = "models/piece_recognizer.h5"
        self.piece_recognizer = PieceRecognizer(piece_model_path)
    def capture_frame(self):
        ret, frame = self.capture.read()
        if not ret:
            raise RuntimeError("Failed to capture frame from camera")
        return frame
    def preprocess(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        return gray
    def detect_board(self, frame):
        gray = self.preprocess(frame)
        ret, corners = cv2.findChessboardCorners(gray, self.board_size, None)
        if not ret:
            raise RuntimeError("Chessboard not detected")
        return corners
    def recognize_piece(self, square_img):
        return self.piece_recognizer.recognize(square_img)
    def get_fen_from_image(self, frame):
        corners = self.detect_board(frame)
        pts_src = corners.reshape(-1, 2)[:4]
        pts_dst = np.array([[0,0], [400,0], [400,400], [0,400]], dtype='float32')
        h, _ = cv2.findHomography(pts_src, pts_dst)
        warp = cv2.warpPerspective(frame, h, (400, 400))
        square_size = 50
        board = chess.Board.empty()
        for row in range(8):
            for col in range(8):
                x, y = col * square_size, row * square_size
                square_img = warp[y:y+square_size, x:x+square_size]
                piece = self.recognize_piece(square_img)
                if piece:
                    board.set_piece_at(chess.square(col, 7-row), piece)
        return board.fen()
