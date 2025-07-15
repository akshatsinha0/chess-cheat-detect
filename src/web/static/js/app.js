let board = null;
let game = new Chess();
let socket = null;
let capturedFEN = null;
let moveHistoryPairs = [];
let pgnMoves = [];
let currentMoveIndex = 0;
let pgnBaseFen = null;
let lastMove = null; // Track the last move for arrow indicator
$(document).ready(function() {
    $.post('/api/new_game', function(response) {
        if (response.status === 'success') {
            board?.position(response.fen);
            game.load(response.fen);
            moveHistoryPairs = [];
            renderMoveHistoryTable();
            updateStatus();
        }
        initBoard();
        initSocket();
        updateStatus();
        initEnhancements();
    });
    // Button animation for .animated-btn
    $('.animated-btn').each(function() {
        var btn = $(this);
        var text = btn.find('.btn-text');
        btn.on('mouseleave', function() {
            text.addClass('reverse-anim');
            text.one('animationend', function() {
                text.removeClass('reverse-anim');
            });
        });
    });
});

// Initialize UI Enhancements
function initEnhancements() {
    initRippleEffects();
    initParticleSystem();
    initTooltips();
    initEnhancedCards();
    initProgressBars();
}

// Ripple Effect System
function initRippleEffects() {
    // Add ripple effect to all buttons
    $('.btn, .enhanced-btn').each(function() {
        if (!$(this).hasClass('ripple-container')) {
            $(this).addClass('ripple-container');
        }
    });
    
    // Handle click events for ripple effect
    $(document).on('click', '.ripple-container', function(e) {
        createRipple(e, this);
    });
}

function createRipple(event, element) {
    const $element = $(element);
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    const $ripple = $('<span class="ripple"></span>');
    $ripple.css({
        width: size + 'px',
        height: size + 'px',
        left: x + 'px',
        top: y + 'px'
    });
    
    $element.append($ripple);

    setTimeout(() => {
        $ripple.remove();
    }, 600);
}


function initParticleSystem() {
 
    if ($('.particle-container').length === 0) {
        const particleContainer = $('<div class="particle-container"></div>');
        
    
        for (let i = 0; i < 10; i++) {
            const particle = $('<div class="particle"></div>');
            particle.css({
                left: Math.random() * 100 + '%',
                top: Math.random() * 100 + '%',
                animationDelay: Math.random() * 20 + 's',
                animationDuration: (15 + Math.random() * 10) + 's'
            });
            particleContainer.append(particle);
        }
        
        $('body').append(particleContainer);
    }
    

    if ($('.ambient-glow').length === 0) {
        $('body').append('<div class="ambient-glow"></div>');
    }
}


function initTooltips() {
  
    $('[data-tooltip]').each(function() {
        const $element = $(this);
        const tooltipText = $element.data('tooltip');
        
        $element.on('mouseenter', function(e) {
            showTooltip(e, tooltipText);
        });
        
        $element.on('mouseleave', function() {
            hideTooltip();
        });
    });
}

function showTooltip(event, text) {
    const $tooltip = $('<div class="enhanced-tooltip">' + text + '</div>');
    $('body').append($tooltip);
    
    const rect = event.target.getBoundingClientRect();
    const tooltipRect = $tooltip[0].getBoundingClientRect();
    
    let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
    let top = rect.top - tooltipRect.height - 10;

    if (left < 10) left = 10;
    if (left + tooltipRect.width > window.innerWidth - 10) {
        left = window.innerWidth - tooltipRect.width - 10;
    }
    if (top < 10) {
        top = rect.bottom + 10;
    }
    
    $tooltip.css({
        left: left + 'px',
        top: top + 'px'
    });

    setTimeout(() => {
        $tooltip.addClass('visible');
    }, 10);
}

function hideTooltip() {
    $('.enhanced-tooltip').removeClass('visible');
    setTimeout(() => {
        $('.enhanced-tooltip').remove();
    }, 300);
}

