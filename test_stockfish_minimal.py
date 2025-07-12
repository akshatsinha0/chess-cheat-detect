from stockfish import Stockfish
import os

# Use the same path as in config.py
stockfish_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'stockfish', 'stockfish-ubuntu-x86-64-avx2')

print(f"Using Stockfish binary at: {stockfish_path}")

try:
    stockfish = Stockfish(path=stockfish_path, depth=15)
    print("Stockfish process started successfully.")
    print("Stockfish info:", stockfish.get_parameters())
    print("Best move from starting position:", stockfish.get_best_move())
except Exception as e:
    print("Error starting Stockfish:", e) 