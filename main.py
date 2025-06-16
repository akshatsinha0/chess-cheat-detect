# main.py

import os
import sys
from src.core.stockfish_engine import stockfish
from src.detection.board_detector import BoardDetector
from src.ml.anomaly_detector import AnomalyDetector

def initialize_components():
    """
    Initialize all core components:
    - Stockfish for move analysis
    - BoardDetector for capturing and interpreting board images
    - AnomalyDetector for detecting suspicious play patterns
    """
    # Stockfish is initialized in its module
    print("Stockfish engine initialized:", stockfish.get_parameters())

    # Initialize board detector
    board_detector = BoardDetector(camera_index=0)
    print("Board detector initialized:", board_detector)

    # Initialize anomaly detector
    anomaly_detector = AnomalyDetector(model_path=os.path.join('models', 'cheat_detector.h5'))
    print("Anomaly detector initialized:", anomaly_detector)

    return board_detector, anomaly_detector

def main():
    """
    Main workflow:
    1. Capture board image
    2. Extract current position
    3. Analyze moves via Stockfish
    4. Run anomaly detection
    5. Alert if cheating is suspected
    """
    board_detector, anomaly_detector = initialize_components()

    try:
        while True:
            # 1. Capture board image
            frame = board_detector.capture_frame()
            
            # 2. Extract moves and current FEN
            fen = board_detector.get_fen_from_image(frame)
            print("Current FEN:", fen)

            # 3. Analyze best move and evaluation
            stockfish.set_fen_position(fen)
            best_move = stockfish.get_best_move()
            evaluation = stockfish.get_evaluation()
            print(f"Best move: {best_move}, Evaluation: {evaluation}")

            # 4. Check for anomalies
            suspicion_score = anomaly_detector.predict_suspicion(fen, best_move, evaluation)
            print("Suspicion score:", suspicion_score)

            # 5. Alert if necessary
            if suspicion_score > anomaly_detector.threshold:
                print("Alert: Potential cheating detected!")

    except KeyboardInterrupt:
        print("Exiting real-time cheat detection.")

if __name__ == "__main__":
    main()
