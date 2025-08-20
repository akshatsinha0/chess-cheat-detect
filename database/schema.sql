-- Chess Cheat Detection Database Schema
-- Comprehensive schema with feature store for longitudinal player tracking

CREATE DATABASE IF NOT EXISTS chess_cheat_detection;
USE chess_cheat_detection;

-- Player profiles table
CREATE TABLE IF NOT EXISTS players (
    player_id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(128) UNIQUE NOT NULL,
    platform ENUM('chess.com', 'lichess', 'fide_online') NOT NULL,
    rating INT DEFAULT 1200,
    rating_deviation INT DEFAULT 350,
    total_games INT DEFAULT 0,
    flagged_games INT DEFAULT 0,
    account_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    trust_score FLOAT DEFAULT 1.0,
    is_banned BOOLEAN DEFAULT FALSE,
    INDEX idx_username (username),
    INDEX idx_platform_rating (platform, rating)
);

-- Games table
CREATE TABLE IF NOT EXISTS games (
    game_id VARCHAR(64) PRIMARY KEY,
    white_player_id VARCHAR(64),
    black_player_id VARCHAR(64),
    platform VARCHAR(32),
    time_control VARCHAR(32),
    rating_category VARCHAR(32),
    pgn TEXT,
    result VARCHAR(16),
    opening VARCHAR(128),
    eco_code VARCHAR(10),
    game_date TIMESTAMP,
    analysis_completed BOOLEAN DEFAULT FALSE,
    cheat_score FLOAT,
    is_flagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (white_player_id) REFERENCES players(player_id),
    FOREIGN KEY (black_player_id) REFERENCES players(player_id),
    INDEX idx_players (white_player_id, black_player_id),
    INDEX idx_date (game_date),
    INDEX idx_flagged (is_flagged)
);

-- Moves analysis table
CREATE TABLE IF NOT EXISTS move_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id VARCHAR(64),
    move_number INT,
    player_color ENUM('white', 'black'),
    move_uci VARCHAR(16),
    move_san VARCHAR(16),
    fen_before TEXT,
    fen_after TEXT,
    best_move VARCHAR(16),
    evaluation_before FLOAT,
    evaluation_after FLOAT,
    centipawn_loss INT,
    think_time_seconds FLOAT,
    is_book_move BOOLEAN DEFAULT FALSE,
    is_critical_position BOOLEAN DEFAULT FALSE,
    move_accuracy FLOAT,
    complexity_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE,
    INDEX idx_game_move (game_id, move_number),
    INDEX idx_accuracy (move_accuracy)
);

-- Player feature store (longitudinal tracking)
CREATE TABLE IF NOT EXISTS player_features (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(64),
    session_id VARCHAR(64),
    session_entropy FLOAT,
    opening_book_adherence FLOAT,
    avg_think_time FLOAT,
    think_time_variance FLOAT,
    blunder_rate FLOAT,
    accuracy_consistency FLOAT,
    sandbagging_score FLOAT,
    rating_volatility FLOAT,
    time_pressure_performance FLOAT,
    endgame_accuracy FLOAT,
    tactical_sharpness FLOAT,
    positional_understanding FLOAT,
    time_control VARCHAR(32),
    rating_pool INT,
    games_in_session INT,
    session_duration_minutes INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    INDEX idx_player_session (player_id, session_id),
    INDEX idx_timestamp (timestamp)
);

-- Device fingerprints
CREATE TABLE IF NOT EXISTS device_fingerprints (
    fingerprint_id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(64),
    user_agent TEXT,
    screen_resolution VARCHAR(32),
    timezone VARCHAR(64),
    language VARCHAR(16),
    platform VARCHAR(64),
    webgl_vendor VARCHAR(128),
    webgl_renderer VARCHAR(128),
    canvas_fingerprint VARCHAR(256),
    audio_fingerprint VARCHAR(256),
    fonts_hash VARCHAR(64),
    plugins_hash VARCHAR(64),
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    trust_score FLOAT DEFAULT 1.0,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    INDEX idx_player (player_id),
    INDEX idx_fingerprint (canvas_fingerprint)
);

-- Network profiles
CREATE TABLE IF NOT EXISTS network_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(64),
    session_id VARCHAR(64),
    ip_address VARCHAR(45),
    ip_country VARCHAR(2),
    ip_region VARCHAR(128),
    avg_latency_ms FLOAT,
    latency_variance FLOAT,
    jitter_ms FLOAT,
    packet_loss_rate FLOAT,
    connection_stability FLOAT,
    vpn_detected BOOLEAN DEFAULT FALSE,
    proxy_detected BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    INDEX idx_player_session (player_id, session_id),
    INDEX idx_ip (ip_address)
);

