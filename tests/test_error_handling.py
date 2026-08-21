"""Tests for utils/error_handling.py -- safe_call decorator and UserFacingError."""

from __future__ import annotations

import pytest

from utils.error_handling import UserFacingError, safe_call


def test_user_facing_error_carries_message_and_suggestion():
    original = ValueError("boom")
    err = UserFacingError(
        "Something went wrong", suggestion="Try again", original_error=original
    )
    assert err.message == "Something went wrong"
    assert err.suggestion == "Try again"
    assert err.original_error is original
    assert str(err) == "Something went wrong"


def test_safe_call_passes_through_successful_result():
    @safe_call(timeout=5)
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_safe_call_returns_fallback_on_exception():
    @safe_call(timeout=5, fallback=[], error_message="failed")
    def always_fails():
        raise RuntimeError("kaboom")

    assert always_fails() == []


def test_safe_call_raises_user_facing_error_without_fallback():
    @safe_call(timeout=5, fallback=None, error_message="custom failure message")
    def always_fails():
        raise RuntimeError("kaboom")

    with pytest.raises(UserFacingError) as exc_info:
        always_fails()
    assert exc_info.value.original_error is not None


def test_safe_call_reraises_user_facing_error_unchanged():
    inner = UserFacingError("already friendly", suggestion="do X")

    @safe_call(timeout=5, fallback=None)
    def raises_user_facing():
        raise inner

    with pytest.raises(UserFacingError) as exc_info:
        raises_user_facing()
    assert exc_info.value is inner


@pytest.mark.parametrize(
    "raised,expected_fragment",
    [
        (Exception("429 Too Many Requests"), "限制"),
        (Exception("401 Unauthorized"), "密钥"),
        (ConnectionError("network unreachable"), "网络"),
        (ValueError("Invalid JSON payload"), "解析"),
        (FileNotFoundError("no such file"), "文件"),
    ],
)
def test_safe_call_maps_known_error_types_to_friendly_messages(
    raised, expected_fragment
):
    @safe_call(timeout=5, fallback=None)
    def raises(exc=raised):
        raise exc

    with pytest.raises(UserFacingError) as exc_info:
        raises()
    assert expected_fragment in exc_info.value.message


def test_safe_call_unrecognized_error_uses_default_message():
    @safe_call(timeout=5, fallback=None, error_message="a very specific default")
    def raises_generic():
        raise RuntimeError("something truly unclassifiable")

    with pytest.raises(UserFacingError) as exc_info:
        raises_generic()
    assert exc_info.value.message == "a very specific default"
