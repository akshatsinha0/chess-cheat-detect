# src/core/stockfish_engine.py

import os
from stockfish import Stockfish

# Determine the path to the Stockfish binary located in the bin directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_PATH = os.path.join(BASE_DIR, "bin", "stockfish")

# Initialize Stockfish with a default depth of 15 plies
stockfish = Stockfish(path=ENGINE_PATH, depth=15)

def analyze_position(fen: str, depth: int = 15):
    """
    Analyze a chess position using Stockfish and return best move and evaluation.
    
    Args:
        fen (str): Forsyth-Edwards Notation of the board position.
        depth (int): Search depth for the engine analysis.

    Returns:
        dict: {
            "best_move": str,        # e.g., "e2e4"
            "evaluation": dict       # e.g., {"type": "cp", "value": 20}
        }
    """
    stockfish.set_depth(depth)
    stockfish.set_fen_position(fen)
    best_move = stockfish.get_best_move()
    evaluation = stockfish.get_evaluation()
    return {
        "best_move": best_move,
        "evaluation": evaluation
    }
