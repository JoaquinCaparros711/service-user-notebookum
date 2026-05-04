"""User service for business logic and persistence proxy"""

import re
import requests
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

    @staticmethod
    def validate_user_data(data: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Validate user input data."""
        if not data or not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON")

        email = data.get("email", "").strip()
        nombre = data.get("nombre", "").strip()

        if not email:
            raise ValidationError("Email is required")

        if not nombre:
            raise ValidationError("Name (nombre) is required")

        # RFC 5322 simplified email validation pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError("Email format is invalid")

        # Validate nombre length (reasonable bounds)
        if len(nombre) > 255:
            raise ValidationError("Name (nombre) must not exceed 255 characters")

        if len(nombre) < 2:
            raise ValidationError("Name (nombre) must be at least 2 characters")

        return {"email": email, "nombre": nombre}

    @staticmethod
    def create_user(email: str, nombre: str) -> Dict[str, Any]:
        """
        Create a new user by delegating to Persistence microservice.
        """
        persistence_url = current_app.config.get("PERSISTENCE_URL")
        
        try:
            response = requests.post(
                f"{persistence_url}/api/v1/db/users",
                json={"email": email, "nombre": nombre},
                timeout=5
            )
            
            if response.status_code == 409:
                raise ValidationError(f"User with email '{email}' already exists")
            elif response.status_code >= 400:
                error_msg = response.json().get("detail", "Error in persistence service")
                raise UpstreamError(error_msg, response.status_code)
                
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"Failed to connect to persistence service: {str(e)}", 503)

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by delegating to Persistence microservice.
        """
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
                
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise UpstreamError(f"Failed to connect to persistence service: {str(e)}", 503)
