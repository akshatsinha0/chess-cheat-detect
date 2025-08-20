

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import chess.pgn
import io
import hashlib
from urllib.parse import urljoin
import mysql.connector
from collections import deque
import threading
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GameData:
    """Structured game data"""
    game_id: str
    white_player: str
    black_player: str
    white_rating: int
    black_rating: int
    time_control: str
    result: str
    pgn: str
    opening: str
    eco: str
    date_played: datetime
    platform: str
    game_url: str
    moves: List[str]
    clock_times: List[float]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'game_id': self.game_id,
            'white_player': self.white_player,
            'black_player': self.black_player,
            'white_rating': self.white_rating,
            'black_rating': self.black_rating,
            'time_control': self.time_control,
            'result': self.result,
            'pgn': self.pgn,
            'opening': self.opening,
            'eco': self.eco,
            'date_played': self.date_played.isoformat() if self.date_played else None,
            'platform': self.platform,
            'game_url': self.game_url,
            'moves': self.moves,
            'clock_times': self.clock_times
        }


class RateLimiter:
    """Rate limiting for API/scraping requests"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def can_proceed(self) -> bool:
        """Check if we can make a request"""
        with self.lock:
            now = time.time()
            
            # Remove old requests outside time window
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # Check if we can proceed
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            return False
    
    def wait_if_needed(self):
        """Wait if rate limit exceeded"""
        while not self.can_proceed():
            time.sleep(1)


class ChessComScraper:
    """Scraper for Chess.com games"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize Chess.com scraper
        
        Args:
            headless: Run browser in headless mode
        """
        self.base_url = "https://www.chess.com"
        self.api_base = "https://api.chess.com/pub"
        self.rate_limiter = RateLimiter(max_requests=5, time_window=60)
        
        # Setup Selenium driver
        self.driver = self._setup_driver(headless)
        
        # Authentication state
        self.authenticated = False
        self.session_cookies = None
    
    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Setup Chrome driver with options"""
        options = Options()
        
        if headless:
            options.add_argument('--headless')
        
        # Anti-detection measures
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Performance optimizations
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=options)
        
        # Bypass detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Chess.com"""
        try:
            self.rate_limiter.wait_if_needed()
            
            # Navigate to login page
            self.driver.get(f"{self.base_url}/login")
            
            # Wait for login form
            wait = WebDriverWait(self.driver, 10)
            
            # Enter credentials
            username_field = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            
            username_field.send_keys(username)
            password_field.send_keys(password)
            
            # Submit form
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for redirect
            time.sleep(3)
            
            # Check if logged in
            if "home" in self.driver.current_url or "member" in self.driver.current_url:
                self.authenticated = True
                self.session_cookies = self.driver.get_cookies()
                logger.info(f"Successfully authenticated as {username}")
                return True
            
            logger.error("Authentication failed")
            return False
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def get_player_games(self, username: str, limit: int = 50) -> List[GameData]:
        """Get recent games for a player"""
        games = []
        
        try:
            # Use API for public game data
            self.rate_limiter.wait_if_needed()
            
            # Get player's recent games via API
            current_date = datetime.now()
            year = current_date.year
            month = current_date.month
            
            api_url = f"{self.api_base}/player/{username}/games/{year}/{month:02d}"
            
            response = requests.get(api_url, headers={
                'User-Agent': 'ChessCheatDetection/1.0'
            })
            
            if response.status_code == 200:
                data = response.json()
                
                for game_data in data.get('games', [])[:limit]:
                    # Parse game data
                    game = self._parse_api_game(game_data, username)
                    games.append(game)
            
        except Exception as e:
            logger.error(f"Error fetching games for {username}: {e}")
        
        return games
    
    def _parse_api_game(self, game_data: Dict, username: str) -> GameData:
        """Parse game data from API response"""
        # Extract basic info
        white_player = game_data.get('white', {}).get('username', '')
        black_player = game_data.get('black', {}).get('username', '')
        
        # Parse PGN
        pgn_text = game_data.get('pgn', '')
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        
        # Extract moves
        moves = []
        if game:
            for move in game.mainline_moves():
                moves.append(move.uci())
        
        # Extract clock times from comments
        clock_times = self._extract_clock_times(pgn_text)
        
        return GameData(
            game_id=game_data.get('url', '').split('/')[-1],
            white_player=white_player,
            black_player=black_player,
            white_rating=game_data.get('white', {}).get('rating', 0),
            black_rating=game_data.get('black', {}).get('rating', 0),
            time_control=game_data.get('time_control', ''),
            result=self._normalize_result(game_data.get('white', {}).get('result', '')),
            pgn=pgn_text,
            opening=game.headers.get('Opening', '') if game else '',
            eco=game.headers.get('ECO', '') if game else '',
            date_played=datetime.fromtimestamp(game_data.get('end_time', 0)),
            platform='chess.com',
            game_url=game_data.get('url', ''),
            moves=moves,
            clock_times=clock_times
        )
    
    def _extract_clock_times(self, pgn_text: str) -> List[float]:
        """Extract clock times from PGN comments"""
        clock_times = []
        
        import re
        pattern = r'\[%clk (\d+):(\d+):(\d+)\]'
        
        for match in re.finditer(pattern, pgn_text):
            hours, minutes, seconds = map(int, match.groups())
            total_seconds = hours * 3600 + minutes * 60 + seconds
            clock_times.append(total_seconds)
        
        return clock_times
    
    def _normalize_result(self, result: str) -> str:
        """Normalize result string"""
        if result in ['win', 'resigned', 'timeout']:
            return '1-0'
        elif result in ['checkmated', 'timeout']:
            return '0-1'
        elif result in ['draw', 'agreed', 'repetition', 'stalemate', 'insufficient']:
            return '1/2-1/2'
        return result
    
    def close(self):
        """Close browser driver"""
        if self.driver:
            self.driver.quit()


