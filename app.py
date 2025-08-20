

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import mysql.connector
from dotenv import load_dotenv
import asyncio
import threading

# Import our custom modules
from src.analyzer import CheatAnalyzer
from src.utils.player_profile_manager import PlayerProfileManager
from src.utils.dynamic_warning_system import DynamicWarningSystem
from src.utils.game_scraper import EnhancedGameScraper

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chess-detection-secret-key-2024')
app.config['SESSION_TYPE'] = 'filesystem'

# Initialize CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize components
cheat_analyzer = None
player_manager = None
warning_system = None
game_scraper = None
db_connection = None

def initialize_components():
    """Initialize all system components"""
    global cheat_analyzer, player_manager, warning_system, game_scraper, db_connection
    
    try:
        # Database connection
        db_connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'chess_detection')
        )
        logger.info("Database connected successfully")
        
        # Initialize analyzer
        cheat_analyzer = CheatAnalyzer()
        logger.info("Cheat analyzer initialized")
        
        # Initialize player manager
        player_manager = PlayerProfileManager(db_connection)
        logger.info("Player profile manager initialized")
        
        # Initialize warning system with WebSocket
        warning_system = DynamicWarningSystem(db_connection, socketio)
        logger.info("Warning system initialized")
        
        # Initialize game scraper
        game_scraper = EnhancedGameScraper()
        logger.info("Game scraper initialized")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return False

# Routes
@app.route('/')
def index():
    """Main application page"""
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_game():
    """Analyze a chess game for cheating"""
    try:
        data = request.json
        pgn = data.get('pgn')
        player_id = data.get('player_id')
        
        if not pgn:
            return jsonify({'error': 'PGN data required'}), 400
        
        # Perform analysis
        analysis_result = cheat_analyzer.analyze_game(pgn)
        
        # Check for warnings
        if warning_system:
            warnings = warning_system.process_analysis(analysis_result, player_id)
            analysis_result['warnings'] = warnings
        
        # Update player profile
        if player_manager and player_id:
            player_manager.update_from_game(player_id, analysis_result)
        
        return jsonify(analysis_result)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/<player_id>')
