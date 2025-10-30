"""Retry utilities for database operations."""

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.exc import DBAPIError, OperationalError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_on_db_error(
    func: Callable[..., T],
    *args: Any,  # noqa: ANN401
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    **kwargs: Any,  # noqa: ANN401
) -> T:
    """
    Retry a function on database errors with exponential backoff.

    Args:
        func: The function to retry
        *args: Positional arguments to pass to the function
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call

    Raises:
        The last exception if all retries fail

    """
    last_exception: Exception | None = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (OperationalError, DBAPIError) as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    "Database operation failed (attempt %d/%d): %s. Retrying in %.2f seconds...",
                    attempt + 1,
                    max_retries + 1,
                    str(e),
                    delay,
                )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(
                    "Database operation failed after %d attempts: %s",
                    max_retries + 1,
                    str(e),
                )

    if last_exception:
        raise last_exception

    msg = "Unexpected error in retry_on_db_error"
    raise RuntimeError(msg)