-- Think time distributions
CREATE TABLE IF NOT EXISTS think_time_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(64),
    game_id VARCHAR(64),
    position_type ENUM('opening', 'middlegame', 'endgame'),
    move_complexity ENUM('trivial', 'simple', 'moderate', 'complex', 'critical'),
    think_time_seconds FLOAT,
    expected_think_time FLOAT,
    deviation_score FLOAT,
    is_anomalous BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    INDEX idx_player_game (player_id, game_id),
    INDEX idx_anomalous (is_anomalous)
);

-- Opening book adherence tracking
CREATE TABLE IF NOT EXISTS opening_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(64),
    opening_name VARCHAR(128),
    eco_code VARCHAR(10),
    times_played INT DEFAULT 1,
    avg_accuracy FLOAT,
    book_deviation_move INT,
    win_rate FLOAT,
    consistency_score FLOAT,
    last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    INDEX idx_player_opening (player_id, eco_code)
);

-- Warning system logs
CREATE TABLE IF NOT EXISTS warnings (
    warning_id INT AUTO_INCREMENT PRIMARY KEY,
    player_id VARCHAR(64),
    game_id VARCHAR(64),
    warning_type ENUM('suspicious_moves', 'time_anomaly', 'accuracy_spike', 
                      'network_anomaly', 'device_mismatch', 'pattern_violation'),
    severity ENUM('low', 'medium', 'high', 'critical'),
    details JSON,
    acknowledged BOOLEAN DEFAULT FALSE,
    action_taken VARCHAR(256),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    INDEX idx_player_warnings (player_id),
    INDEX idx_severity (severity),
    INDEX idx_created (created_at)
);

-- Cohort thresholds (adaptive thresholds by rating and time control)
CREATE TABLE IF NOT EXISTS cohort_thresholds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rating_min INT,
    rating_max INT,
    time_control_category VARCHAR(32),
    accuracy_threshold FLOAT,
    consistency_threshold FLOAT,
    think_time_threshold FLOAT,
    entropy_threshold FLOAT,
    sandbagging_threshold FLOAT,
    sample_size INT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_cohort (rating_min, rating_max, time_control_category),
    INDEX idx_rating_range (rating_min, rating_max)
);

-- Isolation Forest model parameters
CREATE TABLE IF NOT EXISTS model_parameters (
    model_id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(128),
    model_version VARCHAR(32),
    parameters JSON,
    accuracy FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,
    false_positive_rate FLOAT,
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,
    INDEX idx_active (is_active),
    INDEX idx_version (model_version)
);

-- Audit logs for all detection events
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(64),
    player_id VARCHAR(64),
    game_id VARCHAR(64),
    action VARCHAR(128),
    details JSON,
    admin_id VARCHAR(64),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_player (player_id),
    INDEX idx_event (event_type),
    INDEX idx_created (created_at)
);

-- Performance metrics tracking
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_date DATE,
    total_games_analyzed INT,
    total_players_analyzed INT,
    cheats_detected INT,
    false_positives INT,
    true_positives INT,
    false_negatives INT,
    true_negatives INT,
    avg_analysis_time_ms FLOAT,
    system_accuracy FLOAT,
    system_precision FLOAT,
    system_recall FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_date (metric_date),
    INDEX idx_date (metric_date)
);

-- Create views for common queries
CREATE OR REPLACE VIEW suspicious_players AS
SELECT 
    p.player_id,
    p.username,
    p.platform,
    p.rating,
    p.trust_score,
    COUNT(DISTINCT g.game_id) as flagged_games,
    AVG(g.cheat_score) as avg_cheat_score,
    MAX(g.cheat_score) as max_cheat_score
FROM players p
JOIN games g ON (p.player_id = g.white_player_id OR p.player_id = g.black_player_id)
WHERE g.is_flagged = TRUE
GROUP BY p.player_id
HAVING flagged_games > 3
ORDER BY avg_cheat_score DESC;

CREATE OR REPLACE VIEW player_consistency AS
SELECT 
    pf.player_id,
    p.username,
    p.rating,
    AVG(pf.accuracy_consistency) as avg_consistency,
    STDDEV(pf.accuracy_consistency) as consistency_variance,
    AVG(pf.session_entropy) as avg_entropy,
    AVG(pf.sandbagging_score) as avg_sandbagging
