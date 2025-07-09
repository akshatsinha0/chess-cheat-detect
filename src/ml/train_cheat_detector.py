# src/ml/train_cheat_detector.py

import os
import argparse
import numpy as np
import pandas as pd
import chess
import chess.pgn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras import layers, models
from datetime import datetime
import json
import io

# Import our modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.core.stockfish_engine import analyze_position

class CheatDetectorTrainer:
    """
    Train a sophisticated chess cheat detection model using various features.
    """
    
    def __init__(self, data_dir='data/games', model_path='models/cheat_detector_v2.h5'):
        self.data_dir = data_dir
        self.model_path = model_path
        self.scaler = StandardScaler()
        
    def extract_features_from_game(self, pgn_game, is_cheater=False):
        """
        Extract features from a chess game for training.
        Features include:
        - Move accuracy compared to engine
        - Time per move variance
        - Complexity of positions
        - Accuracy in critical positions
        - Consistency of play strength
        """
        board = pgn_game.board()
        features_list = []
        
        move_num = 0
        accuracies = []
        eval_differences = []
        move_times = []
        critical_accuracies = []
        
        for node in pgn_game.mainline():
            move_num += 1
            board.push(node.move)
            
            # Get position analysis
            analysis = analyze_position(board.fen(), depth=15)
            best_move = analysis['best_move']
            eval_score = analysis['evaluation']['value']
            
            # Check if player's move matches engine's best move
            move_accuracy = 1.0 if node.move.uci() == best_move else 0.0
            accuracies.append(move_accuracy)
            
            # Get evaluation difference if move wasn't best
            if node.move.uci() != best_move:
                board.pop()
                board.push(chess.Move.from_uci(best_move))
                best_eval = analyze_position(board.fen(), depth=10)['evaluation']['value']
                board.pop()
                board.push(node.move)
                
                eval_diff = abs(eval_score - best_eval)
                eval_differences.append(eval_diff)
            else:
                eval_differences.append(0)
            
            # Extract move time if available
            if node.clock() is not None:
                move_times.append(node.clock())
            
            # Check if position is critical (evaluation > 200 or < -200 centipawns)
            if abs(eval_score) > 200:
                critical_accuracies.append(move_accuracy)
            
            # Extract features for this position
            features = self.extract_position_features(
                board, 
                move_accuracy, 
                eval_score, 
                move_num,
                is_cheater
            )
            features_list.append(features)
        
        # Calculate aggregate statistics
        avg_accuracy = np.mean(accuracies) if accuracies else 0
        accuracy_variance = np.var(accuracies) if len(accuracies) > 1 else 0
        avg_eval_diff = np.mean(eval_differences) if eval_differences else 0
        critical_accuracy = np.mean(critical_accuracies) if critical_accuracies else avg_accuracy
        
        # Time variance (if move times available)
        time_variance = np.var(move_times) if len(move_times) > 1 else 0
        
        # Add game-level features to all positions
        for features in features_list:
            features.extend([
                avg_accuracy,
                accuracy_variance,
                avg_eval_diff,
                critical_accuracy,
                time_variance
            ])
        
        return features_list
    
    def extract_position_features(self, board, move_accuracy, eval_score, move_num, is_cheater):
        """
        Extract features from a single position.
        """
        features = []
        
        # Basic features
        features.append(move_accuracy)
        features.append(eval_score / 100.0)  # Normalize centipawns
        features.append(move_num / 40.0)  # Normalize move number
        
        # Position complexity features
        legal_moves = len(list(board.legal_moves))
        features.append(legal_moves / 50.0)  # Normalize
        
        # Material balance
        white_material = sum([
            len(board.pieces(piece_type, chess.WHITE)) * value
            for piece_type, value in [
                (chess.PAWN, 1), (chess.KNIGHT, 3), (chess.BISHOP, 3),
                (chess.ROOK, 5), (chess.QUEEN, 9)
            ]
        ])
        black_material = sum([
            len(board.pieces(piece_type, chess.BLACK)) * value
            for piece_type, value in [
                (chess.PAWN, 1), (chess.KNIGHT, 3), (chess.BISHOP, 3),
                (chess.ROOK, 5), (chess.QUEEN, 9)
            ]
        ])
        material_balance = (white_material - black_material) / 10.0
        features.append(material_balance)
        
        # Game phase (opening/middlegame/endgame)
        total_pieces = len(board.piece_map())
        game_phase = total_pieces / 32.0
        features.append(game_phase)
        
        # Check/capture indicators
        features.append(1.0 if board.is_check() else 0.0)
        features.append(1.0 if board.is_capture(board.peek()) else 0.0)
        
        # Cheater label
        features.append(1.0 if is_cheater else 0.0)
        
        return features
    
    def load_games_from_pgn(self, pgn_file, is_cheater=False, max_games=None):
        """
        Load games from a PGN file and extract features.
        """
        all_features = []
        all_labels = []
        
        with open(pgn_file, 'r') as f:
            game_count = 0
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                
                if max_games and game_count >= max_games:
                    break
                
                try:
                    features_list = self.extract_features_from_game(game, is_cheater)
                    for features in features_list:
                        # Remove the cheater label from features (it's the label)
                        label = features.pop()
                        all_features.append(features)
                        all_labels.append(label)
                    
                    game_count += 1
                    if game_count % 10 == 0:
                        print(f"Processed {game_count} games from {pgn_file}")
                        
                except Exception as e:
                    print(f"Error processing game: {e}")
                    continue
        
        return np.array(all_features), np.array(all_labels)
    
    def prepare_training_data(self):
        """
        Load and prepare training data from PGN files.
        """
        print("Loading training data...")
        
        # Create sample data if no real data exists
        if not os.path.exists(self.data_dir):
            print("No game data found. Creating synthetic training data...")
            return self.create_synthetic_data()
        
        all_features = []
        all_labels = []
        
        # Load legitimate games
        legit_dir = os.path.join(self.data_dir, 'legitimate')
        if os.path.exists(legit_dir):
            for pgn_file in os.listdir(legit_dir):
                if pgn_file.endswith('.pgn'):
                    filepath = os.path.join(legit_dir, pgn_file)
                    features, labels = self.load_games_from_pgn(filepath, is_cheater=False)
                    all_features.extend(features)
                    all_labels.extend(labels)
        
        # Load cheater games
        cheater_dir = os.path.join(self.data_dir, 'cheaters')
        if os.path.exists(cheater_dir):
            for pgn_file in os.listdir(cheater_dir):
                if pgn_file.endswith('.pgn'):
                    filepath = os.path.join(cheater_dir, pgn_file)
                    features, labels = self.load_games_from_pgn(filepath, is_cheater=True)
                    all_features.extend(features)
                    all_labels.extend(labels)
        
        if not all_features:
            print("No PGN files found. Creating synthetic training data...")
            return self.create_synthetic_data()
        
        X = np.array(all_features)
        y = np.array(all_labels)
        
        # Normalize features
        X = self.scaler.fit_transform(X)
        
        return train_test_split(X, y, test_size=0.2, random_state=42)
    
    def create_synthetic_data(self):
        """
        Create synthetic training data for demonstration.
        """
        np.random.seed(42)
        n_samples = 10000
        n_features = 13  # Match the number of features from extract_position_features + game-level features
        
        # Generate legitimate player data
        X_legit = np.random.randn(n_samples // 2, n_features)
        X_legit[:, 0] = np.random.beta(2, 5, n_samples // 2)  # Lower move accuracy
        X_legit[:, 8] = np.random.beta(2, 5, n_samples // 2)  # Lower average accuracy
        X_legit[:, 9] = np.random.uniform(0.1, 0.3, n_samples // 2)  # Higher variance
        y_legit = np.zeros(n_samples // 2)
        
        # Generate cheater data
        X_cheat = np.random.randn(n_samples // 2, n_features)
        X_cheat[:, 0] = np.random.beta(9, 2, n_samples // 2)  # Higher move accuracy
        X_cheat[:, 8] = np.random.beta(9, 2, n_samples // 2)  # Higher average accuracy
        X_cheat[:, 9] = np.random.uniform(0, 0.1, n_samples // 2)  # Lower variance
        X_cheat[:, 11] = np.random.beta(9, 2, n_samples // 2)  # High critical accuracy
        y_cheat = np.ones(n_samples // 2)
        
        X = np.vstack([X_legit, X_cheat])
        y = np.hstack([y_legit, y_cheat])
        
        # Shuffle
        indices = np.random.permutation(n_samples)
        X = X[indices]
        y = y[indices]
        
        # Normalize
        X = self.scaler.fit_transform(X)
        
        return train_test_split(X, y, test_size=0.2, random_state=42)
    
    def build_model(self, input_dim):
        """
        Build a sophisticated neural network for cheat detection.
        """
        model = models.Sequential([
            layers.Input(shape=(input_dim,)),
            
            # First block
            layers.Dense(128, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            # Second block
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            
            # Third block
            layers.Dense(32, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            # Fourth block
            layers.Dense(16, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            # Output
            layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
        )
        
        return model
    
    def train(self, epochs=50, batch_size=32):
        """
        Train the cheat detection model.
        """
        # Prepare data
        X_train, X_test, y_train, y_test = self.prepare_training_data()
        
        print(f"Training data shape: {X_train.shape}")
        print(f"Test data shape: {X_test.shape}")
        print(f"Positive samples in training: {np.sum(y_train)} ({np.mean(y_train)*100:.1f}%)")
        
        # Build model
        model = self.build_model(X_train.shape[1])
        model.summary()
        
        # Create callbacks
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                patience=10,
                restore_best_weights=True,
                monitor='val_auc',
                mode='max'
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                patience=5,
                factor=0.5,
                monitor='val_auc',
                mode='max'
            ),
            tf.keras.callbacks.ModelCheckpoint(
                self.model_path,
                save_best_only=True,
                monitor='val_auc',
                mode='max'
            )
        ]
        
        # Train model
        history = model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluate
        test_loss, test_acc, test_auc = model.evaluate(X_test, y_test)
        print(f"\nTest Accuracy: {test_acc:.4f}")
        print(f"Test AUC: {test_auc:.4f}")
        
        # Save training history
        history_path = self.model_path.replace('.h5', '_history.json')
        with open(history_path, 'w') as f:
            json.dump(history.history, f)
        
        # Save scaler
        scaler_path = self.model_path.replace('.h5', '_scaler.pkl')
        import joblib
        joblib.dump(self.scaler, scaler_path)
        
        print(f"\nModel saved to: {self.model_path}")
        print(f"Scaler saved to: {scaler_path}")
        print(f"Training history saved to: {history_path}")
        
        return model, history

def main():
    parser = argparse.ArgumentParser(description="Train chess cheat detection model")
    parser.add_argument('--data-dir', type=str, default='data/games',
                        help='Directory containing PGN files')
    parser.add_argument('--model-path', type=str, default='models/cheat_detector_v2.h5',
                        help='Path to save trained model')
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Training batch size')
    
    args = parser.parse_args()
    
    trainer = CheatDetectorTrainer(args.data_dir, args.model_path)
    trainer.train(args.epochs, args.batch_size)

if __name__ == "__main__":
    main()
