# config.py

import os

# Base project directory (directory containing this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # [1]

# Determine Stockfish engine path:
# - In Docker: /app/engine/stockfish
# - Locally:   bin/stockfish/stockfish-ubuntu-x86-64-avx2
DOCKER_ENGINE = os.path.join(BASE_DIR, "engine", "stockfish")  # [2]
LOCAL_ENGINE  = os.path.join(BASE_DIR, "bin", "stockfish", "stockfish-ubuntu-x86-64-avx2")  # [3]
STOCKFISH_PATH = DOCKER_ENGINE if os.path.isfile(DOCKER_ENGINE) else LOCAL_ENGINE  # [4]

# Default search depth for Stockfish analysis (in plies)
STOCKFISH_DEPTH = 15  # [5]

# TensorFlow model directory and file for anomaly detection
MODEL_DIR  = os.path.join(BASE_DIR, "models")           # [6]
MODEL_FILE = os.path.join(MODEL_DIR, "cheat_detector.h5")  # [7]

# Camera index for board capture (0 = default webcam)
CAMERA_INDEX = 0  # [8]

# Threshold above which cheating is flagged (0.0–1.0 scale)
SUSPICION_THRESHOLD = 0.5  # [9]
