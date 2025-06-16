# config.py

import os

# Base project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the Stockfish engine binary
STOCKFISH_PATH = os.path.join(BASE_DIR, "bin", "stockfish")

# Default search depth for Stockfish analysis
STOCKFISH_DEPTH = 15

# TensorFlow model directory for anomaly detection
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_FILE = os.path.join(MODEL_DIR, "cheat_detector.h5")

# Camera index for board capture (0 = default webcam)
CAMERA_INDEX = 0

# Threshold above which cheating is flagged (0–1 scale)
SUSPICION_THRESHOLD = 0.5
