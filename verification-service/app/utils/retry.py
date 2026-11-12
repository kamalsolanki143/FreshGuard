import asyncio
import logging
import random
from functools import wraps
from typing import Any, Callable, Coroutine, Tuple, Type

logger = logging.getLogger("freshguard.retry")


def retry_async(
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    max_retries: int = 2,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
):
    """
    Decorator for retrying async operations with exponential backoff and optional jitter.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt > max_retries:
                        logger.warning(
                            "Function %s failed after %d retries. Propagating exception: %s",
                            func.__name__,
                            max_retries,
                            str(e),
                        )
                        raise

                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    if jitter:
                        delay += random.uniform(0, delay * 0.1)

                    logger.info(
                        "Retry %d/%d for %s after %.2fs due to: %s",
                        attempt,
                        max_retries,
                        func.__name__,
                        delay,
                        str(e),
                    )
                    await asyncio.sleep(delay)

        return wrapper
    return decorator
