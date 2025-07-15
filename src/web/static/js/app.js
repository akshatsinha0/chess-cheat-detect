let board = null;
let game = new Chess();
let socket = null;
let capturedFEN = null;
let moveHistoryPairs = [];
let pgnMoves = [];
let currentMoveIndex = 0;
let pgnBaseFen = null;
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
// --- Enhanced onDrop with sound ---
function onDrop(source, target) {
    const move = game.move({
        from: source,
        to: target,
        promotion: 'q'
    });
    if (move === null) return 'snapback';
    // Determine sound type
    let soundType = 'move';
    if (move.flags.includes('c')) soundType = 'capture';
    if (move.flags.includes('k') || move.flags.includes('q')) soundType = 'castle';
    if (move.flags.includes('p')) soundType = 'promote';
    // Check for check
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
    if (analysis.suspicion_score > 0.7) {
        showAlert('High cheating probability detected!', 'danger');
    }
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
}
// --- Keyboard Navigation ---
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
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    const alertElement = $(alertHtml);
    $('#alertContainer').append(alertElement);
    setTimeout(() => {
        alertElement.alert('close');
    }, duration);
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
// --- Updated Analyze PGN Button Logic ---
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
    // --- Updated Detect Cheat Button Logic ---
    $(".btn-primary.animated-btn:contains('Detect Cheat')").off('click').on('click', function() {
        let pgn = $('#analyzePgnInput').val().trim() || $('#pgnInput').val().trim();
        if (!pgn) {
            showAlert('Please paste a PGN for cheat detection.', 'warning');
            return;
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
// --- End of new features ---

function syncMoveHistoryFromGame() {
    pgnMoves = game.history({ verbose: true });
    pgnBaseFen = new Chess().fen();
    currentMoveIndex = pgnMoves.length;
}
