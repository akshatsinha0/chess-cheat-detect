# tests/test_web_api.py

import pytest
import json
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the modules before importing the app
sys.modules['src.core.stockfish_engine'] = MagicMock()
sys.modules['src.ml.anomaly_detector'] = MagicMock()
sys.modules['src.detection.board_detector'] = MagicMock()

from src.web.app import app, current_game, move_history, analysis_results

class TestWebAPI:
    """Test suite for the web API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture(autouse=True)
    def reset_game_state(self):
        """Reset game state before each test."""
        global current_game, move_history, analysis_results
        import chess
        current_game = chess.Board()
        move_history.clear()
        analysis_results.clear()
    
    def test_index_route(self, client):
        """Test the index route."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_new_game(self, client):
        """Test starting a new game."""
        response = client.post('/api/new_game')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'fen' in data
        assert 'board_svg' in data
    
    @patch('src.web.app.analyze_position')
    def test_make_move_valid(self, mock_analyze, client):
        """Test making a valid move."""
        # Mock analysis
        mock_analyze.return_value = {
            'best_move': 'e2e4',
            'evaluation': {'value': 30, 'type': 'cp'}
        }
        
        # Mock anomaly detector
        with patch('src.web.app.anomaly_detector.predict_suspicion') as mock_predict:
            mock_predict.return_value = 0.2
            
            response = client.post('/api/make_move', 
                                 json={'move': 'e2e4'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert 'analysis' in data
            assert data['analysis']['suspicion_score'] == 0.2
    
    def test_make_move_invalid(self, client):
        """Test making an invalid move."""
        response = client.post('/api/make_move', 
                             json={'move': 'e2e5'})  # Invalid move
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    @patch('src.web.app.analyze_position')
    def test_analyze_fen(self, mock_analyze, client):
        """Test FEN analysis."""
        mock_analyze.return_value = {
            'best_move': 'e2e4',
            'evaluation': {'value': 30, 'type': 'cp'}
        }
        
        with patch('src.web.app.anomaly_detector.predict_suspicion') as mock_predict:
            mock_predict.return_value = 0.15
            
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            response = client.post('/api/analyze_fen', json={'fen': fen})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert data['suspicion_score'] == 0.15
    
    def test_analyze_fen_invalid(self, client):
        """Test FEN analysis with invalid FEN."""
        response = client.post('/api/analyze_fen', 
                             json={'fen': 'invalid_fen'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
    
    @patch('src.web.app.chess.pgn.read_game')
    @patch('src.web.app.analyze_position')
    def test_import_pgn(self, mock_analyze, mock_read_game, client):
        """Test PGN import and analysis."""
        # Create mock game
        mock_game = MagicMock()
        mock_game.headers = {
            'White': 'Player1',
            'Black': 'Player2',
            'Result': '1-0',
            'Date': '2023.01.01'
        }
        
        # Mock moves
        mock_move1 = MagicMock()
        mock_move1.uci.return_value = 'e2e4'
        mock_move2 = MagicMock()
        mock_move2.uci.return_value = 'e7e5'
        
        mock_game.mainline_moves.return_value = [mock_move1, mock_move2]
        mock_game.board.return_value = MagicMock()
        
        mock_read_game.return_value = mock_game
        mock_analyze.return_value = {
            'best_move': 'e2e4',
            'evaluation': {'value': 30, 'type': 'cp'}
        }
        
        with patch('src.web.app.anomaly_detector.predict_suspicion') as mock_predict:
            mock_predict.return_value = 0.25
            
            pgn = "[Event \"Test\"]\n[White \"Player1\"]\n[Black \"Player2\"]\n1. e4 e5"
            response = client.post('/api/import_pgn', json={'pgn': pgn})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert data['game_info']['white'] == 'Player1'
            assert len(data['analysis']) == 2
    
    @patch('src.web.app.board_detector')
    def test_capture_board(self, mock_board_detector, client):
        """Test board capture from camera."""
        # Create mock frame
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock board detector instance
        mock_detector_instance = MagicMock()
        mock_detector_instance.capture_frame.return_value = mock_frame
        mock_detector_instance.get_fen_from_image.return_value = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Mock cv2.imencode
        with patch('cv2.imencode') as mock_imencode:
            mock_imencode.return_value = (True, np.array([1, 2, 3]))
            
            with patch('src.web.app.BoardDetector') as mock_bd_class:
                mock_bd_class.return_value = mock_detector_instance
                
                response = client.post('/api/capture_board')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'success'
                assert 'fen' in data
                assert 'image' in data

class TestWebSocketEvents:
    """Test suite for WebSocket events."""
    
    @pytest.fixture
    def socketio_client(self):
        """Create a SocketIO test client."""
        from src.web.app import socketio
        client = socketio.test_client(app)
        yield client
        client.disconnect()
    
    def test_connect_event(self, socketio_client):
        """Test WebSocket connection."""
        received = socketio_client.get_received()
        assert len(received) > 0
        assert any(msg['name'] == 'connected' for msg in received)
    
    @patch('src.web.app.analyze_position')
    def test_request_analysis_event(self, mock_analyze, socketio_client):
        """Test analysis request via WebSocket."""
        mock_analyze.return_value = {
            'best_move': 'e2e4',
            'evaluation': {'value': 30, 'type': 'cp'}
        }
        
        with patch('src.web.app.anomaly_detector.predict_suspicion') as mock_predict:
            mock_predict.return_value = 0.3
            
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            socketio_client.emit('request_analysis', {'fen': fen})
            
            received = socketio_client.get_received()
            analysis_msgs = [msg for msg in received if msg['name'] == 'analysis_result']
            
            assert len(analysis_msgs) > 0
            assert analysis_msgs[0]['args'][0]['suspicion_score'] == 0.3
