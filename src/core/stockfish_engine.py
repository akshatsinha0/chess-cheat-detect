# src/core/stockfish_engine.py

import os
from stockfish import Stockfish
from config import STOCKFISH_PATH

# Initialize Stockfish engine
stockfish = Stockfish(path=STOCKFISH_PATH, depth=15)

def analyze_position(fen: str, depth: int = 15):
    stockfish.set_depth(depth)
    stockfish.set_fen_position(fen)
    return {
        "best_move": stockfish.get_best_move(),
        "evaluation": stockfish.get_evaluation()
    }
