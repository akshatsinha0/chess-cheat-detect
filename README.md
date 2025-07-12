# Chess Cheat Detection System

A real-time chess cheat detection system designed for online chess platforms like Chess.com, Lichess, and FIDE Online Arena. This system uses computer vision, machine learning, and chess engine analysis to detect suspicious playing patterns.

## Features

### Core Components
- **Stockfish Integration**: Deep move analysis using the powerful Stockfish chess engine
- **Computer Vision**: OpenCV-based board detection and piece recognition from camera feeds
- **Machine Learning**: TensorFlow/Scikit-learn powered anomaly detection
- **Web Interface**: Modern Flask + React-based frontend with real-time analysis
- **Database Support**: MySQL integration for game logging and analysis history
- **Docker Support**: Fully containerized for easy deployment

### Detection Capabilities
- Real-time move analysis and comparison with engine recommendations
- Pattern recognition for unnaturally consistent play
- Critical position accuracy analysis
- Move time variance detection
- Historical game analysis via PGN import

## Project Structure

```
chess-cheat-detection/
├── src/
│   ├── core/
│   │   └── stockfish_engine.py    # Stockfish integration
│   ├── detection/
│   │   ├── board_detector.py      # Camera board detection
│   │   └── piece_recognizer.py    # CNN-based piece recognition
│   ├── ml/
│   │   ├── anomaly_detector.py    # Basic anomaly detection
│   │   └── train_cheat_detector.py # Advanced ML training
│   ├── utils/
│   │   └── game_scraper.py        # Selenium-based game scraping
│   └── web/
│       ├── app.py                 # Flask backend
│       ├── templates/             # HTML templates
│       └── static/                # CSS/JS assets
├── tests/                         # Comprehensive test suite
├── models/                        # Trained ML models
├── data/                          # Training data
└── bin/                          # Stockfish binaries
```

## Installation

### Prerequisites
- Python 3.8+
- Stockfish chess engine
- Webcam (for board detection features)
- MySQL (optional, for data persistence)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/chess-cheat-detection.git
cd chess-cheat-detection
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Download Stockfish binary:
   - Download from https://stockfishchess.org/download/
   - Place in `bin/stockfish/` directory

## Usage

### Web Interface

1. Start the Flask server:
```bash
python src/web/app.py
```

2. Open browser to `http://localhost:5000`

3. Features available:
   - **Play & Analyze**: Make moves and see real-time cheat detection
   - **Import PGN**: Analyze complete games for suspicious patterns
   - **Camera Capture**: Detect positions from physical boards
   - **FEN Analysis**: Analyze specific positions

### Command Line

1. Run basic detection:
```bash
python main.py
```

2. Train ML model:
```bash
python src/ml/train_cheat_detector.py --epochs 50
```

### Docker Deployment

1. Build the image:
```bash
docker build -t chess-cheat-detector .
```

2. Run the container:
```bash
docker run -p 5000:5000 chess-cheat-detector
```

## API Endpoints

### REST API
- `POST /api/new_game` - Start a new game
- `POST /api/make_move` - Make a move and analyze
- `POST /api/analyze_fen` - Analyze a FEN position
- `POST /api/import_pgn` - Import and analyze PGN
- `POST /api/capture_board` - Capture board from camera

### WebSocket Events
- `connect` - Establish real-time connection
- `request_analysis` - Request position analysis
- `move_made` - Broadcast move updates

## Machine Learning Model

### Features
The ML model analyzes:
- Move accuracy compared to engine
- Consistency of play strength
- Time management patterns
- Critical position performance
- Material imbalance handling

### Training
To train with your own data:

1. Prepare PGN files:
   - Place legitimate games in `data/games/legitimate/`
   - Place known cheater games in `data/games/cheaters/`

2. Run training:
```bash
python src/ml/train_cheat_detector.py --data-dir data/games --epochs 100
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_board_detector.py
pytest tests/test_anomaly_detector.py
pytest tests/test_web_api.py

# Run with coverage
pytest --cov=src tests/
```

## Configuration

Edit `config.py` to customize:
- Stockfish engine path and depth
- ML model paths and thresholds
- Camera settings
- Database connections

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Future Enhancements

- [ ] Support for more chess engines (Leela, Komodo)
- [ ] Advanced neural network architectures
- [ ] Real-time streaming analysis
- [ ] Mobile app support
- [ ] Integration with chess platforms APIs
- [ ] Multi-language support

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Stockfish team for the amazing chess engine
- Chess.com and Lichess for inspiration
- OpenCV community for computer vision tools
- TensorFlow team for ML framework
