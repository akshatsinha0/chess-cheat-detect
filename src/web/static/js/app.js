// Chess board and game instance
let board = null;
let game = new Chess();
let socket = null;
let capturedFEN = null;

// Store move history as pairs of white/black moves and their analysis
let moveHistoryPairs = [];

// PGN navigation state
let pgnMoves = [];
let currentMoveIndex = 0;
let pgnBaseFen = null;

// On page load, fetch backend FEN and sync board/game
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
    });
});

// Initialize the chess board
function initBoard() {
    const config = {
        draggable: true,
        position: 'start',
        pieceTheme: 'https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/img/chesspieces/wikipedia/{piece}.png',
        onDragStart: onDragStart,
        onDrop: onDrop,
        onSnapEnd: onSnapEnd
    };
    board = Chessboard('board', config);
}

// Initialize WebSocket connection
function initSocket() {
    socket = io();
    
    socket.on('connected', function(data) {
        console.log(data.message);
    });
    
    socket.on('move_made', function(data) {
        // Update board position
        board.position(data.fen);
        
        // Update analysis
        updateCurrentAnalysis(data.analysis);
        addMoveToHistory(data.move, data.analysis);
    });
    
    socket.on('analysis_result', function(data) {
        updateCurrentAnalysis(data);
    });
}

// Chess board event handlers
function onDragStart(source, piece, position, orientation) {
    // Do not pick up pieces if the game is over
    if (game.game_over()) return false;
    
    // Only pick up pieces for the side to move
    if ((game.turn() === 'w' && piece.search(/^b/) !== -1) ||
        (game.turn() === 'b' && piece.search(/^w/) !== -1)) {
        return false;
    }
}

function onDrop(source, target) {
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q'
    });
    if (move === null) return 'snapback';
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
            }
        },
        error: function(error) {
            // On error, sync board/game with backend FEN
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

// Update game status
function updateStatus() {
    let status = '';
    
    const moveColor = game.turn() === 'b' ? 'Black' : 'White';
    
    // Checkmate?
    if (game.in_checkmate()) {
        status = 'Game over, ' + moveColor + ' is in checkmate.';
    }
    // Draw?
    else if (game.in_draw()) {
        status = 'Game over, drawn position';
    }
    // Game still on
    else {
        status = moveColor + ' to move';
        
        // Check?
        if (game.in_check()) {
            status += ', ' + moveColor + ' is in check';
        }
    }
    
    $('#fenInput').val(game.fen());
}

// Update current analysis display
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
        <div class="row">
            <div class="col-md-6">
                <h6>Best Move:</h6>
                <p class="fw-bold">${analysis.best_move || 'N/A'}</p>
            </div>
            <div class="col-md-6">
                <h6>Evaluation:</h6>
                <p class="fw-bold">${evalDisplay}</p>
            </div>
        </div>
        <div class="mt-3">
            <h6>Cheating Suspicion:</h6>
            <div class="progress" style="height: 25px;">
                <div class="progress-bar bg-${suspicionClass}" role="progressbar" 
                     style="width: ${suspicionPercent}%">
                    ${suspicionPercent}%
                </div>
            </div>
        </div>
    `;
    
    $('#currentAnalysis').html(html);
    
    // Show alert if high suspicion
    if (analysis.suspicion_score > 0.7) {
        showAlert('High cheating probability detected!', 'danger');
    }
}

// Add move to history table
function addMoveToHistory(san, analysis) {
    const isWhite = (game.history().length % 2) === 1;
    if (isWhite) {
        // New turn, add a new row with white's move and analysis
        moveHistoryPairs.push({
            white: san,
            black: '',
            whiteAnalysis: analysis,
            blackAnalysis: null
        });
    } else {
        // Fill in black's move and analysis in the last row
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

// Button click handlers
function newGame() {
    $.post('/api/new_game', function(response) {
        if (response.status === 'success') {
            board.position(response.fen);
            game.load(response.fen);
            moveHistoryPairs = [];
            renderMoveHistoryTable();
            updateStatus();
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
            // Update board with FEN
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
            
            // Display game summary
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
            
            // Clear move history and display all analyzed moves
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
            // Parse moves for navigation
            pgnMoves = game.history({ verbose: true });
            currentMoveIndex = pgnMoves.length;
            pgnBaseFen = new Chess().fen(); // Always start from standard position for PGN
            board.position(game.fen());
            updateMoveListForPGN();
            updateStatus();
            showAlert('PGN applied to board.', 'success');
        } else {
            showAlert('Invalid PGN string.', 'danger');
        }
    }
}

function updateMoveListForPGN() {
    // Rebuild moveHistoryPairs from PGN moves up to currentMoveIndex
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
    }
}

function flipBoard() {
    board.flip();
}

// Show alert message
function showAlert(message, type = 'info', duration = 5000) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const alertElement = $(alertHtml);
    $('#alertContainer').append(alertElement);
    
    // Auto dismiss after duration
    setTimeout(() => {
        alertElement.alert('close');
    }, duration);
}
