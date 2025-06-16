# src/core/stockfish_engine.py

import os
from stockfish import Stockfish

# Project root (/app)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Align to container’s engine directory
ENGINE_PATH = os.path.join(BASE_DIR, "engine", "stockfish")
ENGINE_PATH = os.path.abspath(ENGINE_PATH)

# Initialize Stockfish engine
stockfish = Stockfish(path=ENGINE_PATH, depth=15)

def analyze_position(fen: str, depth: int = 15):
    stockfish.set_depth(depth)
    stockfish.set_fen_position(fen)
    return {
        "best_move": stockfish.get_best_move(),
        "evaluation": stockfish.get_evaluation()
    }