function initEnhancedCards() {
    $('.card').each(function() {
        if (!$(this).hasClass('enhanced-card')) {
            $(this).addClass('enhanced-card hover-lift');
        }
    });
}

function initProgressBars() {
    $('.progress-bar').each(function() {
        if (!$(this).hasClass('enhanced-progress-bar')) {
            $(this).addClass('enhanced-progress-bar');
        }
    });
}


function createParticleBurst(x, y, color = '#ffb86c') {
    const $burst = $('<div class="particle-burst"></div>');
    $burst.css({
        left: x + 'px',
        top: y + 'px'
    });
    
  
    for (let i = 0; i < 8; i++) {
        const $particle = $('<div class="burst-particle"></div>');
        $particle.css({
            background: color,
            transform: `rotate(${i * 45}deg) translateX(30px)`
        });
        $burst.append($particle);
    }
    
    $('body').append($burst);
    

    setTimeout(() => {
        $burst.remove();
    }, 800);
}

function showEnhancedAlert(message, type = 'info', duration = 5000) {
    const alertTypes = {
        'info': 'enhanced-alert',
        'success': 'enhanced-alert success',
        'danger': 'enhanced-alert danger',
        'warning': 'enhanced-alert warning'
    };
    
    const alertHtml = `
        <div class="${alertTypes[type]} animate-slide-in-right" role="alert">
            <div class="enhanced-alert-content">
                <div class="enhanced-alert-icon">${getAlertIcon(type)}</div>
                <div class="enhanced-alert-text">${message}</div>
                <button type="button" class="btn-close" onclick="$(this).closest('.enhanced-alert').remove();">&times;</button>
            </div>
        </div>
    `;
    
    const $alert = $(alertHtml);
    $('#alertContainer').append($alert);
    

    setTimeout(() => {
        $alert.addClass('animate-fade-out');
        setTimeout(() => {
            $alert.remove();
        }, 300);
    }, duration);
}

function getAlertIcon(type) {
    const icons = {
        'info': 'ℹ',
        'success': '✓',
        'danger': '⚠',
        'warning': '!'
    };
    return icons[type] || icons['info'];
}

function createCircularGauge(container, value, max = 100, label = '') {
    const percentage = (value / max) * 100;
    const rotation = (percentage / 100) * 180 - 90; // -90 to 90 degrees
    
    const gaugeHtml = `
        <div class="circular-gauge">
            <div class="circular-gauge-inner">
                <div class="circular-gauge-needle" style="transform: rotate(${rotation}deg);"></div>
                <div class="circular-gauge-value">${Math.round(percentage)}%</div>
                <div class="circular-gauge-label">${label}</div>
            </div>
        </div>
    `;
    
    $(container).html(gaugeHtml);
}


function setLoadingState(element, loading = true) {
    const $element = $(element);
    if (loading) {
        $element.addClass('loading-state');
        if (!$element.find('.enhanced-spinner').length) {
            $element.append('<div class="enhanced-spinner"></div>');
        }
    } else {
        $element.removeClass('loading-state');
        $element.find('.enhanced-spinner').remove();
    }
}
function initBoard() {
    const config = {
        draggable: true,
        position: 'start',
        pieceTheme: function(piece) {
            // piece is like 'wK', 'bQ', etc.
            return '/static/img/' + piece + '.svg';
        },
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    };
    board = Chessboard('board', config);
    

    setTimeout(() => {
        initChessPieceEnhancements();
    }, 500);
}

function initChessPieceEnhancements() {

    $('#board .square-55d63').each(function() {
        const $square = $(this);
        
        $square.on('mouseenter', function() {
            const $piece = $square.find('img');
            if ($piece.length > 0) {
                $piece.addClass('chess-piece-hover');
                showPossibleMoves($square.data('square'));
            }
        });
        
        $square.on('mouseleave', function() {
            const $piece = $square.find('img');
            $piece.removeClass('chess-piece-hover');
            hidePossibleMoves();
        });
    });
    

    $('#board img').each(function() {
        $(this).addClass('chess-piece-enhanced');
    });
}

