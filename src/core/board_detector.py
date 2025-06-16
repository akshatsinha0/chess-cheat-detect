# src/detection/board_detector.py

import cv2
import numpy as np
import chess

class BoardDetector:
    def __init__(self, camera_index=0, board_size=(8, 8)):
        """
        Initialize the board detector.
        Args:
            camera_index (int): Webcam device index.
            board_size (tuple): Number of squares (rows, cols).
        """
        self.camera_index = camera_index
        self.board_size = board_size
        self.capture = cv2.VideoCapture(self.camera_index)

    def capture_frame(self):
        """
        Capture a single video frame from the camera.
        Returns:
            frame (ndarray): BGR image frame.
        """
        ret, frame = self.capture.read()
        if not ret:
            raise RuntimeError("Failed to capture frame from camera")  
        return frame

    def preprocess(self, frame):
        """
        Convert to grayscale and apply Gaussian blur.
        Args:
            frame (ndarray): Original BGR frame.
        Returns:
            gray (ndarray): Preprocessed grayscale image.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        return gray

    def detect_board(self, frame):
        """
        Detect the chessboard corners using OpenCV.
        Args:
            frame (ndarray): Preprocessed frame.
        Returns:
            corners (ndarray): Array of board corner points.
        """
        gray = self.preprocess(frame)
        ret, corners = cv2.findChessboardCorners(gray, self.board_size, None)
        if not ret:
            raise RuntimeError("Chessboard not detected")  
        return corners

    def get_fen_from_image(self, frame):
        """
        Extract FEN notation from the board image.
        Args:
            frame (ndarray): BGR frame.
        Returns:
            fen (str): FEN string of current position.
        """
        corners = self.detect_board(frame)
        # Perspective transform to get top-down view
        pts_src = corners.reshape(-1, 2)[:4]
        pts_dst = np.array([[0,0], [400,0], [400,400], [0,400]], dtype='float32')
        h, _ = cv2.findHomography(pts_src, pts_dst)
        warp = cv2.warpPerspective(frame, h, (400, 400))
        
        # Divide into 8x8 squares and classify pieces (placeholder logic)
        square_size = 50
        board = chess.Board.empty()
        for row in range(8):
            for col in range(8):
                x, y = col * square_size, row * square_size
                square_img = warp[y:y+square_size, x:x+square_size]
                # TODO: Add piece recognition model here
                # Example: piece = self.recognize_piece(square_img)
                # if piece: board.set_piece_at(chess.square(col, 7-row), piece)
        
        return board.fen()
