/**
 * Chess Cheat Detection System - Frontend Application
 */

// Global variables
let currentAnalysis = null;
let activeWarnings = [];
let playerStats = {};
let analysisHistory = [];

// Utility functions
const utils = {
    /**
     * Show notification to user
     */
    showNotification: function(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                    <p class="mb-0">${message}</p>
                </div>
                <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        document.body.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                notification.remove();
            }, duration);
        }
    },
    
    /**
     * Format timestamp
     */
    formatTime: function(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString();
    },
    
    /**
     * Calculate percentage
     */
    percentage: function(value, max = 100) {
        return Math.round((value / max) * 100);
    },
    
    /**
     * Get severity color
     */
    getSeverityColor: function(severity) {
        const colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545'
        };
        return colors[severity] || '#6c757d';
    },
    
    /**
     * Debounce function
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// API functions
const api = {
    /**
     * Analyze game
     */
    analyzeGame: async function(pgn, playerId = null) {
        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ pgn, player_id: playerId })
            });
            
            if (!response.ok) {
                throw new Error('Analysis failed');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Analysis error:', error);
            utils.showNotification('Failed to analyze game', 'error');
            return null;
        }
    },
    
    /**
     * Get player profile
     */
    getPlayerProfile: async function(playerId) {
        try {
            const response = await fetch(`/api/player/${playerId}`);
            
            if (!response.ok) {
                throw new Error('Player not found');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Profile error:', error);
            return null;
        }
    },
    
    /**
     * Scrape games
     */
    scrapeGames: async function(username, platform = 'chess.com', maxGames = 10) {
        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, platform, max_games: maxGames })
            });
            
            if (!response.ok) {
                throw new Error('Scraping failed');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Scraping error:', error);
            utils.showNotification('Failed to start scraping', 'error');
            return null;
        }
    },
    
    /**
     * Get statistics
     */
    getStatistics: async function() {
        try {
            const response = await fetch('/api/stats');
            
            if (!response.ok) {
                throw new Error('Failed to get statistics');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Statistics error:', error);
            return null;
        }
    },
    
    /**
     * Get warnings
     */
    getWarnings: async function() {
        try {
            const response = await fetch('/api/warnings');
            
            if (!response.ok) {
                throw new Error('Failed to get warnings');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Warnings error:', error);
            return [];
        }
    }
};

// UI update functions
const ui = {
    /**
     * Update analysis metrics
     */
    updateMetrics: function(data) {
        if (data.accuracy !== undefined) {
            $('#accuracy-score').text(Math.round(data.accuracy * 100) + '%');
        }
        if (data.anomaly_score !== undefined) {
            $('#anomaly-score').text(data.anomaly_score.toFixed(2));
        }
        if (data.consistency !== undefined) {
            $('#consistency-score').text(Math.round(data.consistency * 100) + '%');
        }
        if (data.trust_score !== undefined) {
            $('#trust-score').text(Math.round(data.trust_score * 100) + '%');
        }
    },
    
    /**
     * Update player profile display
     */
    updatePlayerProfile: function(profile) {
        $('#player-name').text(profile.username || 'Unknown');
        $('#player-rating').text(profile.rating || '-');
        $('#player-platform').text(profile.platform || '-');
        
        // Update trust metrics
        const trustPercent = Math.round(profile.trust_score * 100);
        $('#trust-bar').css('width', trustPercent + '%').text(trustPercent + '%');
        
        if (profile.consistency) {
            const consistencyPercent = Math.round(profile.consistency * 100);
            $('#consistency-bar').css('width', consistencyPercent + '%').text(consistencyPercent + '%');
        }
        
        if (profile.accuracy_stability) {
            const stabilityPercent = Math.round(profile.accuracy_stability * 100);
            $('#stability-bar').css('width', stabilityPercent + '%').text(stabilityPercent + '%');
        }
    },
    
    /**
     * Add warning to display
     */
    addWarning: function(warning) {
        const warningHtml = `
            <div class="alert alert-${warning.severity === 'critical' ? 'danger' : 'warning'} alert-dismissible">
                <small>${utils.formatTime(warning.timestamp || new Date())}</small><br>
                <strong>${warning.type}</strong>: ${warning.message || warning.details}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('#warning-list').html(warningHtml);
        activeWarnings.push(warning);
    },
    
    /**
     * Update detection history
     */
    updateDetectionHistory: function(detection) {
        const historyItem = `
            <div class="detection-item mb-2">
                <small class="text-muted">${utils.formatTime(detection.timestamp)}</small>
                <div>
                    <strong>${detection.player}</strong> - 
                    <span class="badge bg-${detection.flagged ? 'danger' : 'success'}">
                        ${detection.flagged ? 'Flagged' : 'Clean'}
                    </span>
                </div>
            </div>
        `;
        
        $('#detection-history').prepend(historyItem);
        
        // Keep only last 10 items
        $('#detection-history .detection-item').slice(10).remove();
    },
    
    /**
     * Update admin dashboard
     */
    updateDashboard: async function() {
        const stats = await api.getStatistics();
        
        if (stats) {
            $('#total-players').text(stats.total_players.toLocaleString());
            $('#total-games').text(stats.total_games.toLocaleString());
            $('#active-warnings').text(stats.active_warnings);
            $('#banned-players').text(stats.banned_players);
        }
    },
    
    /**
     * Update flags table
     */
    updateFlagsTable: function(flags) {
        const tbody = $('#flags-table');
        tbody.empty();
        
        if (!flags || flags.length === 0) {
            tbody.append('<tr><td colspan="7" class="text-center">No flags found</td></tr>');
            return;
        }
        
        flags.forEach(flag => {
            const row = `
                <tr>
                    <td>${utils.formatTime(flag.timestamp)}</td>
                    <td>${flag.player_name}</td>
                    <td>${flag.type}</td>
                    <td>
                        <span class="badge" style="background-color: ${utils.getSeverityColor(flag.severity)}">
                            ${flag.severity}
                        </span>
                    </td>
                    <td>${Math.round(flag.confidence * 100)}%</td>
                    <td>
                        <span class="badge bg-${flag.status === 'active' ? 'warning' : 'secondary'}">
                            ${flag.status}
                        </span>
                    </td>
                    <td class="action-buttons">
                        <button class="btn btn-sm btn-primary" onclick="reviewFlag('${flag.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-success" onclick="resolveFlag('${flag.id}')">
                            <i class="fas fa-check"></i>
                        </button>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    },
    
    /**
     * Update recent games table
     */
    updateRecentGames: function(games) {
        const tbody = $('#recent-games-table');
        tbody.empty();
        
        if (!games || games.length === 0) {
            tbody.append('<tr><td colspan="6" class="text-center">No games loaded</td></tr>');
            return;
        }
        
        games.forEach(game => {
            const row = `
                <tr>
                    <td>${utils.formatTime(game.date)}</td>
                    <td>${game.opponent}</td>
                    <td>
                        <span class="badge bg-${game.result === 'win' ? 'success' : game.result === 'loss' ? 'danger' : 'secondary'}">
                            ${game.result}
                        </span>
                    </td>
                    <td>${Math.round(game.accuracy * 100)}%</td>
                    <td>
                        ${game.flagged ? '<span class="badge bg-danger">Flagged</span>' : '-'}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="analyzeGame('${game.id}')">
                            Analyze
                        </button>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    }
};

// Chart update functions
const charts = {
    /**
     * Update accuracy trend chart
     */
    updateAccuracyChart: function(data) {
        if (!window.accuracyChart) return;
        
        window.accuracyChart.data.labels = data.labels || [];
        window.accuracyChart.data.datasets[0].data = data.values || [];
        window.accuracyChart.update();
    },
    
    /**
     * Update performance chart
     */
    updatePerformanceChart: function(data) {
        if (!window.performanceChart) return;
        
        window.performanceChart.data.labels = data.labels || [];
        window.performanceChart.data.datasets[0].data = data.values || [];
        window.performanceChart.update();
    },
    
    /**
     * Add real-time data point
     */
    addRealtimePoint: function(chart, label, value) {
        if (!chart) return;
        
        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(value);
        
        // Keep only last 20 points
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        
        chart.update();
    }
};

// Global functions for onclick handlers
window.reviewFlag = function(flagId) {
    console.log('Reviewing flag:', flagId);
    // Implementation for reviewing flag
    utils.showNotification(`Reviewing flag ${flagId}`, 'info');
};

window.resolveFlag = function(flagId) {
    console.log('Resolving flag:', flagId);
    // Implementation for resolving flag
    utils.showNotification(`Flag ${flagId} resolved`, 'success');
};

window.analyzeGame = function(gameId) {
    console.log('Analyzing game:', gameId);
    // Implementation for analyzing game
    utils.showNotification('Starting game analysis...', 'info');
};

// Real-time updates
const realtime = {
    /**
     * Start periodic updates
     */
    startUpdates: function() {
        // Update dashboard every 30 seconds
        setInterval(() => {
            ui.updateDashboard();
        }, 30000);
        
        // Request stats updates every 10 seconds
        setInterval(() => {
            if (window.socket && window.socket.connected) {
                window.socket.emit('request_update', { type: 'stats' });
            }
        }, 10000);
    },
    
    /**
     * Handle incoming WebSocket messages
     */
    setupSocketHandlers: function() {
        if (!window.socket) return;
        
        // Handle player found
        window.socket.on('player_found', (data) => {
            ui.updatePlayerProfile(data);
            utils.showNotification('Player profile loaded', 'success');
        });
        
        // Handle player not found
        window.socket.on('player_not_found', (data) => {
            utils.showNotification(`Player ${data.username} not found`, 'warning');
        });
        
        // Handle scraping complete
        window.socket.on('scraping_complete', (data) => {
            utils.showNotification(`Scraped ${data.games_count} games for ${data.username}`, 'success');
        });
        
        // Handle scraping error
        window.socket.on('scraping_error', (data) => {
            utils.showNotification(`Scraping failed: ${data.error}`, 'error');
        });
        
        // Handle stats update
        window.socket.on('stats_update', (data) => {
            console.log('Stats update:', data);
            // Update UI with new stats
        });
        
        // Handle warnings update
        window.socket.on('warnings_update', (data) => {
            ui.updateFlagsTable(data);
        });
        
        // Handle analysis started
        window.socket.on('analysis_started', (data) => {
            utils.showNotification(data.message, 'info');
            $('.loader').show();
        });
        
        // Handle analysis error
        window.socket.on('analysis_error', (data) => {
            utils.showNotification(`Analysis error: ${data.error}`, 'error');
            $('.loader').hide();
        });
    }
};

// Initialize on document ready
$(document).ready(function() {
    // Initialize UI
    ui.updateDashboard();
    
    // Setup real-time updates
    realtime.startUpdates();
    realtime.setupSocketHandlers();
    
    // Setup search with debouncing
    const debouncedSearch = utils.debounce(function(username) {
        if (username && window.socket) {
            window.socket.emit('search_player', { username });
        }
    }, 500);
    
    $('#player-search').on('input', function() {
        debouncedSearch($(this).val());
    });
    
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Dark mode toggle
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        $('body').addClass('dark-mode');
    }
    
    // Load initial warnings
    api.getWarnings().then(warnings => {
        if (warnings && warnings.length > 0) {
            warnings.forEach(warning => ui.addWarning(warning));
        }
    });
    
    console.log('Chess Cheat Detection System initialized');
});

// Export for external use
window.chessDetection = {
    api,
    ui,
    charts,
    utils,
    realtime
};
