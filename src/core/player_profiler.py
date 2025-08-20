

import uuid
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import mysql.connector
from collections import defaultdict
import user_agents
from dataclasses import dataclass, asdict
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PlayerProfile:
    """Player profile data structure"""
    player_id: str
    username: str
    platform: str
    rating: int
    rating_deviation: int
    total_games: int
    flagged_games: int
    trust_score: float
    account_created: datetime
    last_active: datetime
    is_banned: bool
    
    # Extended profile attributes
    peak_rating: int = 1200
    lowest_rating: int = 1200
    win_rate: float = 0.5
    avg_game_length: float = 40.0
    preferred_time_control: str = "blitz"
    main_openings: List[str] = None
    playing_schedule: Dict = None
    device_fingerprints: List[str] = None
    known_ips: List[str] = None
    
    def __post_init__(self):
        if self.main_openings is None:
            self.main_openings = []
        if self.playing_schedule is None:
            self.playing_schedule = {}
        if self.device_fingerprints is None:
            self.device_fingerprints = []
        if self.known_ips is None:
            self.known_ips = []


@dataclass
class SessionData:
    """Session tracking data structure"""
    session_id: str
    player_id: str
    start_time: datetime
    end_time: Optional[datetime]
    games_played: int
    avg_accuracy: float
    avg_think_time: float
    session_entropy: float
    device_fingerprint: str
    ip_address: str
    network_metrics: Dict
    anomaly_flags: List[str]
    
    def duration_minutes(self) -> float:
        """Calculate session duration in minutes"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return (datetime.now() - self.start_time).total_seconds() / 60


@dataclass
class DeviceFingerprint:
    """Device fingerprint data structure"""
    fingerprint_id: str
    user_agent: str
    screen_resolution: str
    timezone: str
    language: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    canvas_fingerprint: str
    audio_fingerprint: str
    fonts_hash: str
    plugins_hash: str
    trust_score: float
    
    def generate_hash(self) -> str:
        """Generate unique hash for device fingerprint"""
        data = f"{self.user_agent}{self.screen_resolution}{self.timezone}{self.canvas_fingerprint}"
        return hashlib.sha256(data.encode()).hexdigest()


class PlayerProfileManager:
    """
    Manages player profiles with longitudinal tracking
    """
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        Initialize player profile manager
        
        Args:
            db_config: Database configuration
        """
        self.db_config = db_config or {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'chess_cheat_detection'
        }
        
        # In-memory cache for active profiles
        self.profile_cache = {}
        self.session_cache = {}
        
        # Cohort analysis parameters
        self.cohort_groups = {
            'beginner': (0, 1200),
            'intermediate': (1200, 1600),
            'advanced': (1600, 2000),
            'expert': (2000, 2400),
            'master': (2400, 3000)
        }
        
        # Initialize database tables
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables if they don't exist"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Check if tables exist, create if not
            cursor.execute("SHOW TABLES LIKE 'players'")
            if not cursor.fetchone():
                logger.info("Creating database tables...")
                # Tables should already be created from schema.sql
                # This is a fallback check
            
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def create_player_profile(self, 
                            username: str,
                            platform: str,
                            rating: int = 1200,
                            device_data: Optional[Dict] = None) -> PlayerProfile:
        """
        Create a new player profile
        
        Args:
            username: Player username
            platform: Chess platform (chess.com, lichess, etc.)
            rating: Initial rating
            device_data: Device fingerprint data
            
        Returns:
            Created PlayerProfile object
        """
        player_id = str(uuid.uuid4())
        
        profile = PlayerProfile(
            player_id=player_id,
            username=username,
            platform=platform,
            rating=rating,
            rating_deviation=350,
            total_games=0,
            flagged_games=0,
            trust_score=1.0,
            account_created=datetime.now(),
            last_active=datetime.now(),
            is_banned=False,
            peak_rating=rating,
            lowest_rating=rating
        )
        
        # Process device fingerprint if provided
        if device_data:
            fingerprint = self._process_device_fingerprint(device_data)
            profile.device_fingerprints.append(fingerprint.fingerprint_id)
            self._save_device_fingerprint(player_id, fingerprint)
        
        # Save to database
        self._save_profile_to_db(profile)
        
        # Cache profile
        self.profile_cache[player_id] = profile
        
        logger.info(f"Created profile for {username} (ID: {player_id})")
        return profile
    
    def get_player_profile(self, player_id: str) -> Optional[PlayerProfile]:
        """
        Get player profile by ID
        
        Args:
            player_id: Player ID
            
        Returns:
            PlayerProfile object or None
        """
        # Check cache first
        if player_id in self.profile_cache:
            return self.profile_cache[player_id]
        
        # Load from database
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT * FROM players WHERE player_id = %s
            """, (player_id,))
            
            row = cursor.fetchone()
            if row:
                profile = PlayerProfile(
                    player_id=row['player_id'],
                    username=row['username'],
                    platform=row['platform'],
                    rating=row['rating'],
                    rating_deviation=row['rating_deviation'],
                    total_games=row['total_games'],
                    flagged_games=row['flagged_games'],
                    trust_score=row['trust_score'],
                    account_created=row['account_created'],
                    last_active=row['last_active'],
                    is_banned=bool(row['is_banned'])
                )
                
                # Load extended attributes
                self._load_extended_attributes(profile)
                
                # Cache profile
                self.profile_cache[player_id] = profile
                
                cursor.close()
                conn.close()
                return profile
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading profile {player_id}: {e}")
        
        return None
    
    def update_player_profile(self, 
                            player_id: str,
                            updates: Dict) -> bool:
        """
        Update player profile
        
        Args:
            player_id: Player ID
            updates: Dictionary of updates
            
        Returns:
            Success status
        """
        profile = self.get_player_profile(player_id)
        if not profile:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        # Update peak/lowest ratings
        if 'rating' in updates:
            profile.peak_rating = max(profile.peak_rating, updates['rating'])
            profile.lowest_rating = min(profile.lowest_rating, updates['rating'])
        
        # Update last active
        profile.last_active = datetime.now()
        
        # Save to database
        self._save_profile_to_db(profile)
        
        # Update cache
        self.profile_cache[player_id] = profile
        
        return True
    
    def start_session(self, 
                     player_id: str,
                     device_data: Dict,
                     ip_address: str) -> SessionData:
        """
        Start a new playing session
        
        Args:
            player_id: Player ID
            device_data: Device fingerprint data
            ip_address: Player's IP address
            
        Returns:
            SessionData object
        """
        session_id = str(uuid.uuid4())
        
        # Process device fingerprint
        fingerprint = self._process_device_fingerprint(device_data)
        
        # Check for device consistency
        profile = self.get_player_profile(player_id)
        if profile and fingerprint.fingerprint_id not in profile.device_fingerprints:
            # New device detected
            logger.warning(f"New device detected for player {player_id}")
            profile.device_fingerprints.append(fingerprint.fingerprint_id)
            self._save_device_fingerprint(player_id, fingerprint)
        
        # Create session
        session = SessionData(
            session_id=session_id,
            player_id=player_id,
            start_time=datetime.now(),
            end_time=None,
            games_played=0,
            avg_accuracy=0.0,
            avg_think_time=0.0,
            session_entropy=0.0,
            device_fingerprint=fingerprint.fingerprint_id,
            ip_address=ip_address,
            network_metrics={},
            anomaly_flags=[]
        )
        
        # Save to database
        self._save_session_to_db(session)
        
        # Cache session
        self.session_cache[session_id] = session
        
        logger.info(f"Started session {session_id} for player {player_id}")
        return session
    
    def end_session(self, session_id: str) -> bool:
        """
        End a playing session
        
        Args:
            session_id: Session ID
            
        Returns:
            Success status
        """
        if session_id not in self.session_cache:
            return False
        
        session = self.session_cache[session_id]
        session.end_time = datetime.now()
        
        # Calculate session statistics
        self._calculate_session_statistics(session)
        
        # Update player profile
        profile = self.get_player_profile(session.player_id)
        if profile:
            self._update_profile_from_session(profile, session)
        
        # Save to database
        self._save_session_to_db(session)
        
        # Remove from cache
        del self.session_cache[session_id]
        
        logger.info(f"Ended session {session_id}")
        return True
    
    def track_game_in_session(self,
                            session_id: str,
                            game_data: Dict) -> bool:
        """
        Track a game within a session
        
        Args:
            session_id: Session ID
            game_data: Game data including accuracy, think time, etc.
            
        Returns:
            Success status
        """
        if session_id not in self.session_cache:
            return False
        
        session = self.session_cache[session_id]
        session.games_played += 1
        
        # Update running averages
        n = session.games_played
        session.avg_accuracy = ((n - 1) * session.avg_accuracy + game_data.get('accuracy', 0)) / n
        session.avg_think_time = ((n - 1) * session.avg_think_time + game_data.get('avg_think_time', 0)) / n
        
        # Update session entropy
        session.session_entropy = self._calculate_session_entropy(session, game_data)
        
        # Check for anomalies
        anomalies = self._detect_session_anomalies(session, game_data)
        session.anomaly_flags.extend(anomalies)
        
        return True
    
    def get_cohort_statistics(self, 
                            rating: int,
                            time_control: str) -> Dict:
        """
        Get statistics for a player's cohort
        
        Args:
            rating: Player rating
            time_control: Time control category
            
        Returns:
            Cohort statistics dictionary
        """
        cohort = self._get_cohort_group(rating)
        
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            # Get cohort thresholds
            cursor.execute("""
                SELECT * FROM cohort_thresholds 
                WHERE rating_min <= %s AND rating_max > %s 
                AND time_control_category = %s
            """, (rating, rating, time_control))
            
            thresholds = cursor.fetchone()
            
            # Get cohort statistics
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT p.player_id) as player_count,
                    AVG(pf.accuracy_consistency) as avg_accuracy,
                    AVG(pf.avg_think_time) as avg_think_time,
                    AVG(pf.blunder_rate) as avg_blunder_rate,
                    STD(pf.accuracy_consistency) as accuracy_std
                FROM players p
                JOIN player_features pf ON p.player_id = pf.player_id
                WHERE p.rating BETWEEN %s AND %s
            """, cohort[1])
            
            stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                'cohort': cohort[0],
                'rating_range': cohort[1],
                'thresholds': thresholds,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting cohort statistics: {e}")
            return {}
    
    def calculate_trust_score(self, player_id: str) -> float:
        """
        Calculate player trust score based on historical behavior
        
        Args:
            player_id: Player ID
            
        Returns:
            Trust score (0-1)
        """
        profile = self.get_player_profile(player_id)
        if not profile:
            return 0.5
        
        # Base trust score
        trust_score = 1.0
        
        # Factor 1: Flagged games ratio
        if profile.total_games > 0:
            flagged_ratio = profile.flagged_games / profile.total_games
            trust_score -= flagged_ratio * 0.3
        
        # Factor 2: Account age
        account_age_days = (datetime.now() - profile.account_created).days
        if account_age_days < 30:
            trust_score -= 0.1  # New accounts are less trusted
        elif account_age_days > 365:
            trust_score += 0.1  # Old accounts are more trusted
        
        # Factor 3: Device consistency
        if len(profile.device_fingerprints) > 5:
            trust_score -= 0.1  # Too many devices is suspicious
        
        # Factor 4: Rating volatility
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT STD(rating) as rating_std 
                FROM (
                    SELECT rating FROM games 
                    WHERE white_player_id = %s OR black_player_id = %s 
                    ORDER BY game_date DESC LIMIT 50
                ) as recent_games
            """, (player_id, player_id))
            
            result = cursor.fetchone()
            if result and result[0]:
                rating_std = result[0]
                if rating_std > 100:
                    trust_score -= 0.1  # High volatility is suspicious
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error calculating rating volatility: {e}")
        
        # Factor 5: Warning history
        warning_penalty = self._get_warning_penalty(player_id)
        trust_score -= warning_penalty
        
        # Ensure trust score is in valid range
        trust_score = max(0.0, min(1.0, trust_score))
        
        # Update profile
        profile.trust_score = trust_score
        self._save_profile_to_db(profile)
        
        return trust_score
    
    def detect_device_anomalies(self, 
                               player_id: str,
                               current_device: Dict) -> List[str]:
        """
        Detect device-related anomalies
        
        Args:
            player_id: Player ID
            current_device: Current device data
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        profile = self.get_player_profile(player_id)
        
        if not profile:
            return anomalies
        
        # Check for device switching patterns
        if len(profile.device_fingerprints) > 1:
            # Get recent device usage
            recent_devices = self._get_recent_device_usage(player_id)
            
            # Check for rapid device switching
            if len(recent_devices) > 3:
                anomalies.append("rapid_device_switching")
            
            # Check for simultaneous device usage
            if self._check_simultaneous_devices(player_id):
                anomalies.append("simultaneous_devices")
        
        # Check for VPN/proxy indicators
        if self._detect_vpn_proxy(current_device):
            anomalies.append("vpn_proxy_detected")
        
        # Check for browser automation
        if self._detect_automation(current_device):
            anomalies.append("automation_detected")
        
        return anomalies
    
    def get_longitudinal_trends(self, 
                              player_id: str,
                              days: int = 30) -> Dict:
        """
        Get longitudinal trends for a player
        
        Args:
            player_id: Player ID
            days: Number of days to analyze
            
        Returns:
            Dictionary of trends
        """
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            # Get player features over time
            cursor.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    AVG(session_entropy) as avg_entropy,
                    AVG(accuracy_consistency) as avg_accuracy,
                    AVG(avg_think_time) as avg_think_time,
                    AVG(sandbagging_score) as avg_sandbagging,
                    COUNT(*) as games_played
                FROM player_features
                WHERE player_id = %s 
                AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, (player_id, days))
            
            daily_data = cursor.fetchall()
            
            # Calculate trends
            trends = {
                'dates': [],
                'entropy': [],
                'accuracy': [],
                'think_time': [],
                'sandbagging': [],
                'games': []
            }
            
            for row in daily_data:
                trends['dates'].append(row['date'])
                trends['entropy'].append(float(row['avg_entropy'] or 0))
                trends['accuracy'].append(float(row['avg_accuracy'] or 0))
                trends['think_time'].append(float(row['avg_think_time'] or 0))
                trends['sandbagging'].append(float(row['avg_sandbagging'] or 0))
                trends['games'].append(row['games_played'])
            
            # Calculate trend lines
            if len(trends['dates']) > 1:
                trends['entropy_trend'] = self._calculate_trend(trends['entropy'])
                trends['accuracy_trend'] = self._calculate_trend(trends['accuracy'])
                trends['think_time_trend'] = self._calculate_trend(trends['think_time'])
            
            cursor.close()
            conn.close()
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting longitudinal trends: {e}")
            return {}
    
    def _process_device_fingerprint(self, device_data: Dict) -> DeviceFingerprint:
        """Process and create device fingerprint"""
        # Parse user agent
        ua_string = device_data.get('user_agent', '')
        ua = user_agents.parse(ua_string)
        
        fingerprint = DeviceFingerprint(
            fingerprint_id=str(uuid.uuid4()),
            user_agent=ua_string,
            screen_resolution=device_data.get('screen_resolution', ''),
            timezone=device_data.get('timezone', ''),
            language=device_data.get('language', ''),
            platform=ua.os.family if ua else '',
            webgl_vendor=device_data.get('webgl_vendor', ''),
            webgl_renderer=device_data.get('webgl_renderer', ''),
            canvas_fingerprint=device_data.get('canvas_fingerprint', ''),
            audio_fingerprint=device_data.get('audio_fingerprint', ''),
            fonts_hash=device_data.get('fonts_hash', ''),
            plugins_hash=device_data.get('plugins_hash', ''),
            trust_score=1.0
        )
        
        # Generate unique hash
        fingerprint.fingerprint_id = fingerprint.generate_hash()
        
        return fingerprint
    
    def _save_profile_to_db(self, profile: PlayerProfile):
        """Save player profile to database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO players (
                    player_id, username, platform, rating, rating_deviation,
                    total_games, flagged_games, trust_score, account_created,
                    last_active, is_banned
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    rating = VALUES(rating),
                    rating_deviation = VALUES(rating_deviation),
                    total_games = VALUES(total_games),
                    flagged_games = VALUES(flagged_games),
                    trust_score = VALUES(trust_score),
                    last_active = VALUES(last_active),
                    is_banned = VALUES(is_banned)
            """, (
                profile.player_id, profile.username, profile.platform,
                profile.rating, profile.rating_deviation, profile.total_games,
                profile.flagged_games, profile.trust_score, profile.account_created,
                profile.last_active, profile.is_banned
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
    
    def _save_device_fingerprint(self, player_id: str, fingerprint: DeviceFingerprint):
        """Save device fingerprint to database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO device_fingerprints (
                    player_id, user_agent, screen_resolution, timezone,
                    language, platform, webgl_vendor, webgl_renderer,
                    canvas_fingerprint, audio_fingerprint, fonts_hash,
                    plugins_hash, trust_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    last_seen = NOW(),
                    trust_score = VALUES(trust_score)
            """, (
                player_id, fingerprint.user_agent, fingerprint.screen_resolution,
                fingerprint.timezone, fingerprint.language, fingerprint.platform,
                fingerprint.webgl_vendor, fingerprint.webgl_renderer,
                fingerprint.canvas_fingerprint, fingerprint.audio_fingerprint,
                fingerprint.fonts_hash, fingerprint.plugins_hash,
                fingerprint.trust_score
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving device fingerprint: {e}")
    
    def _save_session_to_db(self, session: SessionData):
        """Save session data to database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO player_features (
                    player_id, session_id, session_entropy, avg_think_time,
                    games_in_session, session_duration_minutes, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    session_entropy = VALUES(session_entropy),
                    avg_think_time = VALUES(avg_think_time),
                    games_in_session = VALUES(games_in_session),
                    session_duration_minutes = VALUES(session_duration_minutes)
            """, (
                session.player_id, session.session_id, session.session_entropy,
                session.avg_think_time, session.games_played,
                session.duration_minutes(), session.start_time
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving session: {e}")
    
    def _load_extended_attributes(self, profile: PlayerProfile):
        """Load extended attributes for a profile"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Load device fingerprints
            cursor.execute("""
                SELECT DISTINCT canvas_fingerprint 
                FROM device_fingerprints 
                WHERE player_id = %s
            """, (profile.player_id,))
            
            profile.device_fingerprints = [row[0] for row in cursor.fetchall()]
            
            # Load known IPs
            cursor.execute("""
                SELECT DISTINCT ip_address 
                FROM network_profiles 
                WHERE player_id = %s
            """, (profile.player_id,))
            
            profile.known_ips = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading extended attributes: {e}")
    
    def _calculate_session_statistics(self, session: SessionData):
        """Calculate final session statistics"""
        # This would aggregate all games in the session
        # For now, using the running averages already calculated
        pass
    
    def _update_profile_from_session(self, profile: PlayerProfile, session: SessionData):
        """Update player profile based on session data"""
        # Update total games
        profile.total_games += session.games_played
        
        # Update last active
        profile.last_active = datetime.now()
        
        # Check for suspicious patterns
        if len(session.anomaly_flags) > 3:
            profile.trust_score *= 0.95  # Reduce trust score
        
        self._save_profile_to_db(profile)
    
    def _calculate_session_entropy(self, session: SessionData, game_data: Dict) -> float:
        """Calculate session entropy based on move patterns"""
        # Simplified entropy calculation
        moves = game_data.get('moves', [])
        if not moves:
            return 0.5
        
        move_counts = defaultdict(int)
        for move in moves:
            move_counts[move[:2]] += 1
        
        total = sum(move_counts.values())
        entropy = 0
        
        for count in move_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * np.log2(p + 1e-10)
        
        return entropy / np.log2(len(move_counts) + 1)
    
    def _detect_session_anomalies(self, session: SessionData, game_data: Dict) -> List[str]:
        """Detect anomalies within a session"""
        anomalies = []
        
        # Check for accuracy spike
        if game_data.get('accuracy', 0) > session.avg_accuracy + 0.2:
            anomalies.append("accuracy_spike")
        
        # Check for time anomaly
        if abs(game_data.get('avg_think_time', 0) - session.avg_think_time) > 10:
            anomalies.append("time_anomaly")
        
        # Check for consistency
        if session.games_played > 5:
            if game_data.get('accuracy', 0) > 0.95:
                anomalies.append("perfect_play")
        
        return anomalies
    
    def _get_cohort_group(self, rating: int) -> Tuple[str, Tuple[int, int]]:
        """Get cohort group for a rating"""
        for group_name, (min_rating, max_rating) in self.cohort_groups.items():
            if min_rating <= rating < max_rating:
                return group_name, (min_rating, max_rating)
        return 'master', (2400, 3000)
    
    def _get_warning_penalty(self, player_id: str) -> float:
        """Get warning penalty for trust score calculation"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as warning_count,
                       SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical_count
                FROM warnings
                WHERE player_id = %s
                AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """, (player_id,))
            
            result = cursor.fetchone()
            if result:
                warning_count, critical_count = result
                penalty = (warning_count * 0.02) + (critical_count * 0.05)
                return min(penalty, 0.3)  # Cap at 0.3
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error getting warning penalty: {e}")
        
        return 0
    
    def _get_recent_device_usage(self, player_id: str) -> List[str]:
        """Get recent device usage for a player"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT canvas_fingerprint
                FROM device_fingerprints
                WHERE player_id = %s
                AND last_seen >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            """, (player_id,))
            
            devices = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting recent devices: {e}")
            return []
    
    def _check_simultaneous_devices(self, player_id: str) -> bool:
        """Check for simultaneous device usage"""
        # This would check for overlapping sessions from different devices
        # Simplified implementation
        return False
    
    def _detect_vpn_proxy(self, device_data: Dict) -> bool:
        """Detect VPN/proxy usage indicators"""
        # Check for known VPN indicators
        vpn_indicators = [
            'vpn', 'proxy', 'tor', 'relay',
            'anonymizer', 'hide', 'secure'
        ]
        
        ua = device_data.get('user_agent', '').lower()
        for indicator in vpn_indicators:
            if indicator in ua:
                return True
        
        # Check timezone mismatch
        # This would compare IP geolocation with reported timezone
        
        return False
    
    def _detect_automation(self, device_data: Dict) -> bool:
        """Detect browser automation indicators"""
        automation_indicators = [
            'headless', 'phantom', 'selenium',
            'puppeteer', 'playwright', 'webdriver'
        ]
        
        ua = device_data.get('user_agent', '').lower()
        for indicator in automation_indicators:
            if indicator in ua:
                return True
        
        # Check for missing standard browser features
        if not device_data.get('canvas_fingerprint'):
            return True
        
        return False
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in a series of values"""
        if len(values) < 2:
            return 0
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Linear regression
        slope, _ = np.polyfit(x, y, 1)
        return slope
    
    def export_profile(self, player_id: str, filepath: str):
        """Export player profile to file"""
        profile = self.get_player_profile(player_id)
        if profile:
            with open(filepath, 'wb') as f:
                pickle.dump(asdict(profile), f)
            logger.info(f"Exported profile {player_id} to {filepath}")
    
    def import_profile(self, filepath: str) -> PlayerProfile:
        """Import player profile from file"""
        with open(filepath, 'rb') as f:
            profile_dict = pickle.load(f)
        
        profile = PlayerProfile(**profile_dict)
        self._save_profile_to_db(profile)
        self.profile_cache[profile.player_id] = profile
        
        logger.info(f"Imported profile {profile.player_id}")
        return profile


if __name__ == "__main__":
    # Example usage
    manager = PlayerProfileManager()
    
    # Create a new player profile
    profile = manager.create_player_profile(
        username="TestPlayer",
        platform="chess.com",
        rating=1500,
        device_data={
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0',
            'screen_resolution': '1920x1080',
            'timezone': 'America/New_York',
            'canvas_fingerprint': 'abc123def456'
        }
    )
    
    print(f"Created profile: {profile.player_id}")
    
    # Start a session
    session = manager.start_session(
        player_id=profile.player_id,
        device_data={
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0',
            'screen_resolution': '1920x1080',
            'timezone': 'America/New_York',
            'canvas_fingerprint': 'abc123def456'
        },
        ip_address='192.168.1.1'
    )
    
    print(f"Started session: {session.session_id}")
    
    # Track a game
    manager.track_game_in_session(
        session_id=session.session_id,
        game_data={
            'accuracy': 0.85,
            'avg_think_time': 5.2,
            'moves': ['e2e4', 'e7e5', 'g1f3']
        }
    )
    
    # Calculate trust score
    trust_score = manager.calculate_trust_score(profile.player_id)
    print(f"Trust score: {trust_score}")
    
    # Get cohort statistics
    cohort_stats = manager.get_cohort_statistics(1500, 'blitz')
    print(f"Cohort statistics: {cohort_stats}")
