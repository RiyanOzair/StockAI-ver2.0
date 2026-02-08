"""
Rate Limiter for LLM API Calls
==============================
Implements sliding window rate limiting to prevent hitting API provider limits.
Thread-safe and supports exponential backoff.
"""

import time
from threading import Lock
from collections import deque
from typing import Optional
from functools import wraps


class RateLimiter:
    """
    Sliding window rate limiter for API calls.
    
    Usage:
        limiter = RateLimiter(max_calls=30, window_seconds=60)
        
        # Option 1: Check and wait
        limiter.wait_if_needed()
        make_api_call()
        
        # Option 2: Check wait time
        wait_time = limiter.acquire()
        if wait_time > 0:
            time.sleep(wait_time)
        make_api_call()
        
        # Option 3: Decorator
        @limiter.limit
        def make_api_call():
            ...
    """
    
    def __init__(self, max_calls: int = 30, window_seconds: float = 60.0):
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = deque()
        self.lock = Lock()
    
    def acquire(self) -> float:
        """
        Attempt to acquire permission to make a call.
        
        Returns:
            Wait time in seconds if rate limited, 0 if call is allowed immediately.
        """
        with self.lock:
            now = time.time()
            
            # Remove calls outside the window
            while self.calls and self.calls[0] < now - self.window_seconds:
                self.calls.popleft()
            
            if len(self.calls) >= self.max_calls:
                # Calculate how long until oldest call expires
                wait_time = self.calls[0] + self.window_seconds - now
                return max(0, wait_time)
            
            # Record this call
            self.calls.append(now)
            return 0
    
    def wait_if_needed(self) -> float:
        """
        Block until a call is allowed, then record the call.
        
        Returns:
            Time waited in seconds (0 if no wait was needed)
        """
        wait_time = self.acquire()
        if wait_time > 0:
            time.sleep(wait_time)
            # Record the call after waiting
            with self.lock:
                self.calls.append(time.time())
            return wait_time
        return 0
    
    def limit(self, func):
        """
        Decorator to rate limit a function.
        
        Usage:
            @limiter.limit
            def my_api_call():
                ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
    
    def get_remaining_calls(self) -> int:
        """Get the number of calls remaining in the current window."""
        with self.lock:
            now = time.time()
            # Clean old calls
            while self.calls and self.calls[0] < now - self.window_seconds:
                self.calls.popleft()
            return max(0, self.max_calls - len(self.calls))
    
    def get_reset_time(self) -> Optional[float]:
        """
        Get seconds until the rate limit resets (oldest call expires).
        
        Returns:
            Seconds until reset, or None if not rate limited
        """
        with self.lock:
            if not self.calls:
                return None
            now = time.time()
            oldest = self.calls[0]
            reset_time = oldest + self.window_seconds - now
            return max(0, reset_time)
    
    def reset(self):
        """Clear all recorded calls (use for testing or after errors)."""
        with self.lock:
            self.calls.clear()


class ExponentialBackoff:
    """
    Exponential backoff helper for retrying failed requests.
    
    Usage:
        backoff = ExponentialBackoff()
        
        while True:
            try:
                result = make_api_call()
                backoff.reset()  # Success, reset backoff
                break
            except RateLimitError:
                wait_time = backoff.get_wait_time()
                if wait_time is None:
                    raise  # Max retries exceeded
                time.sleep(wait_time)
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        max_retries: int = 5,
        jitter: float = 0.1
    ):
        """
        Initialize exponential backoff.
        
        Args:
            initial_delay: Starting delay in seconds
            max_delay: Maximum delay cap in seconds
            multiplier: Factor to multiply delay by after each retry
            max_retries: Maximum number of retries before giving up
            jitter: Random jitter factor (0-1) to prevent thundering herd
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.max_retries = max_retries
        self.jitter = jitter
        self.attempts = 0
    
    def get_wait_time(self) -> Optional[float]:
        """
        Get the next wait time, or None if max retries exceeded.
        """
        if self.attempts >= self.max_retries:
            return None
        
        import random
        delay = self.initial_delay * (self.multiplier ** self.attempts)
        delay = min(delay, self.max_delay)
        
        # Add jitter
        if self.jitter > 0:
            delay *= (1 + random.uniform(-self.jitter, self.jitter))
        
        self.attempts += 1
        return delay
    
    def reset(self):
        """Reset the backoff state after a successful call."""
        self.attempts = 0


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-CONFIGURED LIMITERS FOR LLM PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════════

# Groq - Free tier: ~30 requests/minute
groq_limiter = RateLimiter(max_calls=25, window_seconds=60.0)

# Google Gemini - Free tier: ~60 requests/minute
gemini_limiter = RateLimiter(max_calls=50, window_seconds=60.0)

# OpenAI - Varies by tier, conservative default
openai_limiter = RateLimiter(max_calls=50, window_seconds=60.0)

# Ollama - Local, no real limit but prevent overwhelming
ollama_limiter = RateLimiter(max_calls=100, window_seconds=60.0)


def get_limiter_for_provider(provider: str) -> RateLimiter:
    """Get the appropriate rate limiter for a provider."""
    limiters = {
        "groq": groq_limiter,
        "gemini": gemini_limiter,
        "google": gemini_limiter,
        "openai": openai_limiter,
        "ollama": ollama_limiter,
    }
    return limiters.get(provider.lower(), RateLimiter(max_calls=30, window_seconds=60))
