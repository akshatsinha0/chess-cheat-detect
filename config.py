import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCKER_ENGINE = os.path.join(BASE_DIR, "engine", "stockfish")
LINUX_ENGINE = os.path.join(BASE_DIR, "bin", "stockfish", "stockfish-ubuntu-x86-64-avx2")
WINDOWS_ENGINE = os.path.join(BASE_DIR, "bin", "stockfish", "stockfish-windows-x86-64-avx2.exe")
if os.path.isfile(DOCKER_ENGINE):
    STOCKFISH_PATH = DOCKER_ENGINE
elif sys.platform.startswith("win"):
    STOCKFISH_PATH = WINDOWS_ENGINE
else:
    STOCKFISH_PATH = LINUX_ENGINE
STOCKFISH_DEPTH = 15
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_FILE = os.path.join(MODEL_DIR, "cheat_detector.h5")
CAMERA_INDEX = 0
SUSPICION_THRESHOLD = 0.5