def get_player_profile(player_id):
    """Get player profile data"""
    try:
        if not player_manager:
            return jsonify({'error': 'System not initialized'}), 503
        
        profile = player_manager.get_profile(player_id)
        if profile:
            return jsonify(profile.to_dict())
        else:
            return jsonify({'error': 'Player not found'}), 404
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape_games():
    """Scrape games from chess platforms"""
    try:
        data = request.json
        username = data.get('username')
        platform = data.get('platform', 'chess.com')
        max_games = data.get('max_games', 10)
        
        if not username:
            return jsonify({'error': 'Username required'}), 400
        
        # Start scraping in background
        def scrape_async():
            try:
                games = game_scraper.scrape_player_games(
                    username, platform, max_games
                )
                
                # Store games in database
                for game in games:
                    if db_connection:
                        cursor = db_connection.cursor()
                        cursor.execute("""
                            INSERT INTO games (player_id, pgn, platform, played_at)
                            VALUES (%s, %s, %s, %s)
                        """, (username, game['pgn'], platform, game.get('date')))
                        db_connection.commit()
                
                # Notify via WebSocket
                socketio.emit('scraping_complete', {
                    'username': username,
                    'games_count': len(games)
                })
            except Exception as e:
                logger.error(f"Scraping error: {e}")
                socketio.emit('scraping_error', {'error': str(e)})
        
        thread = threading.Thread(target=scrape_async)
        thread.start()
        
        return jsonify({'status': 'Scraping started'})
    except Exception as e:
        logger.error(f"Scrape request error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/warnings')
def get_warnings():
    """Get active warnings"""
    try:
        if not warning_system:
            return jsonify({'error': 'System not initialized'}), 503
        
        warnings = warning_system.get_active_warnings()
        return jsonify(warnings)
    except Exception as e:
        logger.error(f"Warning retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_statistics():
    """Get system statistics"""
    try:
        stats = {
            'total_players': 0,
            'total_games': 0,
            'active_warnings': 0,
            'banned_players': 0
        }
        
        if db_connection:
            cursor = db_connection.cursor(dictionary=True)
            
            # Get player count
            cursor.execute("SELECT COUNT(*) as count FROM players")
            stats['total_players'] = cursor.fetchone()['count']
            
            # Get game count
            cursor.execute("SELECT COUNT(*) as count FROM games")
            stats['total_games'] = cursor.fetchone()['count']
            
            # Get active warnings
            cursor.execute("SELECT COUNT(*) as count FROM warnings WHERE status = 'active'")
            stats['active_warnings'] = cursor.fetchone()['count']
            
            # Get banned players
            cursor.execute("SELECT COUNT(*) as count FROM players WHERE status = 'banned'")
            stats['banned_players'] = cursor.fetchone()['count']
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to Chess Detection System'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('analyze_move')
def handle_move_analysis(data):
    """Analyze a single move in real-time"""
    try:
        fen = data.get('fen')
        move = data.get('move')
        move_number = data.get('moveNumber')
        
        # Perform quick analysis
        if cheat_analyzer:
            analysis = cheat_analyzer.analyze_position(fen, move)
            
            # Send result back
            emit('move_analyzed', {
                'moveNumber': move_number,
                'move': move,
                'analysis': analysis
            })
            
            # Check for suspicious patterns
            if analysis.get('suspicion_score', 0) > 0.7:
                emit('warning_alert', {
                    'warning': {
                        'type': 'suspicious_move',
                        'message': f'Suspicious move detected: {move}',
                        'details': f'Move {move_number}: {move} has high suspicion score'
                    }
                })
    except Exception as e:
        logger.error(f"Move analysis error: {e}")
        emit('analysis_error', {'error': str(e)})

@socketio.on('start_analysis')
def handle_start_analysis(data):
    """Start full game analysis"""
    try:
        pgn = data.get('pgn')
        
        if not pgn:
            emit('analysis_error', {'error': 'No PGN provided'})
            return
        
        # Start analysis in background
        def analyze_async():
            try:
                result = cheat_analyzer.analyze_game(pgn)
                
                # Send results
                emit('analysis_result', {
                    'accuracy': result.get('accuracy', 0),
                    'anomaly_score': result.get('anomaly_score', 0),
                    'consistency': result.get('consistency', 0),
                    'trust_score': result.get('trust_score', 1),
                    'move_accuracies': result.get('move_accuracies', []),
                    'move_numbers': list(range(1, len(result.get('move_accuracies', [])) + 1))
                })
                
                # Check for warnings
                if result.get('is_suspicious'):
                    emit('warning_alert', {
                        'warning': {
                            'type': 'game_flagged',
                            'message': 'Game flagged for suspicious play',
                            'details': 'Multiple anomalies detected in this game'
                        }
                    })
            except Exception as e:
                logger.error(f"Async analysis error: {e}")
                emit('analysis_error', {'error': str(e)})
        
        thread = threading.Thread(target=analyze_async)
        thread.start()
        
        emit('analysis_started', {'message': 'Analysis in progress...'})
    except Exception as e:
        logger.error(f"Start analysis error: {e}")
        emit('analysis_error', {'error': str(e)})

@socketio.on('search_player')
def handle_player_search(data):
    """Search for player profile"""
    try:
        username = data.get('username')
        
        if not username:
            emit('search_error', {'error': 'Username required'})
            return
        
        # Search in database
        if db_connection:
            cursor = db_connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM players WHERE username = %s
            """, (username,))
            player = cursor.fetchone()
            
            if player:
                # Get additional stats
                cursor.execute("""
                    SELECT COUNT(*) as total_games,
                           AVG(accuracy) as avg_accuracy,
                           COUNT(CASE WHEN flagged = 1 THEN 1 END) as flagged_games
                    FROM games WHERE player_id = %s
                """, (player['id'],))
                stats = cursor.fetchone()
                
                player.update(stats)
                emit('player_found', player)
            else:
                emit('player_not_found', {'username': username})
    except Exception as e:
        logger.error(f"Player search error: {e}")
        emit('search_error', {'error': str(e)})

@socketio.on('request_update')
def handle_update_request(data):
    """Handle real-time update requests"""
    try:
        update_type = data.get('type')
        
        if update_type == 'stats':
            # Send current statistics
            stats = {
                'timestamp': datetime.now().isoformat(),
                'active_analyses': 0,  # Could track active analysis threads
                'detection_rate': 98.2,  # Example metric
                'false_positive_rate': 1.8
            }
            emit('stats_update', stats)
        
        elif update_type == 'warnings':
            # Send recent warnings
            if warning_system:
                warnings = warning_system.get_recent_warnings(limit=10)
                emit('warnings_update', warnings)
    except Exception as e:
        logger.error(f"Update request error: {e}")
        emit('update_error', {'error': str(e)})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Cleanup function
def cleanup():
    """Clean up resources on shutdown"""
    global db_connection
    
    if db_connection:
        db_connection.close()
        logger.info("Database connection closed")
    
    if game_scraper:
        game_scraper.close()
        logger.info("Game scraper closed")

# Main entry point
if __name__ == '__main__':
    try:
        # Initialize components
        if initialize_components():
            logger.info("Starting Chess Cheat Detection System...")
            
            # Run the application
            socketio.run(
                app,
                host='0.0.0.0',
                port=int(os.getenv('PORT', 5000)),
                debug=os.getenv('DEBUG', 'False').lower() == 'true'
            )
        else:
            logger.error("Failed to initialize system components")
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        cleanup()
    except Exception as e:
        logger.error(f"Application error: {e}")
        cleanup()
