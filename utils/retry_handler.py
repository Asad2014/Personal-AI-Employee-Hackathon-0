# utils/retry_handler.py - Exponential backoff retry decorator
import time
import logging
import functools
import random

logger = logging.getLogger('RetryHandler')


def with_retry(max_attempts=3, base_delay=2, max_delay=60, exceptions=(Exception,)):
    """Decorator that retries a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        exceptions: Tuple of exception types to catch and retry on
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f'{func.__name__} failed after {max_attempts} attempts: {e}'
                        )
                        raise
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    wait = delay + jitter
                    logger.warning(
                        f'{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. '
                        f'Retrying in {wait:.1f}s...'
                    )
                    time.sleep(wait)
            raise last_exception
        return wrapper
    return decorator