class LichessScraper:
    """Scraper for Lichess games"""
    
    def __init__(self):
        """Initialize Lichess scraper"""
        self.base_url = "https://lichess.org"
        self.api_base = "https://lichess.org/api"
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
        
        # Lichess API token (optional for higher rate limits)
        self.api_token = None
    
    def set_api_token(self, token: str):
        """Set Lichess API token"""
        self.api_token = token
    
    def get_player_games(self, username: str, limit: int = 50) -> List[GameData]:
        """Get recent games for a player"""
        games = []
        
        try:
            self.rate_limiter.wait_if_needed()
            
            # API endpoint
            url = f"{self.api_base}/games/user/{username}"
            
            # Parameters
            params = {
                'max': limit,
                'moves': 'true',
                'clocks': 'true',
                'opening': 'true',
                'pgnInJson': 'true'
            }
            
            # Headers
            headers = {
                'Accept': 'application/x-ndjson'
            }
            
            if self.api_token:
                headers['Authorization'] = f'Bearer {self.api_token}'
            
            # Make request
            response = requests.get(url, params=params, headers=headers, stream=True)
            
            if response.status_code == 200:
                # Parse NDJSON response
                for line in response.iter_lines():
                    if line:
                        game_data = json.loads(line)
                        game = self._parse_lichess_game(game_data, username)
                        games.append(game)
            else:
                logger.error(f"Failed to fetch Lichess games: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error fetching Lichess games: {e}")
        
        return games
    
    def _parse_lichess_game(self, game_data: Dict, username: str) -> GameData:
        """Parse Lichess game data"""
        # Extract players
        white_player = game_data.get('players', {}).get('white', {}).get('user', {}).get('name', '')
        black_player = game_data.get('players', {}).get('black', {}).get('user', {}).get('name', '')
        
        # Extract moves
        moves = game_data.get('moves', '').split(' ')
        
        # Extract clock times
        clock_times = []
        if 'clocks' in game_data:
            # Convert centiseconds to seconds
            clock_times = [c / 100 for c in game_data['clocks']]
        
        # Generate PGN
        pgn_text = self._generate_pgn(game_data)
        
        return GameData(
            game_id=game_data.get('id', ''),
            white_player=white_player,
            black_player=black_player,
            white_rating=game_data.get('players', {}).get('white', {}).get('rating', 0),
            black_rating=game_data.get('players', {}).get('black', {}).get('rating', 0),
            time_control=f"{game_data.get('clock', {}).get('initial', 0)}+{game_data.get('clock', {}).get('increment', 0)}",
            result=self._get_result(game_data),
            pgn=pgn_text,
            opening=game_data.get('opening', {}).get('name', ''),
            eco=game_data.get('opening', {}).get('eco', ''),
            date_played=datetime.fromtimestamp(game_data.get('createdAt', 0) / 1000),
            platform='lichess',
            game_url=f"https://lichess.org/{game_data.get('id', '')}",
            moves=moves,
            clock_times=clock_times
        )
    
    def _generate_pgn(self, game_data: Dict) -> str:
        """Generate PGN from Lichess game data"""
        headers = []
        
        # Standard headers
        headers.append(f'[Event "{game_data.get("perf", "")} game"]')
        headers.append(f'[Site "https://lichess.org/{game_data.get("id", "")}"]')
        headers.append(f'[Date "{datetime.fromtimestamp(game_data.get("createdAt", 0) / 1000).strftime("%Y.%m.%d")}"]')
        headers.append(f'[White "{game_data.get("players", {}).get("white", {}).get("user", {}).get("name", "")}"]')
        headers.append(f'[Black "{game_data.get("players", {}).get("black", {}).get("user", {}).get("name", "")}"]')
        headers.append(f'[Result "{self._get_result(game_data)}"]')
        
        if 'opening' in game_data:
            headers.append(f'[ECO "{game_data["opening"].get("eco", "")}"]')
            headers.append(f'[Opening "{game_data["opening"].get("name", "")}"]')
        
        # Moves
        moves = game_data.get('moves', '')
        
        pgn = '\n'.join(headers) + '\n\n' + moves
        return pgn
    
    def _get_result(self, game_data: Dict) -> str:
        """Get game result"""
        status = game_data.get('status', '')
        winner = game_data.get('winner', '')
        
        if winner == 'white':
            return '1-0'
        elif winner == 'black':
            return '0-1'
        elif status in ['draw', 'stalemate']:
            return '1/2-1/2'
        
        return '*'


# Backward compatible GameScraper class
class GameScraper:
    """Backward compatible wrapper for unified scraper"""
    
    def __init__(self, username: str = None, password: str = None, driver_path: str = None):
        self.username = username
        self.password = password
        self.chesscom_scraper = ChessComScraper()
        self.lichess_scraper = LichessScraper()
        
        if username and password:
            self.login()
    
    def login(self, url: str = "https://www.chess.com/login"):
        """Login to Chess.com"""
        if self.username and self.password:
            self.chesscom_scraper.authenticate(self.username, self.password)
    
    def fetch_pgn(self, game_url: str) -> str:
        """Fetch PGN from game URL"""
        if 'chess.com' in game_url:
            games = self.chesscom_scraper.get_player_games(self.username, limit=1)
            if games:
                return games[0].pgn
        elif 'lichess.org' in game_url:
            game_id = game_url.split('/')[-1]
            # Would need to implement single game fetch
            pass
        return ""
    
    def parse_pgn(self, pgn_text: str):
        """Parse PGN text"""
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        return game
    
    def close(self):
        """Close resources"""
        self.chesscom_scraper.close()
