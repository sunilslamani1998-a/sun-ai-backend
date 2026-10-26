from verification import verify_result
from sandbox import check_python_syntax


def test_nonempty_result():
    assert verify_result("Hello")["passed"] is True


def test_empty_result():
    assert verify_result(" ")["passed"] is False


def test_valid_python():
    assert check_python_syntax("x = 1")["passed"] is True


def test_invalid_python():
    assert check_python_syntax("def broken(:")["passed"] is False
