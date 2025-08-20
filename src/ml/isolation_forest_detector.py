

import numpy as np
import pandas as pd
import pickle
import json
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import tensorflow as tf
from tensorflow import keras
import chess
import chess.engine
import logging
from datetime import datetime
import mysql.connector
from config import STOCKFISH_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedAnomalyDetector:
    """
    Advanced anomaly detection system using Isolation Forest and Neural Networks
    """
    
    def __init__(self, 
                 contamination: float = 0.1,
                 n_estimators: int = 200,
                 max_samples: int = 256,
                 random_state: int = 42):
        """
        Initialize the enhanced anomaly detector
        
        Args:
            contamination: Expected proportion of outliers in the dataset
            n_estimators: Number of trees in the forest
            max_samples: Number of samples to draw from X to train each estimator
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state
        
        # Initialize Isolation Forest
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1
        )
        
        # Initialize scaler for feature normalization
        self.scaler = StandardScaler()
        
        # Neural network for deep feature learning
        self.neural_model = None
        
        # Feature importance weights
        self.feature_weights = {
            'move_accuracy': 2.0,
            'consistency_score': 1.8,
            'time_management': 1.5,
            'opening_deviation': 1.3,
            'critical_accuracy': 2.5,
            'blunder_rate': 1.7,
            'entropy': 1.4,
            'think_time_variance': 1.6,
            'endgame_accuracy': 1.9,
            'tactical_sharpness': 2.1
        }
        
        # Cohort-based thresholds
        self.cohort_thresholds = {}
        
        # Database connection
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'chess_cheat_detection'
        }
    
    def extract_comprehensive_features(self, 
                                      fen: str, 
                                      move_history: List[str],
                                      player_data: Dict,
                                      game_data: Dict) -> np.ndarray:
        """
        Extract comprehensive features for anomaly detection
        
        Args:
            fen: Current board position in FEN notation
            move_history: List of moves played so far
            player_data: Player profile and historical data
            game_data: Current game metadata
            
        Returns:
            Feature vector as numpy array
        """
        features = []
        
        # Position evaluation features
        board = chess.Board(fen)
        
        # Material balance
        material_balance = self._calculate_material_balance(board)
        features.append(material_balance)
        
        # Position complexity
        complexity = self._calculate_position_complexity(board)
        features.append(complexity)
        
        # Move accuracy features
        if move_history:
            accuracy_features = self._calculate_accuracy_features(move_history, player_data)
            features.extend(accuracy_features)
        else:
            features.extend([0] * 5)  # Default values
        
        # Time management features
        time_features = self._calculate_time_features(game_data)
        features.extend(time_features)
        
        # Consistency features
        consistency_features = self._calculate_consistency_features(player_data)
        features.extend(consistency_features)
        
        # Opening book adherence
        opening_score = self._calculate_opening_adherence(move_history, board)
        features.append(opening_score)
        
        # Endgame accuracy (if applicable)
        if self._is_endgame(board):
            endgame_accuracy = self._calculate_endgame_accuracy(board, move_history)
            features.append(endgame_accuracy)
        else:
            features.append(0)
        
        # Session entropy
        entropy = self._calculate_session_entropy(player_data)
        features.append(entropy)
        
        # Sandbagging detection
        sandbagging_score = self._detect_sandbagging(player_data, game_data)
        features.append(sandbagging_score)
        
        # Network jitter profile
        network_features = self._extract_network_features(game_data)
        features.extend(network_features)
        
        # Device fingerprint consistency
        device_consistency = self._check_device_consistency(player_data)
        features.append(device_consistency)
        
        return np.array(features, dtype=np.float32)
    
    def _calculate_material_balance(self, board: chess.Board) -> float:
        """Calculate material balance on the board"""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        
        white_material = 0
        black_material = 0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = piece_values.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    white_material += value
                else:
                    black_material += value
        
        return (white_material - black_material) / 39  # Normalize
    
    def _calculate_position_complexity(self, board: chess.Board) -> float:
        """Calculate position complexity based on legal moves and piece activity"""
        num_legal_moves = len(list(board.legal_moves))
        
        # Check for tactical features
        num_checks = len([m for m in board.legal_moves if board.gives_check(m)])
        num_captures = len([m for m in board.legal_moves if board.is_capture(m)])
        
        complexity = (num_legal_moves / 50) + (num_checks / 5) + (num_captures / 10)
        return min(complexity, 1.0)  # Cap at 1.0
    
    def _calculate_accuracy_features(self, 
                                    move_history: List[str], 
                                    player_data: Dict) -> List[float]:
        """Calculate move accuracy related features"""
        features = []
        
        # Average accuracy
        avg_accuracy = player_data.get('avg_accuracy', 0.5)
        features.append(avg_accuracy)
        
        # Accuracy consistency
        accuracy_std = player_data.get('accuracy_std', 0.15)
        features.append(1 - accuracy_std)  # Higher consistency = lower std
        
        # Critical move accuracy
        critical_accuracy = player_data.get('critical_accuracy', 0.4)
        features.append(critical_accuracy)
        
        # Blunder rate
        blunder_rate = player_data.get('blunder_rate', 0.1)
        features.append(1 - blunder_rate)  # Inverse for consistency
        
        # Engine correlation
        engine_correlation = player_data.get('engine_correlation', 0.3)
        features.append(engine_correlation)
        
        return features
    
    def _calculate_time_features(self, game_data: Dict) -> List[float]:
        """Calculate time management related features"""
        features = []
        
        # Average think time
        avg_think_time = game_data.get('avg_think_time', 5.0)
        features.append(min(avg_think_time / 30, 1.0))  # Normalize to 30 seconds
        
        # Think time variance
        think_time_var = game_data.get('think_time_variance', 3.0)
        features.append(min(think_time_var / 10, 1.0))
        
        # Time pressure performance
        time_pressure_perf = game_data.get('time_pressure_performance', 0.5)
        features.append(time_pressure_perf)
        
        return features
    
    def _calculate_consistency_features(self, player_data: Dict) -> List[float]:
        """Calculate player consistency features"""
        features = []
        
        # Rating volatility
        rating_volatility = player_data.get('rating_volatility', 50)
        features.append(1 - min(rating_volatility / 200, 1.0))
        
        # Performance consistency across games
        perf_consistency = player_data.get('performance_consistency', 0.7)
        features.append(perf_consistency)
        
        # Opening repertoire consistency
        opening_consistency = player_data.get('opening_consistency', 0.6)
        features.append(opening_consistency)
        
        return features
    
    def _calculate_opening_adherence(self, 
                                    move_history: List[str], 
                                    board: chess.Board) -> float:
        """Calculate adherence to opening book"""
        if len(move_history) > 15:
            return 0.5  # Not in opening anymore
        
        # Simplified opening book check (in production, use a real opening database)
        common_openings = [
            ['e4', 'e5', 'Nf3', 'Nc6'],  # Italian/Spanish
            ['d4', 'd5', 'c4'],  # Queen's Gambit
            ['e4', 'c5'],  # Sicilian
            ['d4', 'Nf6', 'c4', 'g6'],  # King's Indian
            ['e4', 'e6'],  # French
            ['e4', 'c6'],  # Caro-Kann
        ]
        
        for opening in common_openings:
            if move_history[:len(opening)] == opening[:len(move_history)]:
                return 1.0
        
        return 0.3  # Unusual opening
    
    def _is_endgame(self, board: chess.Board) -> bool:
        """Check if position is in endgame"""
        # Simple heuristic: few pieces remaining
        piece_count = len(board.piece_map())
        return piece_count <= 10
    
    def _calculate_endgame_accuracy(self, 
                                   board: chess.Board, 
                                   move_history: List[str]) -> float:
        """Calculate endgame accuracy"""
        if not self._is_endgame(board):
            return 0.5
        
        # Simplified endgame accuracy (in production, use tablebase)
        if board.is_checkmate():
            return 1.0
        elif board.is_stalemate():
            return 0.0
        
        # Check for basic endgame patterns
        pieces = board.piece_map()
        if len(pieces) <= 4:  # Very simple endgame
            return 0.8
        
        return 0.6
    
    def _calculate_session_entropy(self, player_data: Dict) -> float:
        """Calculate session entropy (randomness in play pattern)"""
        moves_distribution = player_data.get('moves_distribution', {})
        
        if not moves_distribution:
            return 0.5
        
        total_moves = sum(moves_distribution.values())
        if total_moves == 0:
            return 0.5
        
        entropy = 0
        for count in moves_distribution.values():
            if count > 0:
                p = count / total_moves
                entropy -= p * np.log2(p + 1e-10)
        
        # Normalize entropy (max entropy for uniform distribution)
        max_entropy = np.log2(len(moves_distribution)) if moves_distribution else 1
        return entropy / max_entropy if max_entropy > 0 else 0.5
    
    def _detect_sandbagging(self, player_data: Dict, game_data: Dict) -> float:
        """Detect potential sandbagging behavior"""
        # Check for intentional losses followed by wins
        recent_results = player_data.get('recent_results', [])
        
        if len(recent_results) < 10:
            return 0.0
        
        # Look for patterns like: lose, lose, win, win, win
        sandbagging_score = 0
        for i in range(len(recent_results) - 4):
            pattern = recent_results[i:i+5]
            if pattern[:2] == [0, 0] and pattern[2:] == [1, 1, 1]:
                sandbagging_score += 0.3
        
        # Check rating drops followed by easy wins
        rating_changes = player_data.get('rating_changes', [])
        if rating_changes:
            for i in range(len(rating_changes) - 1):
                if rating_changes[i] < -50 and rating_changes[i+1] > 30:
                    sandbagging_score += 0.2
        
        return min(sandbagging_score, 1.0)
    
    def _extract_network_features(self, game_data: Dict) -> List[float]:
        """Extract network-related features"""
        features = []
        
        # Latency
        avg_latency = game_data.get('avg_latency_ms', 50)
        features.append(min(avg_latency / 500, 1.0))  # Normalize to 500ms
        
        # Jitter
        jitter = game_data.get('network_jitter', 10)
        features.append(min(jitter / 100, 1.0))
        
        # VPN/Proxy detection
        vpn_detected = 1.0 if game_data.get('vpn_detected', False) else 0.0
        features.append(vpn_detected)
        
        return features
    
    def _check_device_consistency(self, player_data: Dict) -> float:
        """Check device fingerprint consistency"""
        fingerprints = player_data.get('device_fingerprints', [])
        
        if len(fingerprints) <= 1:
            return 1.0  # Not enough data
        
        # Check for multiple different devices
        unique_fingerprints = len(set(fingerprints))
        consistency = 1.0 - (unique_fingerprints - 1) / len(fingerprints)
        
        return max(consistency, 0.0)
    
    def build_neural_model(self, input_dim: int) -> keras.Model:
        """Build deep neural network for feature learning"""
        model = keras.Sequential([
            keras.layers.Input(shape=(input_dim,)),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall()]
        )
        
        return model
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Train the anomaly detection system
        
        Args:
            X: Feature matrix
            y: Labels (0 for normal, 1 for cheating)
            
        Returns:
            Dictionary containing training metrics
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train Isolation Forest (unsupervised)
        self.isolation_forest.fit(X_train_scaled)
        
        # Get Isolation Forest predictions
        if_train_pred = self.isolation_forest.predict(X_train_scaled)
        if_test_pred = self.isolation_forest.predict(X_test_scaled)
        
        # Convert to binary (1 for anomaly, 0 for normal)
        if_train_pred = (if_train_pred == -1).astype(int)
        if_test_pred = (if_test_pred == -1).astype(int)
        
        # Train Neural Network (supervised)
        if self.neural_model is None:
            self.neural_model = self.build_neural_model(X.shape[1])
        
        # Add class weights to handle imbalanced data
        class_weights = {0: 1.0, 1: 10.0}  # Higher weight for cheating class
        
        history = self.neural_model.fit(
            X_train_scaled, y_train,
            validation_data=(X_test_scaled, y_test),
            epochs=50,
            batch_size=32,
            class_weight=class_weights,
            verbose=0
        )
        
        # Get Neural Network predictions
        nn_train_pred = (self.neural_model.predict(X_train_scaled) > 0.5).astype(int).flatten()
        nn_test_pred = (self.neural_model.predict(X_test_scaled) > 0.5).astype(int).flatten()
        
        # Ensemble predictions (combine IF and NN)
        ensemble_train_pred = ((if_train_pred + nn_train_pred) >= 1).astype(int)
        ensemble_test_pred = ((if_test_pred + nn_test_pred) >= 1).astype(int)
        
        # Calculate metrics
        metrics = {
            'isolation_forest_accuracy': accuracy_score(y_test, if_test_pred),
            'neural_network_accuracy': accuracy_score(y_test, nn_test_pred),
            'ensemble_accuracy': accuracy_score(y_test, ensemble_test_pred),
            'ensemble_precision': precision_score(y_test, ensemble_test_pred),
            'ensemble_recall': recall_score(y_test, ensemble_test_pred),
            'ensemble_f1': f1_score(y_test, ensemble_test_pred),
            'false_positive_rate': np.sum((ensemble_test_pred == 1) & (y_test == 0)) / np.sum(y_test == 0)
        }
        
        logger.info(f"Training completed. Ensemble accuracy: {metrics['ensemble_accuracy']:.4f}")
        logger.info(f"False positive rate: {metrics['false_positive_rate']:.4f}")
        
        # Save metrics to database
        self._save_metrics_to_db(metrics)
        
        return metrics
    
    def predict(self, X: np.ndarray, return_proba: bool = False) -> np.ndarray:
        """
        Predict anomalies using ensemble method
        
        Args:
            X: Feature matrix
            return_proba: If True, return probability scores
            
        Returns:
            Predictions or probability scores
        """
        X_scaled = self.scaler.transform(X)
        
        # Isolation Forest predictions
        if_scores = self.isolation_forest.score_samples(X_scaled)
        if_pred = self.isolation_forest.predict(X_scaled)
        if_pred = (if_pred == -1).astype(int)
        
        # Neural Network predictions
        if self.neural_model:
            nn_proba = self.neural_model.predict(X_scaled).flatten()
            nn_pred = (nn_proba > 0.5).astype(int)
        else:
            nn_proba = np.zeros(X.shape[0])
            nn_pred = np.zeros(X.shape[0])
        
        if return_proba:
            # Combine scores
            if_proba = 1 / (1 + np.exp(if_scores))  # Convert to probability
            ensemble_proba = (if_proba + nn_proba) / 2
            return ensemble_proba
        else:
            # Ensemble prediction
            ensemble_pred = ((if_pred + nn_pred) >= 1).astype(int)
            return ensemble_pred
    
    def detect_anomaly(self, 
                       fen: str,
                       move_history: List[str],
                       player_data: Dict,
                       game_data: Dict) -> Dict[str, any]:
        """
        Detect if current position/move is anomalous
        
        Args:
            fen: Current board position
            move_history: List of moves played
            player_data: Player profile data
            game_data: Current game metadata
            
        Returns:
            Dictionary containing detection results
        """
        # Extract features
        features = self.extract_comprehensive_features(
            fen, move_history, player_data, game_data
        )
        
        # Get prediction
        X = features.reshape(1, -1)
        is_anomaly = self.predict(X)[0]
        anomaly_score = self.predict(X, return_proba=True)[0]
        
        # Get cohort-based threshold
        rating = player_data.get('rating', 1500)
        time_control = game_data.get('time_control', 'blitz')
        threshold = self._get_cohort_threshold(rating, time_control)
        
        # Adjust decision based on threshold
        is_suspicious = anomaly_score > threshold
        
        result = {
            'is_anomaly': bool(is_anomaly),
            'is_suspicious': is_suspicious,
            'anomaly_score': float(anomaly_score),
            'threshold': threshold,
            'confidence': abs(anomaly_score - 0.5) * 2,  # Confidence in decision
            'features': {
                'material_balance': float(features[0]),
                'position_complexity': float(features[1]),
                'accuracy_score': float(features[2]) if len(features) > 2 else 0,
                'time_management': float(features[7]) if len(features) > 7 else 0,
                'consistency': float(features[10]) if len(features) > 10 else 0
            }
        }
        
        # Log detection if suspicious
        if is_suspicious:
            self._log_detection(fen, move_history, player_data, game_data, result)
        
        return result
    
    def _get_cohort_threshold(self, rating: int, time_control: str) -> float:
        """Get adaptive threshold based on rating and time control"""
        # Determine time control category
        if 'bullet' in time_control.lower() or '+0' in time_control:
            tc_category = 'bullet'
        elif 'blitz' in time_control.lower() or any(x in time_control for x in ['+2', '+3', '+5']):
            tc_category = 'blitz'
        elif 'rapid' in time_control.lower() or any(x in time_control for x in ['+10', '+15']):
            tc_category = 'rapid'
        else:
            tc_category = 'classical'
        
        # Get threshold from database or use default
        key = f"{rating//200*200}_{tc_category}"
        if key not in self.cohort_thresholds:
            # Query database for threshold
            try:
                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT accuracy_threshold 
                    FROM cohort_thresholds 
                    WHERE rating_min <= %s AND rating_max > %s 
                    AND time_control_category = %s
                """, (rating, rating, tc_category))
                result = cursor.fetchone()
                if result:
                    self.cohort_thresholds[key] = result[0]
                else:
                    self.cohort_thresholds[key] = 0.7  # Default
                cursor.close()
                conn.close()
            except:
                self.cohort_thresholds[key] = 0.7  # Default
        
        return self.cohort_thresholds[key]
    
    def _log_detection(self, 
                      fen: str,
                      move_history: List[str],
                      player_data: Dict,
                      game_data: Dict,
                      detection_result: Dict):
        """Log detection event to database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO warnings (
                    player_id, game_id, warning_type, severity, details, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                player_data.get('player_id'),
                game_data.get('game_id'),
                'suspicious_moves',
                'high' if detection_result['anomaly_score'] > 0.8 else 'medium',
                json.dumps(detection_result),
                datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log detection: {e}")
    
    def _save_metrics_to_db(self, metrics: Dict[str, float]):
        """Save model metrics to database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO model_parameters (
                    model_name, model_version, parameters, accuracy, 
                    precision_score, recall_score, f1_score, 
                    false_positive_rate, training_date, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                'IsolationForest_NN_Ensemble',
                '2.0',
                json.dumps({
                    'contamination': self.contamination,
                    'n_estimators': self.n_estimators,
                    'max_samples': self.max_samples
                }),
                metrics['ensemble_accuracy'],
                metrics['ensemble_precision'],
                metrics['ensemble_recall'],
                metrics['ensemble_f1'],
                metrics['false_positive_rate'],
                datetime.now(),
                True
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def save_model(self, filepath: str):
        """Save the trained model"""
        model_data = {
            'isolation_forest': self.isolation_forest,
            'scaler': self.scaler,
            'feature_weights': self.feature_weights,
            'cohort_thresholds': self.cohort_thresholds
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        if self.neural_model:
            self.neural_model.save(filepath.replace('.pkl', '_nn.h5'))
    
    def load_model(self, filepath: str):
        """Load a trained model"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.isolation_forest = model_data['isolation_forest']
        self.scaler = model_data['scaler']
        self.feature_weights = model_data['feature_weights']
        self.cohort_thresholds = model_data['cohort_thresholds']
        
        nn_path = filepath.replace('.pkl', '_nn.h5')
        if os.path.exists(nn_path):
            self.neural_model = keras.models.load_model(nn_path)


if __name__ == "__main__":
    # Example usage
    detector = EnhancedAnomalyDetector()
    
    # Generate sample data for testing
    np.random.seed(42)
    n_samples = 1000
    n_features = 20
    
    # Generate normal samples
    X_normal = np.random.randn(n_samples * 9 // 10, n_features)
    y_normal = np.zeros(n_samples * 9 // 10)
    
    # Generate anomaly samples (cheating patterns)
    X_anomaly = np.random.randn(n_samples // 10, n_features)
    X_anomaly[:, [0, 2, 4]] *= 3  # Make some features more extreme
    y_anomaly = np.ones(n_samples // 10)
    
    # Combine data
    X = np.vstack([X_normal, X_anomaly])
    y = np.hstack([y_normal, y_anomaly])
    
    # Train model
    metrics = detector.train(X, y)
    print("Training Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")
    
    # Save model
    detector.save_model('models/isolation_forest_model.pkl')
    print("Model saved successfully!")
