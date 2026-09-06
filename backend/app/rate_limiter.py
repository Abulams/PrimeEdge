"""
Market-OS In-Memory Sliding Window Rate Limiter
===============================================
Zero-dependency, thread-safe rate limiter protecting sensitive public endpoints:
  - /api/v1/auth/login (5 req/min)
  - /api/v1/waitlist (3 req/min)
  - /api/v1/chat (20 req/min)
"""

import time
import threading
from collections import defaultdict
from fastapi import Request, HTTPException, status

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def check(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        with self.lock:
            # Clean old entries
            window_start = now - self.window_seconds
            timestamps = [t for t in self.requests[client_ip] if t > window_start]

            if len(timestamps) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )

            timestamps.append(now)
            self.requests[client_ip] = timestamps


# Pre-configured instances
login_rate_limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=60)
waitlist_rate_limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
ai_rate_limiter = SlidingWindowRateLimiter(max_requests=20, window_seconds=60)
