import os
import sys
from src.core.stockfish_engine import stockfish
from src.detection.board_detector import BoardDetector
from src.ml.anomaly_detector import AnomalyDetector

def initialize_components():
    print("Stockfish engine initialized:", stockfish.get_parameters())
    board_detector = BoardDetector(camera_index=0)
    print("Board detector initialized:", board_detector)
    anomaly_detector = AnomalyDetector(model_path=os.path.join('models', 'cheat_detector.h5'))
    print("Anomaly detector initialized:", anomaly_detector)
    return board_detector, anomaly_detector

def main():
    board_detector, anomaly_detector = initialize_components()
    try:
        while True:
            frame = board_detector.capture_frame()
            fen = board_detector.get_fen_from_image(frame)
            print("Current FEN:", fen)
            stockfish.set_fen_position(fen)
            best_move = stockfish.get_best_move()
            evaluation = stockfish.get_evaluation()
            print(f"Best move: {best_move}, Evaluation: {evaluation}")
            suspicion_score = anomaly_detector.predict_suspicion(fen, best_move, evaluation)
            print("Suspicion score:", suspicion_score)
            if suspicion_score > anomaly_detector.threshold:
                print("Alert: Potential cheating detected!")
    except KeyboardInterrupt:
        print("Exiting real-time cheat detection.")

if __name__ == "__main__":
    main()
