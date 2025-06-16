# src/ui/app.py

import tkinter as tk
from tkinter import messagebox
import chess
import chess.svg
from PIL import Image, ImageTk
from src.core.stockfish_engine import analyze_position
from src.ml.anomaly_detector import AnomalyDetector
from config import STOCKFISH_DEPTH, MODEL_FILE, SUSPICION_THRESHOLD

class CheatDetectionApp:
    def __init__(self, root):
        """
        Initialize the GUI application.
        """
        self.root = root
        self.root.title("Chess Cheat Detection")
        self.board = chess.Board()
        self.anomaly_detector = AnomalyDetector(model_path=MODEL_FILE,
                                                threshold=SUSPICION_THRESHOLD)
        # Create UI elements
        self.canvas = tk.Canvas(root, width=400, height=400)
        self.canvas.pack(pady=10)
        self.move_entry = tk.Entry(root, width=10)
        self.move_entry.pack(pady=5)
        self.submit_btn = tk.Button(root, text="Make Move", command=self.make_move)
        self.submit_btn.pack(pady=5)
        self.detect_btn = tk.Button(root, text="Detect Cheat", command=self.detect_cheat)
        self.detect_btn.pack(pady=5)
        self.status_label = tk.Label(root, text="Enter moves in algebraic notation", fg="blue")
        self.status_label.pack(pady=10)
        # Render initial board
        self.update_board()

    def update_board(self):
        """
        Render the current chess position on the canvas.
        """
        svg_data = chess.svg.board(self.board, size=400)
        img = Image.open(io.BytesIO(svg_data.encode('utf-8')))
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

    def make_move(self):
        """
        Apply the move from the entry to the board.
        """
        move_san = self.move_entry.get()
        try:
            move = self.board.parse_san(move_san)
            self.board.push(move)
            self.move_entry.delete(0, tk.END)
            self.update_board()
            self.status_label.config(text=f"Move played: {move_san}", fg="green")
        except ValueError:
            messagebox.showerror("Invalid Move", "Please enter a valid move notation")
            self.status_label.config(text="Invalid move entered", fg="red")

    def detect_cheat(self):
        """
        Analyze the completed game for cheating likelihood.
        """
        fen = self.board.fen()
        # Stockfish analysis
        result = analyze_position(fen, depth=STOCKFISH_DEPTH)
        best_move, evaluation = result["best_move"], result["evaluation"]
        # Anomaly detection
        score = self.anomaly_detector.predict_suspicion(fen, best_move, evaluation)
        percent = round(score * 100, 2)
        messagebox.showinfo("Cheat Detection Result",
                            f"Cheating likelihood: {percent}%")
        self.status_label.config(text=f"Cheat likelihood: {percent}%", fg="purple")


if __name__ == "__main__":
    root = tk.Tk()
    app = CheatDetectionApp(root)
    root.mainloop()