function showPossibleMoves(square) {
    if (!square || game.game_over()) return;
    
    try {
        const moves = game.moves({
            square: square,
            verbose: true
        });
        
        moves.forEach(move => {
            const $targetSquare = $(`[data-square="${move.to}"]`);
            if ($targetSquare.length > 0) {
                $targetSquare.addClass('possible-move-highlight');
                
                
                const $indicator = $('<div class="move-indicator"></div>');
                $targetSquare.append($indicator);
                
                setTimeout(() => {
                    $indicator.addClass('visible');
                }, 50);
            }
        });
    } catch (e) {
      
    }
}

function hidePossibleMoves() {
    $('.possible-move-highlight').removeClass('possible-move-highlight');
    $('.move-indicator').remove();
}
function initSocket() {
    socket = io();
    socket.on('connected', function(data) {
        console.log(data.message);
    });
    socket.on('move_made', function(data) {
        board.position(data.fen);
        updateCurrentAnalysis(data.analysis);
        addMoveToHistory(data.move, data.analysis);
        updateLastMoveDisplay({from:data.move.substring(0,2),to:data.move.substring(2,4)});
    });
    socket.on('analysis_result', function(data) {
        updateCurrentAnalysis(data);
    });
}
function onDragStart(source, piece, position, orientation) {
    if (game.game_over()) return false;
    if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
        (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
        return false;
    }
}
// --- Sound Effects ---
const sounds = {
    move: new Audio('http://images.chesscomfiles.com/chess-themes/sounds/_MP3_/default/move-self.mp3'),
    castle: new Audio('https://images.chesscomfiles.com/chess-themes/sounds/_MP3_/default/castle.mp3'),
    capture: new Audio('http://images.chesscomfiles.com/chess-themes/sounds/_MP3_/default/capture.mp3'),
    check: new Audio('https://images.chesscomfiles.com/chess-themes/sounds/_MP3_/default/move-check.mp3'),
    promote: new Audio('https://images.chesscomfiles.com/chess-themes/sounds/_MP3_/default/promote.mp3')
};
function playSound(type) {
    if (sounds[type]) {
        sounds[type].currentTime = 0;
        sounds[type].play();
    }
}

