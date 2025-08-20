import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
import mysql.connector
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WarningSeverity(Enum):
    """Warning severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WarningType(Enum):
    """Types of warnings"""
    SUSPICIOUS_MOVES = "suspicious_moves"
    TIME_ANOMALY = "time_anomaly"
    ACCURACY_SPIKE = "accuracy_spike"
    NETWORK_ANOMALY = "network_anomaly"
    DEVICE_MISMATCH = "device_mismatch"
    PATTERN_VIOLATION = "pattern_violation"
    SANDBAGGING = "sandbagging"
    BOOSTING = "boosting"
    ENGINE_CORRELATION = "engine_correlation"
    AUTOMATION_DETECTED = "automation_detected"


@dataclass
class Warning:
    """Warning data structure"""
    warning_id: str
    player_id: str
    game_id: Optional[str]
    warning_type: WarningType
    severity: WarningSeverity
    confidence: float
    details: Dict
    triggered_at: datetime
    acknowledged: bool = False
    action_taken: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert warning to dictionary"""
        return {
            'warning_id': self.warning_id,
            'player_id': self.player_id,
            'game_id': self.game_id,
            'warning_type': self.warning_type.value,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'details': self.details,
            'triggered_at': self.triggered_at.isoformat(),
            'acknowledged': self.acknowledged,
            'action_taken': self.action_taken,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class WarningThreshold:
    """Configurable warning thresholds"""
    warning_type: WarningType
    low_threshold: float
    medium_threshold: float
    high_threshold: float
    critical_threshold: float
    time_window_minutes: int = 60
    max_occurrences: int = 3
    
    def get_severity(self, value: float) -> WarningSeverity:
        """Determine severity based on value"""
        if value >= self.critical_threshold:
            return WarningSeverity.CRITICAL
        elif value >= self.high_threshold:
            return WarningSeverity.HIGH
        elif value >= self.medium_threshold:
            return WarningSeverity.MEDIUM
        elif value >= self.low_threshold:
            return WarningSeverity.LOW
        return None


class DynamicWarningSystem:
    """
    Dynamic warning system with real-time alerts and progressive penalties
    """
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        Initialize warning system
        
        Args:
            db_config: Database configuration
        """
        self.db_config = db_config or {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'chess_cheat_detection'
        }
        
        # Active warnings cache
        self.active_warnings = {}
        
        # Warning thresholds
        self.thresholds = self._initialize_thresholds()
        
        # Notification settings
        self.notification_config = {
            'email_enabled': False,
            'websocket_enabled': True,
            'admin_emails': [],
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_user': '',
            'smtp_password': ''
        }
        
        # Progressive penalty levels
        self.penalty_levels = {
            1: {'name': 'First Warning', 'action': 'notify', 'duration_days': 0},
            2: {'name': 'Second Warning', 'action': 'restrict', 'duration_days': 1},
            3: {'name': 'Third Warning', 'action': 'suspend', 'duration_days': 3},
            4: {'name': 'Fourth Warning', 'action': 'suspend', 'duration_days': 7},
            5: {'name': 'Final Warning', 'action': 'ban', 'duration_days': 0}
        }
        
        # WebSocket connections for real-time notifications
        self.websocket_connections = {}
    
    def _initialize_thresholds(self) -> Dict[WarningType, WarningThreshold]:
        """Initialize default warning thresholds"""
        return {
            WarningType.SUSPICIOUS_MOVES: WarningThreshold(
                WarningType.SUSPICIOUS_MOVES,
                low_threshold=0.6,
                medium_threshold=0.75,
                high_threshold=0.85,
                critical_threshold=0.95
            ),
            WarningType.ACCURACY_SPIKE: WarningThreshold(
                WarningType.ACCURACY_SPIKE,
                low_threshold=0.15,
                medium_threshold=0.25,
                high_threshold=0.35,
                critical_threshold=0.45
            ),
            WarningType.TIME_ANOMALY: WarningThreshold(
                WarningType.TIME_ANOMALY,
                low_threshold=2.0,
                medium_threshold=3.0,
                high_threshold=4.0,
                critical_threshold=5.0
            ),
            WarningType.ENGINE_CORRELATION: WarningThreshold(
                WarningType.ENGINE_CORRELATION,
                low_threshold=0.7,
                medium_threshold=0.8,
                high_threshold=0.9,
                critical_threshold=0.95
            ),
            WarningType.SANDBAGGING: WarningThreshold(
                WarningType.SANDBAGGING,
                low_threshold=0.3,
                medium_threshold=0.5,
                high_threshold=0.7,
                critical_threshold=0.9
            )
        }
    
    def check_for_warnings(self, 
                          player_id: str,
                          game_id: str,
                          analysis_results: Dict) -> List[Warning]:
        """
        Check analysis results for warning conditions
        
        Args:
            player_id: Player ID
            game_id: Game ID
            analysis_results: Analysis results from detection systems
            
        Returns:
            List of triggered warnings
        """
        warnings = []
        
        # Check suspicious moves
        if 'anomaly_score' in analysis_results:
            warning = self._check_threshold(
                player_id, game_id,
                WarningType.SUSPICIOUS_MOVES,
                analysis_results['anomaly_score'],
                analysis_results
            )
            if warning:
                warnings.append(warning)
        
        # Check accuracy spike
        if 'accuracy_spike' in analysis_results:
            warning = self._check_threshold(
                player_id, game_id,
                WarningType.ACCURACY_SPIKE,
                abs(analysis_results['accuracy_spike']),
                analysis_results
            )
            if warning:
                warnings.append(warning)
        
        # Check time anomaly
        if 'time_anomaly' in analysis_results:
            warning = self._check_threshold(
                player_id, game_id,
                WarningType.TIME_ANOMALY,
                analysis_results['time_anomaly'],
                analysis_results
            )
            if warning:
                warnings.append(warning)
        
        # Check engine correlation
        if 'engine_correlation' in analysis_results:
            warning = self._check_threshold(
                player_id, game_id,
                WarningType.ENGINE_CORRELATION,
                analysis_results['engine_correlation'],
                analysis_results
            )
            if warning:
                warnings.append(warning)
        
        # Check for pattern violations
        if 'pattern_violations' in analysis_results:
            for violation in analysis_results['pattern_violations']:
                warning = self._create_warning(
                    player_id, game_id,
                    WarningType.PATTERN_VIOLATION,
                    WarningSeverity.MEDIUM,
                    0.7,
                    {'violation': violation}
                )
                warnings.append(warning)
        
        # Process and store warnings
        for warning in warnings:
            self._process_warning(warning)
        
        return warnings
    
    def _check_threshold(self,
                        player_id: str,
                        game_id: str,
                        warning_type: WarningType,
                        value: float,
                        details: Dict) -> Optional[Warning]:
        """Check if value exceeds threshold for warning type"""
        if warning_type not in self.thresholds:
            return None
        
        threshold = self.thresholds[warning_type]
        severity = threshold.get_severity(value)
        
        if severity:
            # Calculate confidence based on how far above threshold
            if severity == WarningSeverity.CRITICAL:
                confidence = min(1.0, value / threshold.critical_threshold)
            elif severity == WarningSeverity.HIGH:
                confidence = min(0.9, value / threshold.high_threshold)
            elif severity == WarningSeverity.MEDIUM:
                confidence = min(0.7, value / threshold.medium_threshold)
            else:
                confidence = min(0.5, value / threshold.low_threshold)
            
            return self._create_warning(
                player_id, game_id,
                warning_type, severity,
                confidence, details
            )
        
        return None
    
    def _create_warning(self,
                       player_id: str,
                       game_id: Optional[str],
                       warning_type: WarningType,
                       severity: WarningSeverity,
                       confidence: float,
                       details: Dict) -> Warning:
        """Create a new warning"""
        warning = Warning(
            warning_id=str(uuid.uuid4()),
            player_id=player_id,
            game_id=game_id,
            warning_type=warning_type,
            severity=severity,
            confidence=confidence,
            details=details,
            triggered_at=datetime.now()
        )
        
        return warning
    
    def _process_warning(self, warning: Warning):
        """Process a warning: store, notify, and apply penalties"""
        # Store in database
        self._save_warning_to_db(warning)
        
        # Add to active warnings
        if warning.player_id not in self.active_warnings:
            self.active_warnings[warning.player_id] = []
        self.active_warnings[warning.player_id].append(warning)
        
        # Send notifications
        self._send_notifications(warning)
        
        # Apply progressive penalties
        self._apply_penalties(warning)
        
        # Log warning
        logger.info(f"Warning triggered: {warning.warning_type.value} for player {warning.player_id}")
    
    def _send_notifications(self, warning: Warning):
        """Send notifications for warning"""
        # Player notification
        if warning.severity in [WarningSeverity.HIGH, WarningSeverity.CRITICAL]:
            self._notify_player(warning)
        
        # Admin notification for critical warnings
        if warning.severity == WarningSeverity.CRITICAL:
            self._notify_admins(warning)
        
        # Real-time WebSocket notification
        if self.notification_config['websocket_enabled']:
            self._send_websocket_notification(warning)
    
    def _notify_player(self, warning: Warning):
        """Send notification to player"""
        message = self._format_player_message(warning)
        
        # In-app notification (would be sent via WebSocket)
        if warning.player_id in self.websocket_connections:
            try:
                ws = self.websocket_connections[warning.player_id]
                ws.send(json.dumps({
                    'type': 'warning',
                    'data': warning.to_dict(),
                    'message': message
                }))
            except Exception as e:
                logger.error(f"Failed to send WebSocket notification: {e}")
    
    def _notify_admins(self, warning: Warning):
        """Send notification to administrators"""
        if not self.notification_config['email_enabled']:
            return
        
        subject = f"Critical Warning: {warning.warning_type.value}"
        body = self._format_admin_message(warning)
        
        for admin_email in self.notification_config['admin_emails']:
            self._send_email(admin_email, subject, body)
    
    def _send_email(self, recipient: str, subject: str, body: str):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.notification_config['smtp_user']
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.notification_config['smtp_server'],
                self.notification_config['smtp_port']
            )
            server.starttls()
            server.login(
                self.notification_config['smtp_user'],
                self.notification_config['smtp_password']
            )
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    def _send_websocket_notification(self, warning: Warning):
        """Send real-time WebSocket notification"""
        notification = {
            'type': 'warning_alert',
            'timestamp': datetime.now().isoformat(),
            'warning': warning.to_dict()
        }
        
        # Broadcast to all connected admins
        for connection_id, ws in self.websocket_connections.items():
            if connection_id.startswith('admin_'):
                try:
                    ws.send(json.dumps(notification))
                except Exception as e:
                    logger.error(f"WebSocket send failed: {e}")
    
    def _apply_penalties(self, warning: Warning):
        """Apply progressive penalties based on warning history"""
        # Get warning count for player
        warning_count = self._get_player_warning_count(
            warning.player_id,
            days=30
        )
        
        # Determine penalty level
        penalty_level = min(warning_count, 5)
        penalty = self.penalty_levels[penalty_level]
        
        # Apply penalty based on severity
        if warning.severity == WarningSeverity.CRITICAL:
            self._execute_penalty(warning.player_id, penalty, warning)
        elif warning.severity == WarningSeverity.HIGH and warning_count >= 3:
            self._execute_penalty(warning.player_id, penalty, warning)
    
    def _execute_penalty(self, player_id: str, penalty: Dict, warning: Warning):
        """Execute a penalty action"""
        action = penalty['action']
        duration_days = penalty['duration_days']
        
        if action == 'notify':
            # Just notification, no further action
            logger.info(f"Notification sent to player {player_id}")
        
        elif action == 'restrict':
            # Restrict certain features
            self._restrict_player(player_id, duration_days)
            warning.action_taken = f"Restricted for {duration_days} days"
        
        elif action == 'suspend':
            # Temporary suspension
            self._suspend_player(player_id, duration_days)
            warning.action_taken = f"Suspended for {duration_days} days"
        
        elif action == 'ban':
            # Permanent ban
            self._ban_player(player_id)
            warning.action_taken = "Permanently banned"
        
        # Update warning with action taken
        self._update_warning_action(warning.warning_id, warning.action_taken)
    
    def _restrict_player(self, player_id: str, duration_days: int):
        """Restrict player features"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Add restriction record
            cursor.execute("""
                INSERT INTO player_restrictions (
                    player_id, restriction_type, start_date, end_date
                ) VALUES (%s, %s, %s, %s)
            """, (
                player_id,
                'feature_restriction',
                datetime.now(),
                datetime.now() + timedelta(days=duration_days)
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Player {player_id} restricted for {duration_days} days")
        except Exception as e:
            logger.error(f"Failed to restrict player: {e}")
    
    def _suspend_player(self, player_id: str, duration_days: int):
        """Suspend player account"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Update player status
            cursor.execute("""
                UPDATE players 
                SET is_suspended = TRUE,
                    suspension_end = %s
                WHERE player_id = %s
            """, (
                datetime.now() + timedelta(days=duration_days),
                player_id
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Player {player_id} suspended for {duration_days} days")
        except Exception as e:
            logger.error(f"Failed to suspend player: {e}")
    
    def _ban_player(self, player_id: str):
        """Permanently ban player"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Update player status
            cursor.execute("""
                UPDATE players 
                SET is_banned = TRUE,
                    ban_date = %s,
                    trust_score = 0
                WHERE player_id = %s
            """, (datetime.now(), player_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Player {player_id} permanently banned")
        except Exception as e:
            logger.error(f"Failed to ban player: {e}")
    
    def acknowledge_warning(self, warning_id: str, admin_id: str) -> bool:
        """Acknowledge a warning"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE warnings 
                SET acknowledged = TRUE,
                    acknowledged_by = %s,
                    acknowledged_at = %s
                WHERE warning_id = %s
            """, (admin_id, datetime.now(), warning_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Update in cache
            for player_warnings in self.active_warnings.values():
                for warning in player_warnings:
                    if warning.warning_id == warning_id:
                        warning.acknowledged = True
                        break
            
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge warning: {e}")
            return False
    
    def resolve_warning(self, 
                       warning_id: str,
                       resolution: str,
                       admin_id: str) -> bool:
        """Resolve a warning"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE warnings 
                SET resolved = TRUE,
                    resolution = %s,
                    resolved_by = %s,
                    resolved_at = %s
                WHERE warning_id = %s
            """, (resolution, admin_id, datetime.now(), warning_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Update in cache
            for player_warnings in self.active_warnings.values():
                for warning in player_warnings:
                    if warning.warning_id == warning_id:
                        warning.resolved = True
                        warning.resolved_at = datetime.now()
                        break
            
            return True
        except Exception as e:
            logger.error(f"Failed to resolve warning: {e}")
            return False
    
    def get_player_warnings(self, 
                           player_id: str,
                           days: Optional[int] = None) -> List[Warning]:
        """Get warnings for a player"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT * FROM warnings 
                WHERE player_id = %s
            """
            params = [player_id]
            
            if days:
                query += " AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"
                params.append(days)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            warnings = []
            for row in rows:
                warning = Warning(
                    warning_id=row['warning_id'],
                    player_id=row['player_id'],
                    game_id=row['game_id'],
                    warning_type=WarningType(row['warning_type']),
                    severity=WarningSeverity(row['severity']),
                    confidence=row.get('confidence', 0.5),
                    details=json.loads(row['details']) if row['details'] else {},
                    triggered_at=row['created_at'],
                    acknowledged=row['acknowledged'],
                    action_taken=row['action_taken']
                )
                warnings.append(warning)
            
            cursor.close()
            conn.close()
            
            return warnings
            
        except Exception as e:
            logger.error(f"Failed to get player warnings: {e}")
            return []
    
    def get_active_warnings(self, 
                          severity_filter: Optional[WarningSeverity] = None) -> List[Warning]:
        """Get all active (unresolved) warnings"""
        active = []
        
        for player_warnings in self.active_warnings.values():
            for warning in player_warnings:
                if not warning.resolved:
                    if severity_filter is None or warning.severity == severity_filter:
                        active.append(warning)
        
        return sorted(active, key=lambda w: w.triggered_at, reverse=True)
    
    def update_thresholds(self, 
                         warning_type: WarningType,
                         thresholds: Dict[str, float]):
        """Update warning thresholds"""
        if warning_type in self.thresholds:
            threshold = self.thresholds[warning_type]
            
            if 'low' in thresholds:
                threshold.low_threshold = thresholds['low']
            if 'medium' in thresholds:
                threshold.medium_threshold = thresholds['medium']
            if 'high' in thresholds:
                threshold.high_threshold = thresholds['high']
            if 'critical' in thresholds:
                threshold.critical_threshold = thresholds['critical']
            
            logger.info(f"Updated thresholds for {warning_type.value}")
    
    def _get_player_warning_count(self, player_id: str, days: int) -> int:
        """Get warning count for player in time period"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM warnings 
                WHERE player_id = %s 
                AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (player_id, days))
            
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to get warning count: {e}")
            return 0
    
    def _save_warning_to_db(self, warning: Warning):
        """Save warning to database"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO warnings (
                    warning_id, player_id, game_id, warning_type,
                    severity, details, acknowledged, action_taken,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                warning.warning_id,
                warning.player_id,
                warning.game_id,
                warning.warning_type.value,
                warning.severity.value,
                json.dumps(warning.details),
                warning.acknowledged,
                warning.action_taken,
                warning.triggered_at
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save warning: {e}")
    
    def _update_warning_action(self, warning_id: str, action: str):
        """Update warning with action taken"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE warnings 
                SET action_taken = %s 
                WHERE warning_id = %s
            """, (action, warning_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update warning action: {e}")
    
    def _format_player_message(self, warning: Warning) -> str:
        """Format warning message for player"""
        severity_text = warning.severity.value.upper()
        type_text = warning.warning_type.value.replace('_', ' ').title()
        
        message = f"""
        ⚠️ {severity_text} WARNING
        
        Type: {type_text}
        Confidence: {warning.confidence:.1%}
        
        Our fair play system has detected unusual activity in your recent game.
        Please ensure you are playing fairly and following all rules.
        
        Repeated violations may result in account restrictions.
        """
        
        return message.strip()
    
    def _format_admin_message(self, warning: Warning) -> str:
        """Format warning message for administrators"""
        message = f"""
        CRITICAL WARNING ALERT
        
        Player ID: {warning.player_id}
        Game ID: {warning.game_id}
        Warning Type: {warning.warning_type.value}
        Severity: {warning.severity.value}
        Confidence: {warning.confidence:.1%}
        Time: {warning.triggered_at}
        
        Details:
        {json.dumps(warning.details, indent=2)}
        
        Previous Warnings: {self._get_player_warning_count(warning.player_id, 30)}
        
        Please review this case immediately.
        """
        
        return message.strip()
    
    def generate_warning_report(self, 
                               start_date: datetime,
                               end_date: datetime) -> Dict:
        """Generate warning statistics report"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            # Get warning statistics
            cursor.execute("""
                SELECT 
                    warning_type,
                    severity,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM warnings
                WHERE created_at BETWEEN %s AND %s
                GROUP BY warning_type, severity
            """, (start_date, end_date))
            
            stats = cursor.fetchall()
            
            # Get top flagged players
            cursor.execute("""
                SELECT 
                    player_id,
                    COUNT(*) as warning_count,
                    MAX(severity) as max_severity
                FROM warnings
                WHERE created_at BETWEEN %s AND %s
                GROUP BY player_id
                ORDER BY warning_count DESC
                LIMIT 10
            """, (start_date, end_date))
            
            top_players = cursor.fetchall()
            
            # Get resolution statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_warnings,
                    SUM(CASE WHEN acknowledged THEN 1 ELSE 0 END) as acknowledged,
                    SUM(CASE WHEN resolved THEN 1 ELSE 0 END) as resolved,
                    SUM(CASE WHEN action_taken IS NOT NULL THEN 1 ELSE 0 END) as actions_taken
                FROM warnings
                WHERE created_at BETWEEN %s AND %s
            """, (start_date, end_date))
            
            resolution_stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'warning_statistics': stats,
                'top_flagged_players': top_players,
                'resolution_statistics': resolution_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {}
    
    def register_websocket(self, connection_id: str, websocket_connection):
        """Register WebSocket connection for real-time notifications"""
        self.websocket_connections[connection_id] = websocket_connection
        logger.info(f"WebSocket registered: {connection_id}")
    
    def unregister_websocket(self, connection_id: str):
        """Unregister WebSocket connection"""
        if connection_id in self.websocket_connections:
            del self.websocket_connections[connection_id]
            logger.info(f"WebSocket unregistered: {connection_id}")


if __name__ == "__main__":
    # Example usage
    warning_system = DynamicWarningSystem()
    
    # Simulate analysis results
    analysis_results = {
        'anomaly_score': 0.87,
        'accuracy_spike': 0.3,
        'engine_correlation': 0.82,
        'time_anomaly': 2.5,
        'pattern_violations': ['rapid_move_in_complex_position']
    }
    
    # Check for warnings
    warnings = warning_system.check_for_warnings(
        player_id="test_player_123",
        game_id="game_456",
        analysis_results=analysis_results
    )
    
    print(f"Triggered {len(warnings)} warnings:")
    for warning in warnings:
        print(f"  - {warning.warning_type.value}: {warning.severity.value} (confidence: {warning.confidence:.1%})")
    
    # Get player warnings
    player_warnings = warning_system.get_player_warnings("test_player_123", days=30)
    print(f"\nPlayer has {len(player_warnings)} warnings in last 30 days")
    
    # Generate report
    report = warning_system.generate_warning_report(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now()
    )
    print(f"\nWeekly report: {json.dumps(report, indent=2, default=str)}")
