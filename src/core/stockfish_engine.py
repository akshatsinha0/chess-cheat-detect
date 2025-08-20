import os
import chess
import chess.engine
import logging
from typing import Dict, List, Optional, Tuple
from stockfish import Stockfish
from config import STOCKFISH_PATH, STOCKFISH_DEPTH
import hashlib
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedStockfishEngine:
    """
    Enhanced Stockfish engine with NNUE support and advanced analysis capabilities
    """
    
    def __init__(self, 
                 path: str = STOCKFISH_PATH,
                 depth: int = STOCKFISH_DEPTH,
                 threads: int = 4,
                 hash_size: int = 256,
                 use_nnue: bool = True):
        """
        Initialize enhanced Stockfish engine
        
        Args:
            path: Path to Stockfish executable
            depth: Default search depth
            threads: Number of threads for analysis
            hash_size: Hash table size in MB
            use_nnue: Enable NNUE evaluation
        """
        self.path = path
        self.depth = depth
        self.threads = threads
        self.hash_size = hash_size
        self.use_nnue = use_nnue
        
        # Initialize Stockfish with advanced parameters
        self.parameters = {
            "Debug Log File": "",
            "Contempt": 0,
            "Min Split Depth": 0,
            "Threads": threads,
            "Ponder": False,
            "Hash": hash_size,
            "MultiPV": 5,  # Analyze top 5 moves
            "Skill Level": 20,
            "Move Overhead": 10,
            "Minimum Thinking Time": 20,
            "Slow Mover": 100,
            "UCI_Chess960": False,
            "UCI_LimitStrength": False,
            "UCI_Elo": 3200
        }
        
        
        
        try:
            self.stockfish = Stockfish(
                path=path,
                depth=depth,
                parameters=self.parameters
            )
            logger.info(f"Stockfish engine initialized with NNUE={'enabled' if use_nnue else 'disabled'}")
        except Exception as e:
            logger.error(f"Failed to initialize Stockfish: {e}")
            raise
        
        # Cache for position evaluations
        self.position_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def analyze_position(self, 
                        fen: str, 
                        depth: Optional[int] = None,
                        time_limit: Optional[float] = None) -> Dict:
        """
        Comprehensive position analysis with NNUE evaluation
        
        Args:
            fen: Position in FEN notation
            depth: Search depth (overrides default)
            time_limit: Time limit in seconds
            
        Returns:
            Dictionary containing detailed analysis
        """
        # Check cache first
        cache_key = self._get_cache_key(fen, depth or self.depth)
        if cache_key in self.position_cache:
            self.cache_hits += 1
            return self.position_cache[cache_key]
        
        self.cache_misses += 1
        
        # Set position
        self.stockfish.set_fen_position(fen)
        
        # Set analysis parameters
        if depth:
            self.stockfish.set_depth(depth)
        else:
            self.stockfish.set_depth(self.depth)
        
        # Get best move and evaluation
        best_move = self.stockfish.get_best_move()
        if time_limit:
            best_move = self.stockfish.get_best_move_time(int(time_limit * 1000))
        
        evaluation = self.stockfish.get_evaluation()
        
        # Get top moves with MultiPV
        top_moves = self.get_top_moves(fen, num_moves=5, depth=depth or self.depth)
        
        # Calculate position complexity
        complexity = self._calculate_complexity(fen)
        
        # Detect critical positions
        is_critical = self._is_critical_position(fen, evaluation)
        
        # Analyze pawn structure
        pawn_structure = self._analyze_pawn_structure(fen)
        
        # Check for tactical motifs
        tactics = self._detect_tactics(fen)
        
        result = {
            "best_move": best_move,
            "evaluation": evaluation,
            "top_moves": top_moves,
            "complexity": complexity,
            "is_critical": is_critical,
            "pawn_structure": pawn_structure,
            "tactics": tactics,
            "nnue_enabled": self.use_nnue,
            "depth_searched": depth or self.depth
        }
        
        # Cache the result
        self.position_cache[cache_key] = result
        
        # Limit cache size
        if len(self.position_cache) > 1000:
            # Remove oldest entries
            keys_to_remove = list(self.position_cache.keys())[:100]
            for key in keys_to_remove:
                del self.position_cache[key]
        
        return result
    
    def get_top_moves(self, 
                     fen: str, 
                     num_moves: int = 5,
                     depth: int = 15) -> List[Dict]:
        """
        Get top N moves with evaluations using MultiPV
        
        Args:
            fen: Position in FEN notation
            num_moves: Number of top moves to analyze
            depth: Search depth
            
        Returns:
            List of top moves with evaluations
        """
        self.stockfish.set_fen_position(fen)
        self.stockfish.set_depth(depth)
        
        # Get top moves
        top_moves = self.stockfish.get_top_moves(num_moves)
        
        # Process and enhance move data
        enhanced_moves = []
        for i, move_data in enumerate(top_moves):
            if move_data and 'Move' in move_data:
                move = move_data['Move']
                
                # Calculate move quality
                if i == 0:
                    quality = "best"
                elif 'Centipawn' in move_data:
                    cp_loss = abs(top_moves[0].get('Centipawn', 0) - move_data['Centipawn'])
                    if cp_loss <= 10:
                        quality = "excellent"
                    elif cp_loss <= 30:
                        quality = "good"
                    elif cp_loss <= 50:
                        quality = "acceptable"
                    else:
                        quality = "dubious"
                else:
                    quality = "unknown"
                
                enhanced_moves.append({
                    "move": move,
                    "evaluation": move_data,
                    "quality": quality,
                    "rank": i + 1
                })
        
        return enhanced_moves
    
    def analyze_move_accuracy(self, 
                             fen_before: str,
                             move_played: str,
                             depth: int = 15) -> Dict:
        """
        Analyze the accuracy of a played move
        
        Args:
            fen_before: Position before the move
            move_played: Move that was played (UCI format)
            depth: Analysis depth
            
        Returns:
            Dictionary with move accuracy metrics
        """
        # Get best move and top moves
        analysis = self.analyze_position(fen_before, depth=depth)
        best_move = analysis['best_move']
        top_moves = analysis['top_moves']
        
        # Check if played move matches best move
        is_best_move = (move_played == best_move)
        
        # Find rank of played move
        move_rank = None
        centipawn_loss = 0
        
        for i, move_data in enumerate(top_moves):
            if move_data['move'] == move_played:
                move_rank = i + 1
                if i > 0 and 'Centipawn' in move_data['evaluation']:
                    best_cp = top_moves[0]['evaluation'].get('Centipawn', 0)
                    played_cp = move_data['evaluation'].get('Centipawn', 0)
                    centipawn_loss = abs(best_cp - played_cp)
                break
        
        # Calculate accuracy score (0-1)
        if is_best_move:
            accuracy_score = 1.0
        elif move_rank and move_rank <= 3:
            accuracy_score = 1.0 - (move_rank - 1) * 0.15
        elif move_rank and move_rank <= 5:
            accuracy_score = 0.7 - (move_rank - 3) * 0.2
        else:
            # Use centipawn loss for moves not in top 5
            accuracy_score = max(0, 1.0 - centipawn_loss / 100)
        
        # Classify move
        if is_best_move:
            classification = "best"
        elif centipawn_loss <= 10:
            classification = "excellent"
        elif centipawn_loss <= 25:
            classification = "good"
        elif centipawn_loss <= 50:
            classification = "inaccuracy"
        elif centipawn_loss <= 100:
            classification = "mistake"
        else:
            classification = "blunder"
        
        return {
            "move_played": move_played,
            "best_move": best_move,
            "is_best_move": is_best_move,
            "move_rank": move_rank,
            "centipawn_loss": centipawn_loss,
            "accuracy_score": accuracy_score,
            "classification": classification,
            "top_moves": top_moves[:3]  # Include top 3 alternatives
        }
    
    def _calculate_complexity(self, fen: str) -> float:
        """
        Calculate position complexity based on various factors
        
        Args:
            fen: Position in FEN notation
            
        Returns:
            Complexity score (0-1)
        """
        board = chess.Board(fen)
        
        # Factor 1: Number of legal moves
        num_legal_moves = len(list(board.legal_moves))
        move_complexity = min(num_legal_moves / 50, 1.0)
        
        # Factor 2: Number of pieces
        num_pieces = len(board.piece_map())
        piece_complexity = num_pieces / 32
        
        # Factor 3: King safety
        white_king_square = board.king(chess.WHITE)
        black_king_square = board.king(chess.BLACK)
        
        king_safety_complexity = 0
        if white_king_square and black_king_square:
            # Check if kings are exposed
            white_king_file = chess.square_file(white_king_square)
            black_king_file = chess.square_file(black_king_square)
            
            if white_king_file not in [0, 7] or black_king_file not in [0, 7]:
                king_safety_complexity += 0.3
        
        # Factor 4: Pawn structure complexity
        pawns = [sq for sq in board.piece_map() 
                if board.piece_at(sq).piece_type == chess.PAWN]
        pawn_islands = self._count_pawn_islands(board)
        pawn_complexity = min(pawn_islands / 4, 1.0) * 0.3
        
        # Factor 5: Material imbalance
        material_imbalance = self._calculate_material_imbalance(board)
        imbalance_complexity = min(material_imbalance / 5, 1.0) * 0.4
        
        # Combine factors
        complexity = (
            move_complexity * 0.3 +
            piece_complexity * 0.2 +
            king_safety_complexity * 0.2 +
            pawn_complexity * 0.15 +
            imbalance_complexity * 0.15
        )
        
        return min(complexity, 1.0)
    
    def _is_critical_position(self, fen: str, evaluation: Dict) -> bool:
        """
        Detect if position is critical (requires accurate play)
        
        Args:
            fen: Position in FEN notation
            evaluation: Position evaluation
            
        Returns:
            True if position is critical
        """
        board = chess.Board(fen)
        
        # Check for immediate threats
        if board.is_check():
            return True
        
        # Check evaluation swings in top moves
        top_moves = self.get_top_moves(fen, num_moves=3, depth=10)
        if len(top_moves) >= 2:
            eval_diff = 0
            if 'Centipawn' in top_moves[0]['evaluation'] and 'Centipawn' in top_moves[1]['evaluation']:
                eval_diff = abs(top_moves[0]['evaluation']['Centipawn'] - 
                              top_moves[1]['evaluation']['Centipawn'])
            
            if eval_diff > 100:  # Large evaluation difference
                return True
        
        # Check for tactical motifs
        if self._has_forcing_moves(board):
            return True
        
        # Check if in endgame with small advantage
        if len(board.piece_map()) <= 10:
            if 'Centipawn' in evaluation:
                cp = abs(evaluation['Centipawn'])
                if 50 <= cp <= 200:  # Small but meaningful advantage
                    return True
        
        return False
    
    def _analyze_pawn_structure(self, fen: str) -> Dict:
        """
        Analyze pawn structure characteristics
        
        Args:
            fen: Position in FEN notation
            
        Returns:
            Dictionary with pawn structure metrics
        """
        board = chess.Board(fen)
        
        white_pawns = []
        black_pawns = []
        
        for square, piece in board.piece_map().items():
            if piece.piece_type == chess.PAWN:
                if piece.color == chess.WHITE:
                    white_pawns.append(square)
                else:
                    black_pawns.append(square)
        
        # Analyze pawn characteristics
        white_doubled = self._count_doubled_pawns(white_pawns, chess.WHITE)
        black_doubled = self._count_doubled_pawns(black_pawns, chess.BLACK)
        
        white_isolated = self._count_isolated_pawns(white_pawns, board, chess.WHITE)
        black_isolated = self._count_isolated_pawns(black_pawns, board, chess.BLACK)
        
        white_passed = self._count_passed_pawns(white_pawns, board, chess.WHITE)
        black_passed = self._count_passed_pawns(black_pawns, board, chess.BLACK)
        
        return {
            "white": {
                "count": len(white_pawns),
                "doubled": white_doubled,
                "isolated": white_isolated,
                "passed": white_passed,
                "islands": self._count_pawn_islands_for_color(board, chess.WHITE)
            },
            "black": {
                "count": len(black_pawns),
                "doubled": black_doubled,
                "isolated": black_isolated,
                "passed": black_passed,
                "islands": self._count_pawn_islands_for_color(board, chess.BLACK)
            },
            "structure_score": self._evaluate_pawn_structure_score(
                white_doubled, black_doubled,
                white_isolated, black_isolated,
                white_passed, black_passed
            )
        }
    
    def _detect_tactics(self, fen: str) -> List[str]:
        """
        Detect tactical motifs in the position
        
        Args:
            fen: Position in FEN notation
            
        Returns:
            List of detected tactical themes
        """
        board = chess.Board(fen)
        tactics = []
        
        # Check for pins
        if self._has_pins(board):
            tactics.append("pin")
        
        # Check for forks
        if self._has_forks(board):
            tactics.append("fork")
        
        # Check for skewers
        if self._has_skewers(board):
            tactics.append("skewer")
        
        # Check for discovered attacks
        if self._has_discovered_attacks(board):
            tactics.append("discovered_attack")
        
        # Check for back rank weakness
        if self._has_back_rank_weakness(board):
            tactics.append("back_rank_weakness")
        
        # Check for hanging pieces
        if self._has_hanging_pieces(board):
            tactics.append("hanging_piece")
        
        return tactics
    
    def _get_cache_key(self, fen: str, depth: int) -> str:
        """Generate cache key for position"""
        return hashlib.md5(f"{fen}_{depth}".encode()).hexdigest()
    
    def _count_pawn_islands(self, board: chess.Board) -> int:
        """Count total pawn islands"""
        white_islands = self._count_pawn_islands_for_color(board, chess.WHITE)
        black_islands = self._count_pawn_islands_for_color(board, chess.BLACK)
        return white_islands + black_islands
    
    def _count_pawn_islands_for_color(self, board: chess.Board, color: bool) -> int:
        """Count pawn islands for a specific color"""
        files_with_pawns = set()
        
        for square, piece in board.piece_map().items():
            if piece.piece_type == chess.PAWN and piece.color == color:
                files_with_pawns.add(chess.square_file(square))
        
        if not files_with_pawns:
            return 0
        
        # Count islands (groups of adjacent files)
        sorted_files = sorted(files_with_pawns)
        islands = 1
        
        for i in range(1, len(sorted_files)):
            if sorted_files[i] - sorted_files[i-1] > 1:
                islands += 1
        
        return islands
    
    def _calculate_material_imbalance(self, board: chess.Board) -> float:
        """Calculate material imbalance score"""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3.25,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        
        white_material = 0
        black_material = 0
        
        for square, piece in board.piece_map().items():
            value = piece_values.get(piece.piece_type, 0)
            if piece.color == chess.WHITE:
                white_material += value
            else:
                black_material += value
        
        return abs(white_material - black_material)
    
    def _has_forcing_moves(self, board: chess.Board) -> bool:
        """Check if position has forcing moves"""
        for move in board.legal_moves:
            if board.is_capture(move) or board.gives_check(move):
                return True
        return False
    
    def _count_doubled_pawns(self, pawn_squares: List[int], color: bool) -> int:
        """Count doubled pawns"""
        files = {}
        for square in pawn_squares:
            file = chess.square_file(square)
            files[file] = files.get(file, 0) + 1
        
        doubled = sum(1 for count in files.values() if count > 1)
        return doubled
    
    def _count_isolated_pawns(self, pawn_squares: List[int], board: chess.Board, color: bool) -> int:
        """Count isolated pawns"""
        isolated = 0
        files_with_pawns = set(chess.square_file(sq) for sq in pawn_squares)
        
        for square in pawn_squares:
            file = chess.square_file(square)
            
            # Check adjacent files
            has_support = False
            for adj_file in [file - 1, file + 1]:
                if 0 <= adj_file <= 7 and adj_file in files_with_pawns:
                    has_support = True
                    break
            
            if not has_support:
                isolated += 1
        
        return isolated
    
    def _count_passed_pawns(self, pawn_squares: List[int], board: chess.Board, color: bool) -> int:
        """Count passed pawns"""
        passed = 0
        
        for square in pawn_squares:
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            
            is_passed = True
            
            # Check if any enemy pawns can block or capture
            for enemy_square, piece in board.piece_map().items():
                if piece.piece_type == chess.PAWN and piece.color != color:
                    enemy_file = chess.square_file(enemy_square)
                    enemy_rank = chess.square_rank(enemy_square)
                    
                    # Check if enemy pawn can block
                    if abs(enemy_file - file) <= 1:
                        if color == chess.WHITE and enemy_rank > rank:
                            is_passed = False
                            break
                        elif color == chess.BLACK and enemy_rank < rank:
                            is_passed = False
                            break
            
            if is_passed:
                passed += 1
        
        return passed
    
    def _evaluate_pawn_structure_score(self, 
                                      white_doubled: int, black_doubled: int,
                                      white_isolated: int, black_isolated: int,
                                      white_passed: int, black_passed: int) -> float:
        """Evaluate overall pawn structure score"""
        # Penalties for weaknesses
        white_penalty = (white_doubled * 0.5 + white_isolated * 0.7)
        black_penalty = (black_doubled * 0.5 + black_isolated * 0.7)
        
        # Bonuses for passed pawns
        white_bonus = white_passed * 1.5
        black_bonus = black_passed * 1.5
        
        score = (white_bonus - white_penalty) - (black_bonus - black_penalty)
        return score / 10  # Normalize
    
    def _has_pins(self, board: chess.Board) -> bool:
        """Check for pins in the position"""
        # Simplified pin detection
        king_square = board.king(board.turn)
        if not king_square:
            return False
        
        # Check for potential pins along ranks, files, and diagonals
        for attacker_square, piece in board.piece_map().items():
            if piece.color != board.turn:
                # Check if piece can attack along a line
                if piece.piece_type in [chess.ROOK, chess.QUEEN]:
                    # Check ranks and files
                    if (chess.square_rank(attacker_square) == chess.square_rank(king_square) or
                        chess.square_file(attacker_square) == chess.square_file(king_square)):
                        return True
                
                if piece.piece_type in [chess.BISHOP, chess.QUEEN]:
                    # Check diagonals (simplified)
                    file_diff = abs(chess.square_file(attacker_square) - chess.square_file(king_square))
                    rank_diff = abs(chess.square_rank(attacker_square) - chess.square_rank(king_square))
                    if file_diff == rank_diff:
                        return True
        
        return False
    
    def _has_forks(self, board: chess.Board) -> bool:
        """Check for fork possibilities"""
        # Check knight forks (most common)
        for square, piece in board.piece_map().items():
            if piece.piece_type == chess.KNIGHT and piece.color == board.turn:
                # Check if knight attacks multiple valuable pieces
                attacks = board.attacks(square)
                valuable_attacks = 0
                
                for attacked_square in attacks:
                    attacked_piece = board.piece_at(attacked_square)
                    if attacked_piece and attacked_piece.color != board.turn:
                        if attacked_piece.piece_type in [chess.ROOK, chess.QUEEN, chess.KING]:
                            valuable_attacks += 1
                
                if valuable_attacks >= 2:
                    return True
        
        return False
    
    def _has_skewers(self, board: chess.Board) -> bool:
        """Check for skewer possibilities"""
        # Simplified skewer detection
        return False  # Implement if needed
    
    def _has_discovered_attacks(self, board: chess.Board) -> bool:
        """Check for discovered attack possibilities"""
        # Simplified discovered attack detection
        return len(list(board.legal_moves)) > 30  # Heuristic
    
    def _has_back_rank_weakness(self, board: chess.Board) -> bool:
        """Check for back rank weakness"""
        king_square = board.king(board.turn)
        if not king_square:
            return False
        
        # Check if king is on back rank
        if board.turn == chess.WHITE:
            if chess.square_rank(king_square) == 0:
                # Check if king has escape squares
                escape_squares = 0
                for move in board.legal_moves:
                    if move.from_square == king_square:
                        escape_squares += 1
                
                return escape_squares <= 2
        else:
            if chess.square_rank(king_square) == 7:
                # Check if king has escape squares
                escape_squares = 0
                for move in board.legal_moves:
                    if move.from_square == king_square:
                        escape_squares += 1
                
                return escape_squares <= 2
        
        return False
    
    def _has_hanging_pieces(self, board: chess.Board) -> bool:
        """Check for hanging (undefended) pieces"""
        for square, piece in board.piece_map().items():
            if piece.color == board.turn:
                # Check if piece is attacked and not defended
                if board.is_attacked_by(not board.turn, square):
                    # Simplified check - in production, check if adequately defended
                    return True
        
        return False
    
    def get_statistics(self) -> Dict:
        """Get engine statistics"""
        cache_hit_rate = 0
        if self.cache_hits + self.cache_misses > 0:
            cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses)
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self.position_cache),
            "nnue_enabled": self.use_nnue,
            "threads": self.threads,
            "hash_size_mb": self.hash_size
        }
    
    def clear_cache(self):
        """Clear position cache"""
        self.position_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Position cache cleared")


# Create global instance for backward compatibility
stockfish = EnhancedStockfishEngine()

# Backward compatible function
def analyze_position(fen: str, depth: int = 15) -> Dict:
    """Backward compatible wrapper for position analysis"""
    return stockfish.analyze_position(fen, depth=depth)
