"""JWT token generation and validation utilities"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

from flask import current_app, jsonify, request
import jwt


class JWTError(Exception):
    """Base exception for JWT errors"""
    pass


class TokenExpiredError(JWTError):
    """Token has expired"""
    pass


class InvalidTokenError(JWTError):
    """Token is invalid or malformed"""
    pass


class JWTHandler:
    """Handle JWT token generation and validation"""

    @staticmethod
    def generate_token(user_id: int, email: str, expires_in: int = 3600) -> tuple[str, int]:
        """
        Generate a JWT token.
        
        Args:
            user_id: User ID to encode in token
            email: User email to encode in token
            expires_in: Token expiration time in seconds (default 1 hour)
            
        Returns:
            Tuple of (token, expires_in)
        """
        secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key")
        
        payload = {
            "user_id": user_id,
            "email": email,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        }
        
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token, expires_in

    @staticmethod
    def generate_refresh_token(user_id: int, email: str) -> tuple[str, int]:
        """
        Generate a refresh token with longer expiration.
        
        Args:
            user_id: User ID to encode in token
            email: User email to encode in token
            
        Returns:
            Tuple of (refresh_token, expires_in) where expires_in is 7 days
        """
        secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key")
        expires_in = 7 * 24 * 3600  # 7 days
        
        payload = {
            "user_id": user_id,
            "email": email,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        }
        
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token, expires_in

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid or malformed
        """
        secret_key = current_app.config.get("SECRET_KEY", "dev-secret-key")
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")

    @staticmethod
    def get_token_from_request() -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        
        Expected format: Authorization: Bearer <token>
        
        Returns:
            Token string or None if not found
        """
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header:
            return None
            
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
            
        return parts[1]


def require_auth(f):
    """
    Decorator to require valid JWT token for an endpoint.
    
    Validates token and adds user_id and email to request context.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.utils.errors import problem_details, forbidden
        
        token = JWTHandler.get_token_from_request()
        
        if not token:
            return problem_details(
                status=401,
                title="Unauthorized",
                detail="Missing or invalid Authorization header",
            ), 401
        
        try:
            payload = JWTHandler.verify_token(token)
            # Store in request context for use in the handler
            request.user_id = payload.get("user_id")
            request.user_email = payload.get("email")
            request.token_type = payload.get("type", "access")
        except TokenExpiredError:
            return problem_details(
                status=401,
                title="Unauthorized",
                detail="Token has expired",
            ), 401
        except InvalidTokenError as e:
            return problem_details(
                status=401,
                title="Unauthorized",
                detail=str(e),
            ), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
