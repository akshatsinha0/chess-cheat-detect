import pytest
from src.core.stockfish_engine import analyze_position
@pytest.mark.parametrize("fen,depth", [
    ("rnbqkb1r/pppp1ppp/5n2/4p3/4P3/2N5/PPPP1PPP/R1BQKBNR w KQkq - 2 3", 5),
    ("8/8/8/8/8/8/8/8 w - - 0 1", 5)
])
def test_analyze_position_returns_valid_structure(fen, depth):
    result = analyze_position(fen, depth=depth)
    assert isinstance(result, dict)
    assert "best_move" in result and isinstance(result["best_move"], str)
    assert "evaluation" in result and isinstance(result["evaluation"], dict)
    eval_dict = result["evaluation"]
    assert "type" in eval_dict and "value" in eval_dict
    assert isinstance(eval_dict["value"], int)