function onDrop(source, target) {
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q'
    });
    if (move === null) return 'snapback';

    let soundType = 'move';
    if (move.flags.includes('c')) soundType = 'capture';
    if (move.flags.includes('k') || move.flags.includes('q')) soundType = 'castle';
    if (move.flags.includes('p')) soundType = 'promote';

    setTimeout(() => {
        if (game.in_check()) {
            playSound('check');
        } else {
            playSound(soundType);
        }
    }, 10);
    $.ajax({
        url: '/api/make_move',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            move: move.from + move.to + (move.promotion || '')
        }),
        success: function(response) {
            if (response.status === 'success') {
                updateStatus();
                updateCurrentAnalysis(response.analysis);
                addMoveToHistory(move.san, response.analysis);
                syncMoveHistoryFromGame();
                // Show last move arrow
                updateLastMoveDisplay({ from: source, to: target });
            }
        },
        error: function(error) {
            $.post('/api/new_game', function(response) {
                board.position(response.fen);
                game.load(response.fen);
                updateStatus();
            });
            showAlert('Error making move: ' + error.responseJSON.message, 'danger');
        }
    });
}
function onSnapEnd() {
    board.position(game.fen());
}
function updateStatus() {
    let status = '';
    const moveColor = game.turn() === 'b' ? 'Black' : 'White';
    if (game.in_checkmate()) {
        status = 'Game over, ' + moveColor + ' is in checkmate.';
    }
    else if (game.in_draw()) {
        status = 'Game over, drawn position';
    }
    else {
        status = moveColor + ' to move';
        if (game.in_check()) {
            status += ', ' + moveColor + ' is in check';
        }
    }
    $('#fenInput').val(game.fen());
}
function updateCurrentAnalysis(analysis) {
    const evalValue = analysis.evaluation?.value || 0;
    const evalType = analysis.evaluation?.type || 'cp';
    const suspicionPercent = (analysis.suspicion_score * 100).toFixed(1);
    let evalDisplay = '';
    if (evalType === 'mate') {
        evalDisplay = `Mate in ${Math.abs(evalValue)}`;
    } else {
        evalDisplay = (evalValue / 100).toFixed(2);
    }
    let suspicionClass = 'success';
    if (analysis.suspicion_score > 0.7) {
        suspicionClass = 'danger';
    } else if (analysis.suspicion_score > 0.5) {
        suspicionClass = 'warning';
    }
    
  
    const html = `
        <div class="enhanced-analysis-container">
            <div class="analysis-card animate-fade-in animate-stagger-1">
                <div class="analysis-header">
                    <h6><i class="analysis-icon">♔</i> Best Move</h6>
                </div>
                <div class="analysis-value">${analysis.best_move || 'N/A'}</div>
            </div>
            <div class="analysis-card animate-fade-in animate-stagger-2">
                <div class="analysis-header">
                    <h6><i class="analysis-icon">⚖</i> Evaluation</h6>
                </div>
                <div class="analysis-value">${evalDisplay}</div>
            </div>
            <div class="analysis-card animate-fade-in animate-stagger-3">
                <div class="analysis-header">
                    <h6><i class="analysis-icon">🔍</i> Suspicion Level</h6>
                </div>
                <div class="enhanced-progress">
                    <div class="enhanced-progress-bar shimmer bg-${suspicionClass}" 
                         style="width: ${suspicionPercent}%">
                        <span class="progress-text">${suspicionPercent}%</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    $('#currentAnalysis').html(html);
    

    if (analysis.suspicion_score > 0.7) {
        showEnhancedAlert('High cheating probability detected!', 'danger');
        createParticleBurst(window.innerWidth - 100, 100, '#ff5555');
    }
    

    setTimeout(() => {
        if ($('.analysis-card').length > 0) {
            createCircularGauge('.analysis-card:last-child .enhanced-progress', suspicionPercent, 100, 'Suspicion');
        }
    }, 500);
}
function addMoveToHistory(san, analysis) {
    const isWhite = (game.history().length % 2) === 1;
    if (isWhite) {
        moveHistoryPairs.push({
            white: san,
            black: '',
            whiteAnalysis: analysis,
            blackAnalysis: null
        });
    } else {
        if (moveHistoryPairs.length === 0) {
            moveHistoryPairs.push({
                white: '',
                black: san,
                whiteAnalysis: null,
                blackAnalysis: analysis
            });
        } else {
            moveHistoryPairs[moveHistoryPairs.length - 1].black = san;
            moveHistoryPairs[moveHistoryPairs.length - 1].blackAnalysis = analysis;
        }
    }
    renderMoveHistoryTable();
}
function renderMoveHistoryTable() {
    let html = '';
    for (let i = 0; i < moveHistoryPairs.length; i++) {
        const row = moveHistoryPairs[i];
        html += `<tr>
            <td>${i + 1}</td>
            <td>${row.white || ''}</td>
            <td>${row.black || ''}</td>
            <td>${row.whiteAnalysis ? (row.whiteAnalysis.best_move || '') : ''}</td>
            <td>${row.blackAnalysis ? (row.blackAnalysis.best_move || '') : ''}</td>
            <td>${row.whiteAnalysis ? formatEval(row.whiteAnalysis.evaluation) : ''}</td>
            <td>${row.blackAnalysis ? formatEval(row.blackAnalysis.evaluation) : ''}</td>
            <td>${row.whiteAnalysis ? formatSuspicion(row.whiteAnalysis.suspicion_score) : ''}</td>
            <td>${row.blackAnalysis ? formatSuspicion(row.blackAnalysis.suspicion_score) : ''}</td>
        </tr>`;
    }
    $('#moveHistory').html(html);
}
function formatEval(evaluation) {
    if (!evaluation) return '';
    if (evaluation.type === 'mate') {
        return `M${Math.abs(evaluation.value)}`;
    } else {
        return (evaluation.value / 100).toFixed(2);
    }
}
function formatSuspicion(score) {
    if (typeof score !== 'number') return '';
    return (score * 100).toFixed(1) + '%';
}
function newGame() {
    $.post('/api/new_game', function(response) {
        if (response.status === 'success') {
            board.position(response.fen);
            game.load(response.fen);
            moveHistoryPairs = [];
            renderMoveHistoryTable();
            updateStatus();
            syncMoveHistoryFromGame();
            // Hide last move arrow for new game
            hideLastMoveArrow();
        }
    });
}
function detectCheat() {
    const fen = game.fen();
    $.post('/api/analyze_fen', { fen: fen }).done(function(response) {
        if (response.status === 'success') {
            updateCurrentAnalysis(response);
            showAlert(`Analysis complete. Suspicion score: ${(response.suspicion_score * 100).toFixed(1)}%`, 'info');
        }
    }).fail(function(error) {
        showAlert('Error analyzing position: ' + error.responseJSON.message, 'danger');
    });
}
function analyzeFEN() {
    const fen = $('#fenInput').val();
    if (!fen) {
        showAlert('Please enter a FEN string', 'warning');
        return;
    }
    $.post('/api/analyze_fen', { fen: fen }).done(function(response) {
        if (response.status === 'success') {
            game.load(fen);
            board.position(fen);
            updateStatus();
            updateCurrentAnalysis(response);
            showAlert('FEN position analyzed successfully', 'success');
        }
    }).fail(function(error) {
        showAlert('Error analyzing FEN: ' + error.responseJSON.message, 'danger');
    });
}
function captureFromCamera() {
    const modal = new bootstrap.Modal(document.getElementById('cameraModal'));
    modal.show();
    $.post('/api/capture_board').done(function(response) {
        if (response.status === 'success') {
            $('#cameraLoading').hide();
            $('#capturedImage').attr('src', response.image).show();
            capturedFEN = response.fen;
        }
    }).fail(function(error) {
        $('#cameraLoading').hide();
        showAlert('Error capturing board: ' + error.responseJSON.message, 'danger');
        modal.hide();
    });
}
function useCapturedPosition() {
    if (capturedFEN) {
        game.load(capturedFEN);
        board.position(capturedFEN);
        updateStatus();
        const modal = bootstrap.Modal.getInstance(document.getElementById('cameraModal'));
        modal.hide();
        showAlert('Board position loaded from camera', 'success');
    }
}
function showImportModal() {
    const modal = new bootstrap.Modal(document.getElementById('importModal'));
    modal.show();
}
function importPGN() {
    const pgnText = $('#pgnText').val();
    if (!pgnText) {
        showAlert('Please paste a PGN game', 'warning');
        return;
    }
    $.post('/api/import_pgn', { pgn: pgnText }).done(function(response) {
        if (response.status === 'success') {
            const modal = bootstrap.Modal.getInstance(document.getElementById('importModal'));
            modal.hide();
            const summary = response.summary;
            const gameInfo = response.game_info;
            let alertMessage = `
                <strong>Game Analysis Complete!</strong><br>
                ${gameInfo.white} vs ${gameInfo.black} (${gameInfo.result})<br>
                Total moves: ${summary.total_moves}<br>
                Average suspicion: ${summary.avg_suspicion.toFixed(1)}%<br>
                Suspicious moves: ${summary.suspicious_moves}
            `;
            showAlert(alertMessage, summary.avg_suspicion > 50 ? 'warning' : 'success', 10000);
            $('#moveHistory').empty();
            response.analysis.forEach((analysis, index) => {
                addMoveToHistory(analysis.move, analysis);
            });
        }
    }).fail(function(error) {
        showAlert('Error importing PGN: ' + error.responseJSON.message, 'danger');
    });
}
function applyFEN() {
    const fen = $('#fenInput').val().trim();
    if (fen) {
        const loaded = game.load(fen);
        if (loaded) {
            board.position(fen);
            moveHistoryPairs = [];
            renderMoveHistoryTable();
            updateStatus();
            showAlert('FEN applied to board.', 'success');
            updateLastMoveDisplay(null);
        } else {
            showAlert('Invalid FEN string.', 'danger');
        }
    }
}
function applyPGN() {
    const pgn = $('#pgnInput').val().trim();
    if (pgn) {
        const loaded = game.load_pgn(pgn);
        if (loaded) {
            pgnMoves = game.history({ verbose: true });
            currentMoveIndex = pgnMoves.length;
            pgnBaseFen = new Chess().fen();
            board.position(game.fen());
            updateMoveListForPGN();
            updateStatus();
            showAlert('PGN applied to board.', 'success');
            if (pgnMoves.length > 0) {
                const move = pgnMoves[pgnMoves.length - 1];
                updateLastMoveDisplay({ from: move.from, to: move.to });
            } else {
                updateLastMoveDisplay(null);
            }
        } else {
            showAlert('Invalid PGN string.', 'danger');
        }
    }
}
function updateMoveListForPGN() {
    moveHistoryPairs = [];
    let tempGame = new Chess(pgnBaseFen);
    for (let i = 0; i < currentMoveIndex; i++) {
        const move = pgnMoves[i];
        const san = move.san;
        const isWhite = (i % 2) === 0;
        if (isWhite) {
            moveHistoryPairs.push({ white: san, black: '', whiteAnalysis: null, blackAnalysis: null });
        } else {
            moveHistoryPairs[moveHistoryPairs.length - 1].black = san;
        }
        tempGame.move(move);
    }
    renderMoveHistoryTable();
}
// --- Navigation Sounds and Functions ---
function prevMove() {
    if (currentMoveIndex > 0) {
        currentMoveIndex--;
        let tempGame = new Chess(pgnBaseFen);
        for (let i = 0; i < currentMoveIndex; i++) {
            tempGame.move(pgnMoves[i]);
        }
        board.position(tempGame.fen());
        game.load(tempGame.fen());
        updateMoveListForPGN();
        updateStatus();
        playSound('move');
        if (pgnMoves.length > 0 && currentMoveIndex > 0) {
            const move = pgnMoves[currentMoveIndex - 1];
            updateLastMoveDisplay({ from: move.from, to: move.to });
        } else {
            updateLastMoveDisplay(null);
        }
    }
}
function nextMove() {
    if (currentMoveIndex < pgnMoves.length) {
        currentMoveIndex++;
        let tempGame = new Chess(pgnBaseFen);
        for (let i = 0; i < currentMoveIndex; i++) {
            tempGame.move(pgnMoves[i]);
        }
        board.position(tempGame.fen());
        game.load(tempGame.fen());
        updateMoveListForPGN();
        updateStatus();
        playSound('move');
        if (pgnMoves.length > 0 && currentMoveIndex > 0) {
            const move = pgnMoves[currentMoveIndex - 1];
            updateLastMoveDisplay({ from: move.from, to: move.to });
        } else {
            updateLastMoveDisplay(null);
        }
    }
}
function goToStart() {
    currentMoveIndex = 0;
    let tempGame = new Chess(pgnBaseFen);
    board.position(tempGame.fen());
    game.load(tempGame.fen());
    updateMoveListForPGN();
    updateStatus();
    playSound('move');
    updateLastMoveDisplay(null);
}
function goToEnd() {
    currentMoveIndex = pgnMoves.length;
    let tempGame = new Chess(pgnBaseFen);
    for (let i = 0; i < currentMoveIndex; i++) {
        tempGame.move(pgnMoves[i]);
    }
    board.position(tempGame.fen());
    game.load(tempGame.fen());
    updateMoveListForPGN();
    updateStatus();
    playSound('move');
    if (pgnMoves.length > 0 && currentMoveIndex > 0) {
        const move = pgnMoves[currentMoveIndex - 1];
        updateLastMoveDisplay({ from: move.from, to: move.to });
    } else {
        updateLastMoveDisplay(null);
    }
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowLeft') {
        prevMove();
        e.preventDefault();
    } else if (e.key === 'ArrowRight') {
        nextMove();
        e.preventDefault();
    }
});
function flipBoard() {
    board.flip();
}
function showAlert(message, type = 'info', duration = 5000) {
    // Use enhanced alert system for better visual effects
    showEnhancedAlert(message, type, duration);
}

// --- Sidebar Logic ---
function openSidebar(title, html) {
    $('#sidebar-title').text(title);
    $('#sidebar-content').html(html);
    $('#sidebar-overlay').addClass('open');
    $('#sidebar').addClass('open');
}
function closeSidebar() {
    $('#sidebar-overlay').removeClass('open');
    $('#sidebar').removeClass('open');
}
$('#sidebar-overlay').on('click', function(e) {
    if (e.target === this) closeSidebar();
});

$(document).ready(function() {
    $('#analyzePgnBtn').off('click').on('click', function() {
        const pgn = $('#analyzePgnInput').val();
        if (!pgn.trim()) {
            showAlert('Please paste a PGN for analysis.', 'warning');
            return;
        }
        openSidebar('PGN Analysis', '<span class="text-info">Analyzing PGN...</span>');
        $.ajax({
            url: '/analyze_pgn',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ pgn }),
            success: function(data) {
                if (data.success) {
                    let html = "<b>Move-by-move analysis:</b><br><table class='table table-sm'><tr><th>#</th><th>Move</th><th>Best Move</th><th>Eval</th><th>CPL</th></tr>";
                    data.analysis.forEach((move, idx) => {
                        html += `<tr>
                            <td>${idx+1}</td>
                            <td>${move.move}</td>
                            <td>${move.best_move}</td>
                            <td>${move.eval}</td>
                            <td>${move.centipawn_loss}</td>
                        </tr>`;
                    });
                    html += "</table>";
                    openSidebar('PGN Analysis', html);
                } else {
                    openSidebar('PGN Analysis', '<span class="text-danger">' + data.error + '</span>');
                }
            },
            error: function(xhr) {
                openSidebar('PGN Analysis', '<span class="text-danger">Error analyzing PGN.</span>');
            }
        });
    });

    $(".btn-primary.animated-btn:contains('Detect Cheat')").off('click').on('click', function() {
        let pgn = $('#analyzePgnInput').val().trim() || $('#pgnInput').val().trim();
        if (!pgn) {
            pgn = game.pgn();
            if (!pgn || pgn.trim().length === 0) {
                showAlert('No moves to analyze for cheat detection.', 'warning');
                return;
            }
        }
        openSidebar('Cheat Detection', '<span class="text-info">Detecting cheat...</span>');
        $.ajax({
            url: '/detect_cheat',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ pgn }),
            success: function(data) {
                if (data.success) {
                    let r = data.cheat_result;
                    let verdict = r.is_suspicious ? "<span class='text-danger fw-bold'>Suspicious Play Detected!</span>" : "<span class='text-success fw-bold'>No Cheating Detected</span>";
                    let html = `
                        <b>Cheat Detection Result:</b><br>
                        ${verdict}<br>
                        <b>Engine Match Ratio:</b> ${(r.match_ratio*100).toFixed(1)}%<br>
                        <b>Average Centipawn Loss:</b> ${r.avg_centipawn_loss.toFixed(1)}<br>
                        <b>Cheat Score:</b> ${r.cheat_score.toFixed(2)}
                    `;
                    openSidebar('Cheat Detection', html);
                } else {
                    openSidebar('Cheat Detection', '<span class="text-danger">' + data.error + '</span>');
                }
            },
            error: function(xhr) {
                openSidebar('Cheat Detection', '<span class="text-danger">Error detecting cheat.</span>');
            }
        });
    });
});

let addedPgnList = [];
function renderAddedPgnBox() {
    const box = $('#addedPgnBox');
    if (addedPgnList.length === 0) {
        box.html('<span class="text-muted">No games added yet.</span>');
        return;
    }
    let html = '<ul class="list-group">';
    addedPgnList.forEach((pgn, idx) => {
        html += `<li class="list-group-item d-flex justify-content-between align-items-center bg-dark text-light">
            <span style="word-break:break-all;">${pgn.replace(/\n/g, ' ')}</span>
            <button class="btn btn-sm btn-danger ms-2" onclick="deletePgn(${idx})" title="Delete"><i class="bi bi-trash"></i></button>
        </li>`;
    });
    html += '</ul>';
    box.html(html);
}
function deletePgn(idx) {
    addedPgnList.splice(idx, 1);
    renderAddedPgnBox();
}
window.deletePgn = deletePgn;

$('#finishGameBtn').on('click', function() {
    const pgn = game.pgn();
    if (pgn && pgn.trim().length > 0) {
        addedPgnList.push(pgn);
        renderAddedPgnBox();
        showAlert('Game added to PGN list.', 'success');
    } else {
        showAlert('No moves to save.', 'warning');
    }
});

$('#newGameBtn').on('click', function() {
    newGame();
    showAlert('New game started.', 'info');
});

$(document).ready(function() {
    renderAddedPgnBox();
});


function syncMoveHistoryFromGame() {
    pgnMoves = game.history({ verbose: true });
    pgnBaseFen = new Chess().fen();
    currentMoveIndex = pgnMoves.length;
}

// Last Move Arrow Functions
function showLastMoveArrow(fromSquare, toSquare) {
    // Remove any existing arrow
    hideLastMoveArrow();
    
    // Get board container and square positions
    const boardContainer = $('#board');
    const fromElement = $(`[data-square="${fromSquare}"]`);
    const toElement = $(`[data-square="${toSquare}"]`);
    
    if (fromElement.length === 0 || toElement.length === 0) return;
    
    // Calculate positions relative to board
    const boardRect = boardContainer[0].getBoundingClientRect();
    const fromRect = fromElement[0].getBoundingClientRect();
    const toRect = toElement[0].getBoundingClientRect();
    
    const fromX = fromRect.left - boardRect.left + fromRect.width / 2;
    const fromY = fromRect.top - boardRect.top + fromRect.height / 2;
    const toX = toRect.left - boardRect.left + toRect.width / 2;
    const toY = toRect.top - boardRect.top + toRect.height / 2;
    
    // Calculate arrow angle and length
    const deltaX = toX - fromX;
    const deltaY = toY - fromY;
    const angle = Math.atan2(deltaY, deltaX) * 180 / Math.PI;
    const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    
    // Create arrow SVG
    const arrowSvg = `
        <svg width="${length + 20}" height="60" style="position: absolute; left: ${fromX - 10}px; top: ${fromY - 30}px; transform: rotate(${angle}deg); transform-origin: 10px 30px;">
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon class="arrow-head" points="0 0, 10 3.5, 0 7" />
                </marker>
            </defs>
            <line class="arrow-glow" x1="10" y1="30" x2="${length}" y2="30" />
            <line class="arrow-line" x1="10" y1="30" x2="${length}" y2="30" marker-end="url(#arrowhead)" />
        </svg>
    `;
    
    // Add arrow to board
    const $arrow = $(`<div class="last-move-arrow">${arrowSvg}</div>`);
    boardContainer.append($arrow);
    
    // Add square highlights
    fromElement.addClass('last-move-from');
    toElement.addClass('last-move-to');
    
    // Animate arrow appearance
    setTimeout(() => {
        $arrow.addClass('visible');
    }, 50);
    
    // Store last move info
    lastMove = { from: fromSquare, to: toSquare };
}

function hideLastMoveArrow() {
    $('.last-move-arrow').removeClass('visible');
    setTimeout(() => {
        $('.last-move-arrow').remove();
    }, 300);
    
    // Remove square highlights
    $('.last-move-from').removeClass('last-move-from');
    $('.last-move-to').removeClass('last-move-to');
    
    lastMove = null;
}

function updateLastMoveDisplay(move) {
    if (move && move.from && move.to) {
        showLastMoveArrow(move.from, move.to);
    } else {
        hideLastMoveArrow();
    }
}
