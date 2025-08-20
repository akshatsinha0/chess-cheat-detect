

import numpy as np
import pandas as pd
import chess
import chess.pgn
import chess.polyglot
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import hashlib
import json
import logging
from collections import defaultdict
import mysql.connector
from scipy import stats
from src.core.stockfish_engine import EnhancedStockfishEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComprehensiveFeatureExtractor:
    """
    Extracts comprehensive features for chess cheat detection
    """
    
    def __init__(self, stockfish_engine: Optional[EnhancedStockfishEngine] = None):
        """
        Initialize feature extractor
        
        Args:
            stockfish_engine: Enhanced Stockfish engine instance
        """
        self.engine = stockfish_engine or EnhancedStockfishEngine()
        
        # Opening book (polyglot format)
        self.opening_book = None
        try:
            # Try to load opening book
            import os
            book_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'book.bin')
            if os.path.exists(book_path):
                self.opening_book = chess.polyglot.open_reader(book_path)
        except:
            logger.warning("Opening book not found, using basic opening detection")
        
        # Feature categories
        self.feature_categories = {
            'accuracy': ['avg_accuracy', 'accuracy_variance', 'critical_accuracy', 
                        'time_pressure_accuracy', 'opening_accuracy', 'endgame_accuracy'],
            'time_management': ['avg_think_time', 'think_time_variance', 'move_time_correlation',
                              'time_pressure_handling', 'premove_frequency', 'time_usage_efficiency'],
            'consistency': ['rating_consistency', 'performance_stability', 'style_consistency',
                          'accuracy_consistency', 'time_consistency', 'opening_consistency'],
            'patterns': ['blunder_rate', 'mistake_rate', 'inaccuracy_rate', 'perfect_move_rate',
                        'engine_correlation', 'human_move_patterns'],
            'complexity': ['avg_position_complexity', 'complex_position_handling',
                         'tactical_accuracy', 'positional_understanding', 'endgame_technique'],
            'behavioral': ['session_entropy', 'move_diversity', 'opening_repertoire',
                         'time_of_day_performance', 'fatigue_patterns', 'tilt_detection'],
            'anomaly': ['unusual_accuracy_spikes', 'time_anomalies', 'pattern_breaks',
                       'rating_manipulation', 'sandbagging_indicators', 'boosting_patterns']
        }
        
        # Database connection
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'chess_cheat_detection'
        }
    
    def extract_all_features(self, 
                            game_pgn: str,
                            player_color: str,
                            player_data: Dict,
                            historical_games: List[Dict]) -> Dict:
        """
        Extract all features from a game
        
        Args:
            game_pgn: PGN string of the game
            player_color: 'white' or 'black'
            player_data: Player profile data
            historical_games: List of historical games for comparison
            
        Returns:
            Dictionary containing all extracted features
        """
        # Parse game
        game = chess.pgn.read_game(chess.io.StringIO(game_pgn))
        if not game:
            raise ValueError("Invalid PGN")
        
        # Extract basic game info
        board = game.board()
        moves = list(game.mainline_moves())
        
        # Initialize feature dictionary
        features = {}
        
        # Extract features by category
        features['accuracy'] = self.extract_accuracy_features(game, player_color)
        features['time_management'] = self.extract_time_features(game, player_color)
        features['consistency'] = self.extract_consistency_features(game, player_color, historical_games)
        features['patterns'] = self.extract_pattern_features(game, player_color)
        features['complexity'] = self.extract_complexity_features(game, player_color)
        features['behavioral'] = self.extract_behavioral_features(game, player_color, player_data)
        features['anomaly'] = self.extract_anomaly_features(game, player_color, historical_games)
        
        # Flatten features
        flat_features = self._flatten_features(features)
        
        return flat_features
    
    def extract_accuracy_features(self, game: chess.pgn.Game, player_color: str) -> Dict:
        """
        Extract accuracy-related features
        """
        board = game.board()
        moves = []
        evaluations = []
        accuracies = []
        critical_moves = []
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Analyze position before move
                fen_before = board.fen()
                analysis = self.engine.analyze_move_accuracy(fen_before, move.uci())
                
                accuracies.append(analysis['accuracy_score'])
                
                # Check if critical position
                if self.engine._is_critical_position(fen_before, analysis):
                    critical_moves.append(analysis['accuracy_score'])
            
            board.push(move)
            move_num += 1
        
        # Calculate features
        features = {
            'avg_accuracy': np.mean(accuracies) if accuracies else 0,
            'accuracy_variance': np.var(accuracies) if accuracies else 0,
            'accuracy_std': np.std(accuracies) if accuracies else 0,
            'critical_accuracy': np.mean(critical_moves) if critical_moves else np.mean(accuracies) if accuracies else 0,
            'accuracy_trend': self._calculate_trend(accuracies),
            'perfect_moves': sum(1 for a in accuracies if a >= 0.95),
            'good_moves': sum(1 for a in accuracies if 0.7 <= a < 0.95),
            'inaccuracies': sum(1 for a in accuracies if 0.5 <= a < 0.7),
            'mistakes': sum(1 for a in accuracies if 0.3 <= a < 0.5),
            'blunders': sum(1 for a in accuracies if a < 0.3)
        }
        
        # Opening accuracy (first 15 moves)
        opening_accuracies = accuracies[:15] if len(accuracies) > 15 else accuracies
        features['opening_accuracy'] = np.mean(opening_accuracies) if opening_accuracies else 0
        
        # Middlegame accuracy
        middlegame_accuracies = accuracies[15:35] if len(accuracies) > 35 else accuracies[15:] if len(accuracies) > 15 else []
        features['middlegame_accuracy'] = np.mean(middlegame_accuracies) if middlegame_accuracies else 0
        
        # Endgame accuracy
        endgame_accuracies = accuracies[35:] if len(accuracies) > 35 else []
        features['endgame_accuracy'] = np.mean(endgame_accuracies) if endgame_accuracies else 0
        
        # Time pressure accuracy (last 10 moves)
        time_pressure_accuracies = accuracies[-10:] if len(accuracies) > 10 else accuracies
        features['time_pressure_accuracy'] = np.mean(time_pressure_accuracies) if time_pressure_accuracies else 0
        
        return features
    
    def extract_time_features(self, game: chess.pgn.Game, player_color: str) -> Dict:
        """
        Extract time management features
        """
        # Get clock times from comments (if available)
        board = game.board()
        think_times = []
        remaining_times = []
        
        move_num = 0
        node = game
        
        while node.variations:
            next_node = node.variation(0)
            
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Extract time from comment (format: [%clk 0:05:23])
                if next_node.comment:
                    import re
                    time_match = re.search(r'\[%clk (\d+):(\d+):(\d+)\]', next_node.comment)
                    if time_match:
                        hours, minutes, seconds = map(int, time_match.groups())
                        remaining_time = hours * 3600 + minutes * 60 + seconds
                        remaining_times.append(remaining_time)
                        
                        if len(remaining_times) > 1:
                            think_time = remaining_times[-2] - remaining_times[-1]
                            think_times.append(max(0, think_time))
            
            node = next_node
            move_num += 1
        
        # If no time data, use estimates
        if not think_times:
            # Estimate based on game length and time control
            num_moves = len(list(game.mainline_moves())) // 2
            think_times = [np.random.normal(5, 2) for _ in range(num_moves)]
        
        features = {
            'avg_think_time': np.mean(think_times) if think_times else 5,
            'think_time_variance': np.var(think_times) if think_times else 4,
            'think_time_std': np.std(think_times) if think_times else 2,
            'max_think_time': np.max(think_times) if think_times else 10,
            'min_think_time': np.min(think_times) if think_times else 1,
            'think_time_trend': self._calculate_trend(think_times),
            'quick_moves': sum(1 for t in think_times if t < 2),
            'long_thinks': sum(1 for t in think_times if t > 30),
            'time_usage_efficiency': self._calculate_time_efficiency(think_times, remaining_times),
            'premove_frequency': sum(1 for t in think_times if t < 0.5) / len(think_times) if think_times else 0
        }
        
        # Time pressure handling
        if len(think_times) > 10:
            early_times = think_times[:len(think_times)//2]
            late_times = think_times[len(think_times)//2:]
            features['time_pressure_handling'] = np.mean(early_times) / (np.mean(late_times) + 0.1)
        else:
            features['time_pressure_handling'] = 1.0
        
        # Move time correlation with position complexity
        features['move_time_correlation'] = self._calculate_time_complexity_correlation(
            game, think_times, player_color
        )
        
        return features
    
    def extract_consistency_features(self, 
                                    game: chess.pgn.Game, 
                                    player_color: str,
                                    historical_games: List[Dict]) -> Dict:
        """
        Extract consistency features across games
        """
        features = {}
        
        # Get current game metrics
        current_accuracy = self.extract_accuracy_features(game, player_color)['avg_accuracy']
        
        # Historical accuracies
        historical_accuracies = []
        historical_times = []
        historical_ratings = []
        
        for hist_game in historical_games[-20:]:  # Last 20 games
            if 'accuracy' in hist_game:
                historical_accuracies.append(hist_game['accuracy'])
            if 'avg_think_time' in hist_game:
                historical_times.append(hist_game['avg_think_time'])
            if 'rating' in hist_game:
                historical_ratings.append(hist_game['rating'])
        
        # Accuracy consistency
        if historical_accuracies:
            features['accuracy_consistency'] = 1 - np.std(historical_accuracies + [current_accuracy])
            features['accuracy_deviation'] = abs(current_accuracy - np.mean(historical_accuracies))
        else:
            features['accuracy_consistency'] = 0.5
            features['accuracy_deviation'] = 0
        
        # Time consistency
        if historical_times:
            features['time_consistency'] = 1 - (np.std(historical_times) / (np.mean(historical_times) + 0.1))
        else:
            features['time_consistency'] = 0.5
        
        # Rating consistency
        if historical_ratings:
            features['rating_consistency'] = 1 - (np.std(historical_ratings) / (np.mean(historical_ratings) + 1))
            features['rating_volatility'] = np.std(historical_ratings)
        else:
            features['rating_consistency'] = 0.5
            features['rating_volatility'] = 50
        
        # Performance stability
        features['performance_stability'] = self._calculate_performance_stability(historical_games)
        
        # Style consistency (opening choices)
        features['opening_consistency'] = self._calculate_opening_consistency(game, historical_games)
        
        # Win/loss streaks
        features['streak_pattern'] = self._analyze_streak_patterns(historical_games)
        
        return features
    
    def extract_pattern_features(self, game: chess.pgn.Game, player_color: str) -> Dict:
        """
        Extract pattern-based features
        """
        board = game.board()
        moves = []
        engine_moves = []
        human_patterns = []
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Get engine's best move
                fen = board.fen()
                analysis = self.engine.analyze_position(fen, depth=15)
                best_move = analysis['best_move']
                
                moves.append(move.uci())
                engine_moves.append(best_move)
                
                # Check for human patterns
                if self._is_human_pattern(board, move):
                    human_patterns.append(1)
                else:
                    human_patterns.append(0)
            
            board.push(move)
            move_num += 1
        
        features = {
            'engine_correlation': sum(1 for m, e in zip(moves, engine_moves) if m == e) / len(moves) if moves else 0,
            'top3_move_rate': self._calculate_top_move_rate(game, player_color, top_n=3),
            'top5_move_rate': self._calculate_top_move_rate(game, player_color, top_n=5),
            'human_move_patterns': np.mean(human_patterns) if human_patterns else 0.5,
            'move_diversity': len(set(moves)) / len(moves) if moves else 0,
            'forcing_move_accuracy': self._calculate_forcing_move_accuracy(game, player_color),
            'quiet_move_accuracy': self._calculate_quiet_move_accuracy(game, player_color)
        }
        
        # Calculate rates for different move classifications
        board = game.board()
        blunders = mistakes = inaccuracies = perfect = 0
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                analysis = self.engine.analyze_move_accuracy(board.fen(), move.uci())
                
                if analysis['classification'] == 'blunder':
                    blunders += 1
                elif analysis['classification'] == 'mistake':
                    mistakes += 1
                elif analysis['classification'] == 'inaccuracy':
                    inaccuracies += 1
                elif analysis['classification'] == 'best':
                    perfect += 1
            
            board.push(move)
            move_num += 1
        
        total_moves = (blunders + mistakes + inaccuracies + perfect) or 1
        
        features['blunder_rate'] = blunders / total_moves
        features['mistake_rate'] = mistakes / total_moves
        features['inaccuracy_rate'] = inaccuracies / total_moves
        features['perfect_move_rate'] = perfect / total_moves
        
        return features
    
    def extract_complexity_features(self, game: chess.pgn.Game, player_color: str) -> Dict:
        """
        Extract complexity-related features
        """
        board = game.board()
        complexities = []
        complex_accuracies = []
        simple_accuracies = []
        tactical_positions = []
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                fen = board.fen()
                
                # Calculate position complexity
                complexity = self.engine._calculate_complexity(fen)
                complexities.append(complexity)
                
                # Get move accuracy
                analysis = self.engine.analyze_move_accuracy(fen, move.uci())
                accuracy = analysis['accuracy_score']
                
                # Categorize by complexity
                if complexity > 0.7:
                    complex_accuracies.append(accuracy)
                elif complexity < 0.3:
                    simple_accuracies.append(accuracy)
                
                # Check for tactical positions
                tactics = self.engine._detect_tactics(fen)
                if tactics:
                    tactical_positions.append(accuracy)
            
            board.push(move)
            move_num += 1
        
        features = {
            'avg_position_complexity': np.mean(complexities) if complexities else 0.5,
            'complexity_variance': np.var(complexities) if complexities else 0,
            'complex_position_handling': np.mean(complex_accuracies) if complex_accuracies else 0.5,
            'simple_position_handling': np.mean(simple_accuracies) if simple_accuracies else 0.7,
            'tactical_accuracy': np.mean(tactical_positions) if tactical_positions else 0.5,
            'complexity_adaptation': self._calculate_complexity_adaptation(complexities, 
                                                                         complex_accuracies + simple_accuracies)
        }
        
        # Positional understanding
        features['positional_understanding'] = self._evaluate_positional_play(game, player_color)
        
        # Endgame technique
        features['endgame_technique'] = self._evaluate_endgame_technique(game, player_color)
        
        return features
    
    def extract_behavioral_features(self, 
                                   game: chess.pgn.Game, 
                                   player_color: str,
                                   player_data: Dict) -> Dict:
        """
        Extract behavioral features
        """
        features = {}
        
        # Session entropy
        moves = []
        board = game.board()
        move_num = 0
        
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                moves.append(move.uci())
            board.push(move)
            move_num += 1
        
        features['session_entropy'] = self._calculate_entropy(moves)
        features['move_diversity'] = len(set(moves)) / len(moves) if moves else 0
        
        # Opening repertoire
        opening = game.headers.get('Opening', '')
        eco = game.headers.get('ECO', '')
        features['opening_repertoire_size'] = player_data.get('opening_count', 5)
        features['uses_main_repertoire'] = 1 if eco in player_data.get('main_openings', []) else 0
        
        # Time of day performance
        game_date = game.headers.get('Date', '')
        game_time = game.headers.get('Time', '')
        features['time_of_day'] = self._get_time_of_day_category(game_time)
        
        # Fatigue patterns
        features['fatigue_indicator'] = self._calculate_fatigue_indicator(game, player_color)
        
        # Tilt detection
        features['tilt_indicator'] = player_data.get('recent_loss_streak', 0) / 5
        
        # Playing style features
        features['aggressive_style'] = self._calculate_aggression_score(game, player_color)
        features['defensive_style'] = self._calculate_defensive_score(game, player_color)
        
        return features
    
    def extract_anomaly_features(self, 
                                game: chess.pgn.Game, 
                                player_color: str,
                                historical_games: List[Dict]) -> Dict:
        """
        Extract anomaly detection features
        """
        features = {}
        
        # Current game metrics
        current_accuracy = self.extract_accuracy_features(game, player_color)['avg_accuracy']
        current_time = self.extract_time_features(game, player_color)['avg_think_time']
        
        # Historical baselines
        historical_accuracies = [g.get('accuracy', 0.5) for g in historical_games[-20:]]
        historical_times = [g.get('avg_think_time', 5) for g in historical_games[-20:]]
        
        # Accuracy spike detection
        if historical_accuracies:
            accuracy_mean = np.mean(historical_accuracies)
            accuracy_std = np.std(historical_accuracies)
            features['accuracy_spike'] = (current_accuracy - accuracy_mean) / (accuracy_std + 0.01)
            features['unusual_accuracy'] = 1 if abs(features['accuracy_spike']) > 2 else 0
        else:
            features['accuracy_spike'] = 0
            features['unusual_accuracy'] = 0
        
        # Time anomalies
        if historical_times:
            time_mean = np.mean(historical_times)
            time_std = np.std(historical_times)
            features['time_anomaly'] = abs(current_time - time_mean) / (time_std + 0.1)
            features['unusual_time'] = 1 if features['time_anomaly'] > 2 else 0
        else:
            features['time_anomaly'] = 0
            features['unusual_time'] = 0
        
        # Pattern break detection
        features['pattern_break'] = self._detect_pattern_break(game, player_color, historical_games)
        
        # Rating manipulation indicators
        features['rating_manipulation'] = self._detect_rating_manipulation(historical_games)
        
        # Sandbagging indicators
        features['sandbagging_score'] = self._calculate_sandbagging_score(historical_games)
        
        # Boosting patterns
        features['boosting_indicator'] = self._detect_boosting_patterns(historical_games)
        
        return features
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in a series of values"""
        if len(values) < 2:
            return 0
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Linear regression
        slope, _ = np.polyfit(x, y, 1)
        return slope
    
    def _calculate_time_efficiency(self, think_times: List[float], remaining_times: List[float]) -> float:
        """Calculate time usage efficiency"""
        if not think_times or not remaining_times:
            return 0.5
        
        # Check if player uses time proportionally to remaining time
        efficiency_scores = []
        
        for i, (think_time, remaining) in enumerate(zip(think_times, remaining_times)):
            if remaining > 0:
                expected_time = remaining / (40 - i)  # Assume 40 moves per game
                efficiency = 1 - abs(think_time - expected_time) / expected_time
                efficiency_scores.append(max(0, min(1, efficiency)))
        
        return np.mean(efficiency_scores) if efficiency_scores else 0.5
    
    def _calculate_time_complexity_correlation(self, 
                                              game: chess.pgn.Game,
                                              think_times: List[float],
                                              player_color: str) -> float:
        """Calculate correlation between think time and position complexity"""
        if not think_times:
            return 0
        
        board = game.board()
        complexities = []
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                complexity = self.engine._calculate_complexity(board.fen())
                complexities.append(complexity)
            
            board.push(move)
            move_num += 1
        
        if len(complexities) == len(think_times) and len(complexities) > 1:
            correlation, _ = stats.pearsonr(complexities, think_times)
            return correlation
        
        return 0
    
    def _calculate_performance_stability(self, historical_games: List[Dict]) -> float:
        """Calculate performance stability across games"""
        if len(historical_games) < 5:
            return 0.5
        
        performances = []
        for game in historical_games[-20:]:
            if 'performance_rating' in game:
                performances.append(game['performance_rating'])
        
        if len(performances) < 5:
            return 0.5
        
        # Calculate coefficient of variation
        cv = np.std(performances) / (np.mean(performances) + 1)
        stability = 1 - min(cv, 1)
        
        return stability
    
    def _calculate_opening_consistency(self, game: chess.pgn.Game, historical_games: List[Dict]) -> float:
        """Calculate consistency in opening choices"""
        current_eco = game.headers.get('ECO', '')
        current_opening = game.headers.get('Opening', '')
        
        if not current_eco:
            return 0.5
        
        eco_codes = []
        for hist_game in historical_games[-20:]:
            if 'eco' in hist_game:
                eco_codes.append(hist_game['eco'])
        
        if not eco_codes:
            return 0.5
        
        # Check how often player uses same opening family
        same_family = sum(1 for eco in eco_codes if eco[:2] == current_eco[:2])
        consistency = same_family / len(eco_codes)
        
        return consistency
    
    def _analyze_streak_patterns(self, historical_games: List[Dict]) -> float:
        """Analyze win/loss streak patterns for unusual behavior"""
        if len(historical_games) < 10:
            return 0
        
        results = []
        for game in historical_games[-30:]:
            if 'result' in game:
                results.append(1 if game['result'] == 'win' else 0)
        
        if len(results) < 10:
            return 0
        
        # Look for suspicious patterns (e.g., deliberate losses followed by wins)
        suspicious_patterns = 0
        
        for i in range(len(results) - 5):
            window = results[i:i+6]
            # Pattern: lose-lose-win-win-win
            if window[:2] == [0, 0] and window[3:] == [1, 1, 1]:
                suspicious_patterns += 1
            # Pattern: win-win-win-lose-lose
            if window[:3] == [1, 1, 1] and window[4:] == [0, 0]:
                suspicious_patterns += 1
        
        return min(suspicious_patterns / 5, 1)
    
    def _is_human_pattern(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if move follows human patterns"""
        # Human patterns include:
        # - Preferring knight moves over bishop in closed positions
        # - Castle early
        # - Develop pieces before moving them twice
        # - Avoid moving same piece multiple times in opening
        
        piece = board.piece_at(move.from_square)
        if not piece:
            return True
        
        # Castling is human-like
        if board.is_castling(move):
            return True
        
        # In opening (move < 10), developing moves are human-like
        if len(board.move_stack) < 20:
            if piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                # Check if this piece has moved before
                for past_move in board.move_stack:
                    if past_move.to_square == move.from_square:
                        return False  # Moving same piece twice in opening
                return True
        
        return True
    
    def _calculate_top_move_rate(self, game: chess.pgn.Game, player_color: str, top_n: int = 3) -> float:
        """Calculate rate of playing top N engine moves"""
        board = game.board()
        top_move_count = 0
        total_moves = 0
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Get top N moves
                top_moves = self.engine.get_top_moves(board.fen(), num_moves=top_n)
                top_move_ucis = [m['move'] for m in top_moves]
                
                if move.uci() in top_move_ucis:
                    top_move_count += 1
                total_moves += 1
            
            board.push(move)
            move_num += 1
        
        return top_move_count / total_moves if total_moves > 0 else 0
    
    def _calculate_forcing_move_accuracy(self, game: chess.pgn.Game, player_color: str) -> float:
        """Calculate accuracy in forcing positions (checks, captures)"""
        board = game.board()
        forcing_accuracies = []
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Check if position has forcing moves
                if any(board.is_capture(m) or board.gives_check(m) for m in board.legal_moves):
                    analysis = self.engine.analyze_move_accuracy(board.fen(), move.uci())
                    forcing_accuracies.append(analysis['accuracy_score'])
            
            board.push(move)
            move_num += 1
        
        return np.mean(forcing_accuracies) if forcing_accuracies else 0.5
    
    def _calculate_quiet_move_accuracy(self, game: chess.pgn.Game, player_color: str) -> float:
        """Calculate accuracy in quiet positions"""
        board = game.board()
        quiet_accuracies = []
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Check if position is quiet (no immediate tactics)
                if not any(board.is_capture(m) or board.gives_check(m) for m in board.legal_moves):
                    analysis = self.engine.analyze_move_accuracy(board.fen(), move.uci())
                    quiet_accuracies.append(analysis['accuracy_score'])
            
            board.push(move)
            move_num += 1
        
        return np.mean(quiet_accuracies) if quiet_accuracies else 0.5
    
    def _calculate_complexity_adaptation(self, complexities: List[float], accuracies: List[float]) -> float:
        """Calculate how well player adapts to complexity changes"""
        if len(complexities) < 2 or len(accuracies) < 2:
            return 0.5
        
        # Check if accuracy decreases appropriately with complexity
        if len(complexities) == len(accuracies):
            correlation, _ = stats.pearsonr(complexities, accuracies)
            # Expect negative correlation (higher complexity, lower accuracy)
            adaptation = 1 - abs(correlation + 0.3)  # Optimal correlation around -0.3
            return max(0, min(1, adaptation))
        
        return 0.5
    
    def _evaluate_positional_play(self, game: chess.pgn.Game, player_color: str) -> float:
        """Evaluate positional understanding"""
        board = game.board()
        positional_scores = []
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Evaluate pawn structure changes
                pawn_structure_before = self.engine._analyze_pawn_structure(board.fen())
                board_copy = board.copy()
                board_copy.push(move)
                pawn_structure_after = self.engine._analyze_pawn_structure(board_copy.fen())
                
                # Good positional play improves pawn structure
                if player_color == 'white':
                    improvement = pawn_structure_after['structure_score'] - pawn_structure_before['structure_score']
                else:
                    improvement = pawn_structure_before['structure_score'] - pawn_structure_after['structure_score']
                
                positional_scores.append(1 / (1 + np.exp(-improvement)))  # Sigmoid normalization
            
            board.push(move)
            move_num += 1
        
        return np.mean(positional_scores) if positional_scores else 0.5
    
    def _evaluate_endgame_technique(self, game: chess.pgn.Game, player_color: str) -> float:
        """Evaluate endgame technique"""
        board = game.board()
        endgame_moves = []
        endgame_accuracies = []
        
        move_num = 0
        for move in game.mainline_moves():
            # Check if in endgame
            if len(board.piece_map()) <= 10:
                if (player_color == 'white' and move_num % 2 == 0) or \
                   (player_color == 'black' and move_num % 2 == 1):
                    
                    analysis = self.engine.analyze_move_accuracy(board.fen(), move.uci())
                    endgame_accuracies.append(analysis['accuracy_score'])
                    endgame_moves.append(move)
            
            board.push(move)
            move_num += 1
        
        if not endgame_accuracies:
            return 0.5
        
        # Endgame technique = high accuracy + progress toward win
        technique_score = np.mean(endgame_accuracies)
        
        # Check if player made progress in endgame
        if endgame_moves:
            # Simple heuristic: reducing material or advancing pawns
            progress_score = 0.5  # Default
            technique_score = technique_score * 0.7 + progress_score * 0.3
        
        return technique_score
    
    def _calculate_entropy(self, moves: List[str]) -> float:
        """Calculate entropy of move distribution"""
        if not moves:
            return 0
        
        move_counts = defaultdict(int)
        for move in moves:
            move_counts[move[:2]] += 1  # Group by piece/square
        
        total = sum(move_counts.values())
        entropy = 0
        
        for count in move_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * np.log2(p)
        
        # Normalize
        max_entropy = np.log2(len(move_counts)) if move_counts else 1
        return entropy / max_entropy if max_entropy > 0 else 0
    
    def _get_time_of_day_category(self, time_str: str) -> int:
        """Get time of day category from time string"""
        if not time_str:
            return 2  # Unknown
        
        try:
            hour = int(time_str.split(':')[0])
            if 6 <= hour < 12:
                return 0  # Morning
            elif 12 <= hour < 18:
                return 1  # Afternoon
            elif 18 <= hour < 24:
                return 2  # Evening
            else:
                return 3  # Night
        except:
            return 2
    
    def _calculate_fatigue_indicator(self, game: chess.pgn.Game, player_color: str) -> float:
        """Calculate fatigue indicator based on accuracy decline"""
        accuracies = self.extract_accuracy_features(game, player_color)
        
        # Compare early vs late game accuracy
        early_acc = (accuracies.get('opening_accuracy', 0) + accuracies.get('middlegame_accuracy', 0)) / 2
        late_acc = accuracies.get('endgame_accuracy', 0) or accuracies.get('time_pressure_accuracy', 0)
        
        if early_acc > 0:
            fatigue = max(0, early_acc - late_acc) / early_acc
        else:
            fatigue = 0
        
        return fatigue
    
    def _calculate_aggression_score(self, game: chess.pgn.Game, player_color: str) -> float:
        """Calculate aggressive playing style score"""
        board = game.board()
        captures = 0
        checks = 0
        total_moves = 0
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                if board.is_capture(move):
                    captures += 1
                if board.gives_check(move):
                    checks += 1
                total_moves += 1
            
            board.push(move)
            move_num += 1
        
        if total_moves == 0:
            return 0.5
        
        aggression = (captures + checks * 2) / total_moves
        return min(aggression, 1.0)
    
    def _calculate_defensive_score(self, game: chess.pgn.Game, player_color: str) -> float:
        """Calculate defensive playing style score"""
        # Inverse of aggression with adjustments
        aggression = self._calculate_aggression_score(game, player_color)
        
        # Also consider king safety moves and piece retreats
        board = game.board()
        defensive_moves = 0
        total_moves = 0
        
        move_num = 0
        for move in game.mainline_moves():
            if (player_color == 'white' and move_num % 2 == 0) or \
               (player_color == 'black' and move_num % 2 == 1):
                
                # Check for defensive patterns
                if board.is_castling(move):
                    defensive_moves += 2
                
                # Check for piece retreats (simplified)
                if move_num > 0:
                    from_rank = chess.square_rank(move.from_square)
                    to_rank = chess.square_rank(move.to_square)
                    
                    if player_color == 'white' and to_rank < from_rank:
                        defensive_moves += 1
                    elif player_color == 'black' and to_rank > from_rank:
                        defensive_moves += 1
                
                total_moves += 1
            
            board.push(move)
            move_num += 1
        
        if total_moves == 0:
            return 0.5
        
        defensive = (1 - aggression) * 0.5 + (defensive_moves / total_moves) * 0.5
        return min(defensive, 1.0)
    
    def _detect_pattern_break(self, 
                             game: chess.pgn.Game,
                             player_color: str,
                             historical_games: List[Dict]) -> float:
        """Detect breaks from usual playing patterns"""
        if len(historical_games) < 10:
            return 0
        
        # Get current game features
        current_features = {
            'aggression': self._calculate_aggression_score(game, player_color),
            'time_usage': self.extract_time_features(game, player_color)['avg_think_time']
        }
        
        # Get historical averages
        hist_aggression = []
        hist_time = []
        
        for hist_game in historical_games[-20:]:
            if 'aggression_score' in hist_game:
                hist_aggression.append(hist_game['aggression_score'])
            if 'avg_think_time' in hist_game:
                hist_time.append(hist_game['avg_think_time'])
        
        pattern_breaks = 0
        
        # Check for significant deviations
        if hist_aggression:
            aggression_dev = abs(current_features['aggression'] - np.mean(hist_aggression))
            if aggression_dev > 2 * np.std(hist_aggression):
                pattern_breaks += 1
        
        if hist_time:
            time_dev = abs(current_features['time_usage'] - np.mean(hist_time))
            if time_dev > 2 * np.std(hist_time):
                pattern_breaks += 1
        
        return pattern_breaks / 2
    
    def _detect_rating_manipulation(self, historical_games: List[Dict]) -> float:
        """Detect potential rating manipulation patterns"""
        if len(historical_games) < 20:
            return 0
        
        ratings = []
        for game in historical_games[-30:]:
            if 'rating' in game:
                ratings.append(game['rating'])
        
        if len(ratings) < 20:
            return 0
        
        # Look for artificial rating drops followed by climbs
        manipulation_score = 0
        
        for i in range(len(ratings) - 10):
            window = ratings[i:i+10]
            first_half = np.mean(window[:5])
            second_half = np.mean(window[5:])
            
            # Significant drop then rise
            if first_half - second_half > 100:
                manipulation_score += 0.3
        
        return min(manipulation_score, 1.0)
    
    def _calculate_sandbagging_score(self, historical_games: List[Dict]) -> float:
        """Calculate sandbagging score (intentional underperformance)"""
        if len(historical_games) < 10:
            return 0
        
        # Look for patterns of poor play followed by strong play
        accuracies = []
        results = []
        
        for game in historical_games[-20:]:
            if 'accuracy' in game:
                accuracies.append(game['accuracy'])
            if 'result' in game:
                results.append(1 if game['result'] == 'win' else 0)
        
        if len(accuracies) < 10:
            return 0
        
        sandbagging_score = 0
        
        # Check for low accuracy in losses, high accuracy in wins
        loss_accuracies = [acc for acc, res in zip(accuracies, results) if res == 0]
        win_accuracies = [acc for acc, res in zip(accuracies, results) if res == 1]
        
        if loss_accuracies and win_accuracies:
            accuracy_diff = np.mean(win_accuracies) - np.mean(loss_accuracies)
            if accuracy_diff > 0.2:  # Significant difference
                sandbagging_score = min(accuracy_diff * 2, 1.0)
        
        return sandbagging_score
    
    def _detect_boosting_patterns(self, historical_games: List[Dict]) -> float:
        """Detect boosting patterns (artificial rating increase)"""
        if len(historical_games) < 15:
            return 0
        
        # Look for unusual win streaks against weak opponents
        boosting_score = 0
        
        win_streak = 0
        opponent_ratings = []
        
        for game in historical_games[-20:]:
            if 'result' in game:
                if game['result'] == 'win':
                    win_streak += 1
                    if 'opponent_rating' in game:
                        opponent_ratings.append(game['opponent_rating'])
                else:
                    if win_streak > 5:
                        # Check if opponents were significantly weaker
                        if opponent_ratings and 'rating' in game:
                            avg_opponent = np.mean(opponent_ratings)
                            if game['rating'] - avg_opponent > 200:
                                boosting_score += 0.5
                    win_streak = 0
                    opponent_ratings = []
        
        return min(boosting_score, 1.0)
    
    def _flatten_features(self, features: Dict) -> Dict:
        """Flatten nested feature dictionary"""
        flat = {}
        
        for category, category_features in features.items():
            if isinstance(category_features, dict):
                for key, value in category_features.items():
                    flat[f"{category}_{key}"] = value
            else:
                flat[category] = category_features
        
        return flat
    
    def save_features_to_db(self, features: Dict, game_id: str, player_id: str):
        """Save extracted features to database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Prepare feature values for insertion
            feature_json = json.dumps(features)
            
            cursor.execute("""
                INSERT INTO player_features (
                    player_id, session_id, session_entropy, opening_book_adherence,
                    avg_think_time, think_time_variance, blunder_rate, accuracy_consistency,
                    sandbagging_score, rating_volatility, time_pressure_performance,
                    endgame_accuracy, tactical_sharpness, positional_understanding,
                    timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                player_id,
                game_id,
                features.get('behavioral_session_entropy', 0),
                features.get('patterns_top3_move_rate', 0),
                features.get('time_management_avg_think_time', 5),
                features.get('time_management_think_time_variance', 4),
                features.get('patterns_blunder_rate', 0.1),
                features.get('consistency_accuracy_consistency', 0.5),
                features.get('anomaly_sandbagging_score', 0),
                features.get('consistency_rating_volatility', 50),
                features.get('accuracy_time_pressure_accuracy', 0.5),
                features.get('accuracy_endgame_accuracy', 0.5),
                features.get('complexity_tactical_accuracy', 0.5),
                features.get('complexity_positional_understanding', 0.5),
                datetime.now()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Features saved for player {player_id}, game {game_id}")
            
        except Exception as e:
            logger.error(f"Failed to save features: {e}")


if __name__ == "__main__":
    # Example usage
    extractor = ComprehensiveFeatureExtractor()
    
    # Sample PGN
    pgn = """
    [Event "Online Game"]
    [White "Player1"]
    [Black "Player2"]
    [Result "1-0"]
    [ECO "C50"]
    [Opening "Italian Game"]
    
    1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O Nf6 5. d3 O-O 6. c3 d6 7. Re1 a6
    8. Bb3 Ba7 9. h3 h6 10. Nbd2 Re8 11. Nf1 Be6 12. Ng3 Qd7 13. Be3 Bxe3
    14. Rxe3 d5 15. exd5 Bxd5 16. Nxe5 Nxe5 17. Rxe5 Bxb3 18. Qxb3 Rxe5
    19. Nf5 Rae8 20. Nxh6+ gxh6 21. Qxb7 Qd6 22. Qxa6 Re1+ 23. Rxe1 Rxe1#
    """
    
    # Extract features
    features = extractor.extract_all_features(
        pgn,
        'white',
        {'rating': 1500, 'opening_count': 5},
        []  # No historical games for this example
    )
    
    print("Extracted Features:")
    for key, value in features.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
