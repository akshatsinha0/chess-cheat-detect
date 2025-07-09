# config.py

import os
import sys

# Base project directory (directory containing this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # [1]

# Determine Stockfish engine path:
# - In Docker: /app/engine/stockfish
# - Locally:   bin/stockfish/stockfish-ubuntu-x86-64-avx2
DOCKER_ENGINE = os.path.join(BASE_DIR, "engine", "stockfish")  # [2]
LINUX_ENGINE  = os.path.join(BASE_DIR, "bin", "stockfish", "stockfish-ubuntu-x86-64-avx2")  # [3]
WINDOWS_ENGINE = os.path.join(BASE_DIR, "bin", "stockfish", "stockfish-windows-x86-64-avx2.exe")  # [4]

if os.path.isfile(DOCKER_ENGINE):
    STOCKFISH_PATH = DOCKER_ENGINE
elif sys.platform.startswith("win"):
    STOCKFISH_PATH = WINDOWS_ENGINE
else:
    STOCKFISH_PATH = LINUX_ENGINE

# Default search depth for Stockfish analysis (in plies)
STOCKFISH_DEPTH = 15  # [5]

# TensorFlow model directory and file for anomaly detection
MODEL_DIR  = os.path.join(BASE_DIR, "models")           # [6]
MODEL_FILE = os.path.join(MODEL_DIR, "cheat_detector.h5")  # [7]

# Camera index for board capture (0 = default webcam)
CAMERA_INDEX = 0  # [8]

# Threshold above which cheating is flagged (0.0–1.0 scale)
SUSPICION_THRESHOLD = 0.5  # [9]
