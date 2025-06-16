# src/core/stockfish_engine.py

import os
from stockfish import Stockfish

# Compute project root (two levels up: src/core → src → project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Python os.path docs[4]

# Align path to Dockerfile’s COPY destination: /app/engine/stockfish
ENGINE_PATH = os.path.join(BASE_DIR, "engine", "stockfish")
ENGINE_PATH = os.path.abspath(ENGINE_PATH)

# Initialize Stockfish engine at the correct path with a default depth of 15 plies
stockfish = Stockfish(path=ENGINE_PATH, depth=15)  # stockfish PyPI wrapper[5]

def analyze_position(fen: str, depth: int = 15):
    """
    Analyze a chess position using Stockfish and return best move and evaluation.
    """
    stockfish.set_depth(depth)
    stockfish.set_fen_position(fen)
    return {
        "best_move": stockfish.get_best_move(),
        "evaluation": stockfish.get_evaluation()
    }
