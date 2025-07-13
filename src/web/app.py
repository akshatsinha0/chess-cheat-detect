import os
import json
import base64
import io
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import chess
import chess.svg
import chess.pgn
import cv2
from PIL import Image
import numpy as np
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.core.stockfish_engine import analyze_position
from src.ml.anomaly_detector import AnomalyDetector
from src.detection.board_detector import BoardDetector
from config import MODEL_FILE, SUSPICION_THRESHOLD
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
anomaly_detector = AnomalyDetector(model_path=MODEL_FILE, threshold=SUSPICION_THRESHOLD)
board_detector = None
current_game = chess.Board()
move_history = []
analysis_results = []
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/api/new_game', methods=['POST'])
def new_game():
    global current_game, move_history, analysis_results
    current_game = chess.Board()
    move_history = []
    analysis_results = []
    return jsonify({'status': 'success','fen': current_game.fen(),'board_svg': chess.svg.board(current_game)})
@app.route('/api/make_move', methods=['POST'])
def make_move():
    global current_game, move_history
    data = request.json
    move_uci = data.get('move')
    try:
        move = chess.Move.from_uci(move_uci)
        if move in current_game.legal_moves:
            current_game.push(move)
            move_history.append(move_uci)
            analysis = analyze_position(current_game.fen())
            suspicion_score = anomaly_detector.predict_suspicion(current_game.fen(), analysis['best_move'], analysis['evaluation'])
            analysis_results.append({'move': move_uci,'best_move': analysis['best_move'],'evaluation': analysis['evaluation'],'suspicion_score': suspicion_score})
            socketio.emit('move_made', {'fen': current_game.fen(),'move': move_uci,'analysis': analysis_results[-1]})
            return jsonify({'status': 'success','fen': current_game.fen(),'board_svg': chess.svg.board(current_game),'analysis': analysis_results[-1]})
        else:
            return jsonify({'status': 'error', 'message': 'Illegal move'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
@app.route('/api/analyze_fen', methods=['POST'])
def analyze_fen():
    data = request.json
    fen = data.get('fen')
    try:
        board = chess.Board(fen)
        moves_analysis = []
        for move in list(board.legal_moves)[:10]:
            board.push(move)
            analysis = analyze_position(board.fen())
            board.pop()
            moves_analysis.append({'move': move.uci(),'evaluation': analysis['evaluation']})
        analysis = analyze_position(fen)
        suspicion_score = anomaly_detector.predict_suspicion(fen, analysis['best_move'], analysis['evaluation'])
        return jsonify({'status': 'success','best_move': analysis['best_move'],'evaluation': analysis['evaluation'],'suspicion_score': suspicion_score,'moves_analysis': moves_analysis,'board_svg': chess.svg.board(board)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
@app.route('/api/import_pgn', methods=['POST'])
def import_pgn():
    data = request.json
    pgn_text = data.get('pgn')
    try:
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        if not game:
            return jsonify({'status': 'error', 'message': 'Invalid PGN'}), 400
        board = game.board()
        analysis_list = []
        for move in game.mainline_moves():
            board.push(move)
            analysis = analyze_position(board.fen())
            suspicion_score = anomaly_detector.predict_suspicion(board.fen(), analysis['best_move'], analysis['evaluation'])
            analysis_list.append({'move': move.uci(),'fen': board.fen(),'best_move': analysis['best_move'],'evaluation': analysis['evaluation'],'suspicion_score': suspicion_score})
        suspicion_scores = [a['suspicion_score'] for a in analysis_list]
        avg_suspicion = np.mean(suspicion_scores) if suspicion_scores else 0
        max_suspicion = np.max(suspicion_scores) if suspicion_scores else 0
        return jsonify({'status': 'success','game_info': {'white': game.headers.get('White', 'Unknown'),'black': game.headers.get('Black', 'Unknown'),'result': game.headers.get('Result', '*'),'date': game.headers.get('Date', 'Unknown')},'analysis': analysis_list,'summary': {'total_moves': len(analysis_list),'avg_suspicion': float(avg_suspicion),'max_suspicion': float(max_suspicion),'suspicious_moves': len([a for a in analysis_list if a['suspicion_score'] > SUSPICION_THRESHOLD])}})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
@app.route('/api/capture_board', methods=['POST'])
def capture_board():
    global board_detector
    try:
        if board_detector is None:
            board_detector = BoardDetector(camera_index=0)
        frame = board_detector.capture_frame()
        fen = board_detector.get_fen_from_image(frame)
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        return jsonify({'status': 'success','fen': fen,'image': f'data:image/jpeg;base64,{frame_base64}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to chess cheat detection server'})
@socketio.on('request_analysis')
def handle_analysis_request(data):
    fen = data.get('fen')
    try:
        analysis = analyze_position(fen)
        suspicion_score = anomaly_detector.predict_suspicion(fen, analysis['best_move'], analysis['evaluation'])
        emit('analysis_result', {'best_move': analysis['best_move'],'evaluation': analysis['evaluation'],'suspicion_score': suspicion_score})
    except Exception as e:
        emit('analysis_result', {'error': str(e)})
if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