FROM player_features pf
JOIN players p ON pf.player_id = p.player_id
GROUP BY pf.player_id
ORDER BY consistency_variance DESC;

-- Stored procedures for common operations
DELIMITER //

CREATE PROCEDURE UpdatePlayerTrustScore(IN p_player_id VARCHAR(64))
BEGIN
    DECLARE trust_score FLOAT;
    DECLARE total_games INT;
    DECLARE flagged_ratio FLOAT;
    
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN is_flagged = TRUE THEN 1 ELSE 0 END) / COUNT(*) as flagged_ratio
    INTO total_games, flagged_ratio
    FROM games
    WHERE white_player_id = p_player_id OR black_player_id = p_player_id;
    
    -- Calculate trust score based on flagged ratio and other factors
    SET trust_score = GREATEST(0, LEAST(1, 1 - (flagged_ratio * 2)));
    
    UPDATE players 
    SET trust_score = trust_score,
        total_games = total_games
    WHERE player_id = p_player_id;
END //

CREATE PROCEDURE AnalyzePlayerSession(
    IN p_player_id VARCHAR(64),
    IN p_session_id VARCHAR(64)
)
BEGIN
    DECLARE session_entropy FLOAT;
    DECLARE opening_adherence FLOAT;
    DECLARE avg_accuracy FLOAT;
    
    -- Calculate session metrics
    SELECT 
        -SUM(accuracy * LOG(accuracy + 0.001)) as entropy,
        AVG(CASE WHEN is_book_move THEN 1 ELSE 0 END) as book_adherence,
        AVG(move_accuracy) as avg_acc
    INTO session_entropy, opening_adherence, avg_accuracy
    FROM move_analysis ma
    JOIN games g ON ma.game_id = g.game_id
    WHERE (g.white_player_id = p_player_id OR g.black_player_id = p_player_id)
    AND DATE(ma.created_at) = CURDATE();
    
    -- Insert or update player features
    INSERT INTO player_features (
        player_id, session_id, session_entropy, 
        opening_book_adherence, timestamp
    ) VALUES (
        p_player_id, p_session_id, session_entropy, 
        opening_adherence, NOW()
    );
END //

DELIMITER ;

-- Indexes for performance optimization
ALTER TABLE move_analysis ADD INDEX idx_player_accuracy 
    (game_id, move_accuracy, centipawn_loss);
    
ALTER TABLE player_features ADD INDEX idx_feature_analysis 
    (player_id, session_entropy, accuracy_consistency);
    
ALTER TABLE games ADD INDEX idx_cheat_detection 
    (cheat_score, is_flagged, analysis_completed);

-- Initial data for cohort thresholds
INSERT INTO cohort_thresholds (rating_min, rating_max, time_control_category, 
    accuracy_threshold, consistency_threshold, think_time_threshold, 
    entropy_threshold, sandbagging_threshold, sample_size) VALUES
(0, 1200, 'bullet', 0.65, 0.15, 1.5, 2.5, 0.3, 1000),
(1200, 1600, 'bullet', 0.70, 0.12, 1.2, 2.3, 0.25, 1000),
(1600, 2000, 'bullet', 0.75, 0.10, 1.0, 2.0, 0.20, 1000),
(2000, 2400, 'bullet', 0.80, 0.08, 0.8, 1.8, 0.15, 1000),
(2400, 3000, 'bullet', 0.85, 0.06, 0.6, 1.5, 0.10, 1000),
(0, 1200, 'blitz', 0.60, 0.18, 3.0, 2.8, 0.35, 1000),
(1200, 1600, 'blitz', 0.65, 0.15, 2.5, 2.5, 0.30, 1000),
(1600, 2000, 'blitz', 0.70, 0.12, 2.0, 2.2, 0.25, 1000),
(2000, 2400, 'blitz', 0.75, 0.10, 1.5, 2.0, 0.20, 1000),
(2400, 3000, 'blitz', 0.80, 0.08, 1.2, 1.7, 0.15, 1000),
(0, 1200, 'rapid', 0.55, 0.20, 10.0, 3.0, 0.40, 1000),
(1200, 1600, 'rapid', 0.60, 0.17, 8.0, 2.7, 0.35, 1000),
(1600, 2000, 'rapid', 0.65, 0.14, 6.0, 2.4, 0.30, 1000),
(2000, 2400, 'rapid', 0.70, 0.11, 5.0, 2.1, 0.25, 1000),
(2400, 3000, 'rapid', 0.75, 0.09, 4.0, 1.8, 0.20, 1000);
