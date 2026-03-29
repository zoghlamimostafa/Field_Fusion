"""
Rate Limiting Middleware for Flask API
Implements token bucket algorithm for rate limiting
"""

import time
from functools import wraps
from flask import request, jsonify
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """
    Rate limiter using token bucket algorithm

    Features:
    - Per-user rate limiting
    - Configurable rate limits per endpoint
    - Thread-safe implementation
    - Automatic token refill
    """

    def __init__(self):
        self.buckets = defaultdict(lambda: {'tokens': 0, 'last_update': time.time()})
        self.lock = Lock()

        # Default rate limits (requests per minute)
        self.rate_limits = {
            'default': 60,           # 60 requests per minute
            'upload': 5,             # 5 uploads per minute
            'analysis': 10,          # 10 analysis requests per minute
            'download': 30,          # 30 downloads per minute
            'auth': 20,              # 20 auth requests per minute
            'analytics': 100         # 100 analytics queries per minute
        }

        # Burst allowance (max tokens that can accumulate)
        self.burst_limits = {
            'default': 100,
            'upload': 10,
            'analysis': 20,
            'download': 60,
            'auth': 40,
            'analytics': 200
        }

    def _get_bucket_key(self, identifier, limit_type):
        """Generate bucket key for user and limit type"""
        return f"{identifier}:{limit_type}"

    def _refill_tokens(self, bucket, rate_per_minute, burst_limit):
        """Refill tokens based on time elapsed"""
        current_time = time.time()
        time_elapsed = current_time - bucket['last_update']

        # Calculate tokens to add (rate per minute converted to per second)
        tokens_to_add = time_elapsed * (rate_per_minute / 60.0)

        # Update bucket
        bucket['tokens'] = min(burst_limit, bucket['tokens'] + tokens_to_add)
        bucket['last_update'] = current_time

    def is_allowed(self, identifier, limit_type='default', cost=1):
        """
        Check if request is allowed under rate limit

        Args:
            identifier: User identifier (username, IP, API key)
            limit_type: Type of rate limit to apply
            cost: Number of tokens to consume (default: 1)

        Returns:
            tuple: (allowed: bool, retry_after: float)
        """
        with self.lock:
            bucket_key = self._get_bucket_key(identifier, limit_type)
            bucket = self.buckets[bucket_key]

            # Get rate limit configuration
            rate_limit = self.rate_limits.get(limit_type, self.rate_limits['default'])
            burst_limit = self.burst_limits.get(limit_type, self.burst_limits['default'])

            # Refill tokens
            self._refill_tokens(bucket, rate_limit, burst_limit)

            # Check if enough tokens available
            if bucket['tokens'] >= cost:
                bucket['tokens'] -= cost
                return True, 0
            else:
                # Calculate retry_after (time until enough tokens available)
                tokens_needed = cost - bucket['tokens']
                retry_after = (tokens_needed * 60.0) / rate_limit
                return False, retry_after

    def get_stats(self, identifier, limit_type='default'):
        """Get current rate limit stats for identifier"""
        with self.lock:
            bucket_key = self._get_bucket_key(identifier, limit_type)
            bucket = self.buckets[bucket_key]

            # Get rate limit configuration
            rate_limit = self.rate_limits.get(limit_type, self.rate_limits['default'])
            burst_limit = self.burst_limits.get(limit_type, self.burst_limits['default'])

            # Refill tokens to get current state
            self._refill_tokens(bucket, rate_limit, burst_limit)

            return {
                'limit_type': limit_type,
                'rate_limit': rate_limit,
                'burst_limit': burst_limit,
                'tokens_available': int(bucket['tokens']),
                'tokens_used': burst_limit - int(bucket['tokens'])
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(limit_type='default', cost=1):
    """
    Decorator to apply rate limiting to Flask routes

    Args:
        limit_type: Type of rate limit (upload, analysis, download, etc.)
        cost: Number of tokens to consume per request

    Usage:
        @app.route('/api/upload', methods=['POST'])
        @rate_limit(limit_type='upload', cost=1)
        def upload_video():
            # Your endpoint logic
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get identifier (username if authenticated, IP otherwise)
            identifier = kwargs.get('current_user')

            if not identifier:
                # Fall back to IP address
                identifier = request.remote_addr

            # Check rate limit
            allowed, retry_after = rate_limiter.is_allowed(identifier, limit_type, cost)

            if not allowed:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {int(retry_after)} seconds.',
                    'retry_after': int(retry_after),
                    'limit_type': limit_type
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(int(retry_after))
                response.headers['X-RateLimit-Limit'] = str(rate_limiter.rate_limits.get(limit_type, 60))
                response.headers['X-RateLimit-Remaining'] = '0'
                return response

            # Get current stats for headers
            stats = rate_limiter.get_stats(identifier, limit_type)

            # Execute endpoint
            result = f(*args, **kwargs)

            # Add rate limit headers to response
            if isinstance(result, tuple):
                response, status_code = result[0], result[1]
            else:
                response = result
                status_code = 200

            # Add headers if response is a Flask response object
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(stats['rate_limit'])
                response.headers['X-RateLimit-Remaining'] = str(stats['tokens_available'])
                response.headers['X-RateLimit-Reset'] = str(int(time.time() + 60))

            return response, status_code if isinstance(result, tuple) else response

        return decorated_function
    return decorator


def get_rate_limit_info(identifier, limit_type='default'):
    """
    Get rate limit information for a user

    Args:
        identifier: User identifier
        limit_type: Type of rate limit

    Returns:
        dict: Rate limit statistics
    """
    return rate_limiter.get_stats(identifier, limit_type)
