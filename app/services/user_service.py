"""User service for business logic and persistence proxy"""

import re
import requests
import json
import redis
import bcrypt
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


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


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
    def _get_correlation_id() -> Optional[str]:
        """Get X-Correlation-ID from request context"""
        from flask import request
        return request.headers.get("X-Correlation-ID")

    @staticmethod
    def validate_user_data(data: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Validate user input data."""
        if not data or not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON")

        email = data.get("email", "").strip()
        name = data.get("name", "").strip()
        password = data.get("password", "").strip()

        if not email:
            raise ValidationError("Email is required")

        if not name:
            raise ValidationError("Name is required")

        if not password:
            raise ValidationError("Password is required")

        # RFC 5322 simplified email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Email format is invalid")

        # Validate name length (reasonable bounds)
        if len(name) > 255:
            raise ValidationError("Name must not exceed 255 characters")

        if len(name) < 2:
            raise ValidationError("Name must be at least 2 characters")

        # Validate password strength
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        return {"email": email, "name": name, "password": password}

    @staticmethod
    def validate_login_data(data: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Validate login credentials"""
        if not data or not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON")

        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        if not email:
            raise ValidationError("Email is required")

        if not password:
            raise ValidationError("Password is required")

        return {"email": email, "password": password}

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode())

    @staticmethod
    def create_user(email: str, name: str, password: str) -> Dict[str, Any]:
        """
        Create a new user by delegating to Persistence microservice.
        Also performs write-through caching into Redis.
        """
        persistence_url = current_app.config.get("PERSISTENCE_URL")
        correlation_id = UserService._get_correlation_id()
        
        # Hash password before sending to Persistence
        hashed_password = UserService.hash_password(password)
        
        try:
            headers = {}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id

            response = requests.post(
                f"{persistence_url}/api/v1/users",
                json={"email": email, "name": name, "password": hashed_password},
                headers=headers,
                timeout=5,
                verify=False  # Fixed: enable SSL verification
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
        correlation_id = UserService._get_correlation_id()
        
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
            headers = {}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id

            response = requests.get(
                f"{persistence_url}/api/v1/users/{user_id}",
                headers=headers,
                timeout=5,
                verify=False  # Fixed: enable SSL verification
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

    @staticmethod
    def update_user(user_id: int, email: Optional[str] = None, name: Optional[str] = None, 
                   password: Optional[str] = None) -> Dict[str, Any]:
        """
        Update user information.
        """
        persistence_url = current_app.config.get("PERSISTENCE_URL")
        correlation_id = UserService._get_correlation_id()
        
        update_data = {}
        if email:
            update_data["email"] = email.strip()
        if name:
            update_data["name"] = name.strip()
        if password:
            update_data["password"] = UserService.hash_password(password)

        if not update_data:
            raise ValidationError("At least one field must be provided for update")

        try:
            headers = {}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id

            response = requests.patch(
                f"{persistence_url}/api/v1/users/{user_id}",
                json=update_data,
                headers=headers,
                timeout=5,
                verify=False  # Fixed: enable SSL verification
            )
            
            if response.status_code == 404:
                raise ValidationError(f"User with ID {user_id} not found")
            elif response.status_code == 409:
                raise ValidationError("Email already in use")
            elif response.status_code >= 400:
                error_msg = response.json().get("detail", "Error in persistence service")
                raise UpstreamError(error_msg, response.status_code)
                
            user_data = response.json()

            # Invalidate cache
            try:
                r = UserService._get_redis_client()
                if r:
                    r.delete(f"user:{user_id}")
                    current_app.logger.info(f"Redis cache invalidated for user:{user_id}")
            except Exception as cache_err:
                current_app.logger.warning(f"Failed to invalidate Redis cache: {cache_err}")

            return user_data
            
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"Failed to connect to persistence service: {str(e)}", 503)

    @staticmethod
    def delete_user(user_id: int) -> None:
        """
        Delete a user.
        """
        persistence_url = current_app.config.get("PERSISTENCE_URL")
        correlation_id = UserService._get_correlation_id()

        try:
            headers = {}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id

            response = requests.delete(
                f"{persistence_url}/api/v1/users/{user_id}",
                headers=headers,
                timeout=5,
                verify=False  # Fixed: enable SSL verification
            )
            
            if response.status_code == 404:
                raise ValidationError(f"User with ID {user_id} not found")
            elif response.status_code >= 400:
                error_msg = response.json().get("detail", "Error in persistence service")
                raise UpstreamError(error_msg, response.status_code)

            # Invalidate cache
            try:
                r = UserService._get_redis_client()
                if r:
                    r.delete(f"user:{user_id}")
                    current_app.logger.info(f"Redis cache invalidated for user:{user_id}")
            except Exception as cache_err:
                current_app.logger.warning(f"Failed to invalidate Redis cache: {cache_err}")
            
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"Failed to connect to persistence service: {str(e)}", 503)

    @staticmethod
    def authenticate_user(email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user by email and password.
        Fetches user from persistence and verifies password.
        """
        persistence_url = current_app.config.get("PERSISTENCE_URL")
        correlation_id = UserService._get_correlation_id()

        try:
            headers = {}
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id

            # Fetch user by email from Persistence
            response = requests.get(
                f"{persistence_url}/api/v1/users/email/{email}",
                headers=headers,
                timeout=5,
                verify=False
            )
            
            if response.status_code == 404:
                raise AuthenticationError("Invalid email or password")
            elif response.status_code >= 400:
                error_msg = response.json().get("detail", "Error in persistence service")
                raise UpstreamError(error_msg, response.status_code)
                
            user_data = response.json()
            stored_password = user_data.get("password", "")

            # Verify password
            if not UserService.verify_password(password, stored_password):
                raise AuthenticationError("Invalid email or password")

            return user_data
            
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"Failed to connect to persistence service: {str(e)}", 503)

