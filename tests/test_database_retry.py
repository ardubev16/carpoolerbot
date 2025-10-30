"""Test database retry logic."""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import OperationalError

from carpoolerbot.database.retry import retry_on_db_error


def test_retry_on_db_error_succeeds_first_try():
    """Test that function succeeds on first try."""
    mock_func = Mock(return_value="success")
    result = retry_on_db_error(mock_func)
    assert result == "success"
    assert mock_func.call_count == 1


def test_retry_on_db_error_succeeds_after_retries():
    """Test that function succeeds after retries."""
    # OperationalError args: (statement, params, orig) - using None for minimal test setup
    mock_func = Mock(side_effect=[OperationalError("error", None, None), "success"])
    result = retry_on_db_error(mock_func, max_retries=3, initial_delay=0.01)
    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_on_db_error_fails_after_max_retries():
    """Test that function fails after max retries."""
    mock_func = Mock(side_effect=OperationalError("error", None, None))
    with pytest.raises(OperationalError):
        retry_on_db_error(mock_func, max_retries=2, initial_delay=0.01)
    assert mock_func.call_count == 3  # Initial try + 2 retries


def test_retry_on_db_error_with_args_and_kwargs():
    """Test that function is called with correct args and kwargs."""
    mock_func = Mock(return_value="success")
    result = retry_on_db_error(mock_func, "arg1", "arg2", kwarg1="value1")
    assert result == "success"
    mock_func.assert_called_with("arg1", "arg2", kwarg1="value1")


def test_retry_on_db_error_exponential_backoff():
    """Test that retry delays follow exponential backoff."""
    mock_func = Mock(
        side_effect=[
            OperationalError("error", None, None),
            OperationalError("error", None, None),
            "success",
        ]
    )

    with patch("carpoolerbot.database.retry.time.sleep") as mock_sleep:
        result = retry_on_db_error(mock_func, max_retries=3, initial_delay=0.5, backoff_factor=2.0)
        assert result == "success"
        assert mock_func.call_count == 3

        # Verify exponential backoff: 0.5s, 1.0s
        assert mock_sleep.call_count == 2
        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays[0] == 0.5
        assert delays[1] == 1.0


def test_retry_on_db_error_non_retriable_exception():
    """Test that non-retriable exceptions are not retried."""
    mock_func = Mock(side_effect=ValueError("not a db error"))
    with pytest.raises(ValueError):
        retry_on_db_error(mock_func, max_retries=3, initial_delay=0.01)
    assert mock_func.call_count == 1  # Only one try, no retries
