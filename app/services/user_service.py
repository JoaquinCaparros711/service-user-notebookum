"""User service for business logic and persistence proxy"""

import re
import requests
import json
import redis
from typing import Optional, Dict, Any
from flask import current_app

class ValidationError(Exception):
    """Raised when user data validation fails"""
    pass

class UpstreamError(Exception):
    """Raised when communication with persistence service fails"""
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.status_code = status_code


class UserService:
    """Service layer for user operations"""

    _redis_client = None

    @classmethod
    def _get_redis_client(cls):
        """Lazy loader for Redis client with fault tolerance"""
        if cls._redis_client is None:
            try:
                redis_url = current_app.config.get("REDIS_URL")
                if redis_url:
                    cls._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                current_app.logger.warning(f"Could not connect to Redis: {e}. Caching disabled.")
        return cls._redis_client

    @staticmethod
    def validate_user_data(data: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Validate user input data."""
        if not data or not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON")

        email = data.get("email", "").strip()
        name = data.get("name", "").strip()

        if not email:
            raise ValidationError("Email is required")

        if not name:
            raise ValidationError("Name is required")

        # RFC 5322 simplified email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Email format is invalid")

        # Validate name length (reasonable bounds)
        if len(name) > 255:
            raise ValidationError("Name must not exceed 255 characters")

        if len(name) < 2:
            raise ValidationError("Name must be at least 2 characters")

        return {"email": email, "name": name}

    @staticmethod
    def create_user(email: str, name: str) -> Dict[str, Any]:
        """
        Create a new user by delegating to Persistence microservice.
        Also performs write-through caching into Redis.
        """
        persistence_url = current_app.config.get("PERSISTENCE_URL")
        
        try:
            response = requests.post(
                f"{persistence_url}/api/v1/db/users",
                json={"email": email, "name": name},
                timeout=5, verify=False
            )
            
            if response.status_code == 409:
                raise ValidationError(f"User with email '{email}' already exists")
            elif response.status_code >= 400:
                error_msg = response.json().get("detail", "Error in persistence service")
                raise UpstreamError(error_msg, response.status_code)
                
            user_data = response.json()
            user_id = user_data.get("id")

            # Write-Through Caching: Cache user immediately upon creation (5 minutes TTL)
            if user_id:
                try:
                    r = UserService._get_redis_client()
                    if r:
                        r.setex(f"user:{user_id}", 300, json.dumps(user_data))
                        current_app.logger.info(f"Redis cache write-through success for user:{user_id}")
                except Exception as cache_err:
                    current_app.logger.warning(f"Failed to write to Redis cache: {cache_err}")

            return user_data
            
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"Failed to connect to persistence service: {str(e)}", 503)

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by checking Redis cache first, then falling back to Persistence.
        """
        # Try fetching from Redis cache first
        try:
            r = UserService._get_redis_client()
            if r:
                cached_user = r.get(f"user:{user_id}")
                if cached_user:
                    current_app.logger.info(f"Redis cache HIT for user:{user_id}")
                    return json.loads(cached_user)
                current_app.logger.info(f"Redis cache MISS for user:{user_id}")
        except Exception as cache_err:
            current_app.logger.warning(f"Failed to read from Redis cache: {cache_err}")

        persistence_url = current_app.config.get("PERSISTENCE_URL")
        
        try:
            response = requests.get(
                f"{persistence_url}/api/v1/db/users/{user_id}",
                timeout=5
            )
            
            if response.status_code == 404:
                return None
            elif response.status_code >= 400:
                error_msg = response.json().get("detail", "Error in persistence service")
                raise UpstreamError(error_msg, response.status_code)
                
            user_data = response.json()

            # Cache the fetched user in Redis (5 minutes TTL)
            try:
                r = UserService._get_redis_client()
                if r:
                    r.setex(f"user:{user_id}", 300, json.dumps(user_data))
                    current_app.logger.info(f"Redis cache SET success for user:{user_id}")
            except Exception as cache_err:
                current_app.logger.warning(f"Failed to save to Redis cache: {cache_err}")

            return user_data
            
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"Failed to connect to persistence service: {str(e)}", 503)
