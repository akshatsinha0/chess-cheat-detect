// Chess board and game instance
let board = null;
let game = new Chess();
let socket = null;
let capturedFEN = null;

// Initialize the application
$(document).ready(function() {
    initBoard();
    initSocket();
    updateStatus();
});

// Initialize the chess board
function initBoard() {
    const config = {
        draggable: true,
        position: 'start',
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
    // See if the move is legal
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q' // Always promote to queen for simplicity
    });
    
    // Illegal move
    if (move === null) return 'snapback';
    
    // Send move to server
    $.post('/api/make_move', {
        move: move.from + move.to + (move.promotion || '')
    }).done(function(response) {
        if (response.status === 'success') {
            updateStatus();
            updateCurrentAnalysis(response.analysis);
            addMoveToHistory(move.san, response.analysis);
        }
    }).fail(function(error) {
        // Revert move
        game.undo();
        board.position(game.fen());
        showAlert('Error making move: ' + error.responseJSON.message, 'danger');
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
function addMoveToHistory(move, analysis) {
    const moveNum = $('#moveHistory tr').length + 1;
    const evalValue = analysis.evaluation?.value || 0;
    const evalType = analysis.evaluation?.type || 'cp';
    const suspicionPercent = (analysis.suspicion_score * 100).toFixed(1);
    
    let evalDisplay = '';
    if (evalType === 'mate') {
        evalDisplay = `M${Math.abs(evalValue)}`;
    } else {
        evalDisplay = (evalValue / 100).toFixed(2);
    }
    
    let suspicionClass = '';
    if (analysis.suspicion_score > 0.7) {
        suspicionClass = 'table-danger';
    } else if (analysis.suspicion_score > 0.5) {
        suspicionClass = 'table-warning';
    }
    
    const row = `
        <tr class="${suspicionClass}">
            <td>${moveNum}</td>
            <td>${move}</td>
            <td>${analysis.best_move}</td>
            <td>${evalDisplay}</td>
            <td>${suspicionPercent}%</td>
        </tr>
    `;
    
    $('#moveHistory').append(row);
}

// Button click handlers
function newGame() {
    $.post('/api/new_game').done(function(response) {
        if (response.status === 'success') {
            game = new Chess();
            board.position('start');
            $('#moveHistory').empty();
            $('#currentAnalysis').html('<p class="text-muted">Make a move to see analysis</p>');
            updateStatus();
            showAlert('New game started!', 'success');
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
