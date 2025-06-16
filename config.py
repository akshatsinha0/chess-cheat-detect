import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOCKFISH_PATH = os.path.join(
    BASE_DIR,
    "bin",
    "stockfish",
    "stockfish-windows-x86-64-avx2.exe"
)
STOCKFISH_DEPTH = 15
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_FILE = os.path.join(MODEL_DIR, "cheat_detector.h5")
CAMERA_INDEX = 0
SUSPICION_THRESHOLD = 0.5
