"""Users API routes"""

from flask import Blueprint, request, jsonify
from app.services.user_service import UserService, ValidationError, UpstreamError
from app.utils.errors import bad_request, conflict, not_found, internal_server_error, problem_details

users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@users_bp.post("")
def create_user():
    """Create a new user"""
    data = request.get_json()

    try:
        # Validate user data using UserService
        validated_data = UserService.validate_user_data(data)
        email = validated_data["email"]
        nombre = validated_data["nombre"]

        # Create user using UserService
        user_data = UserService.create_user(email, nombre)

        response = jsonify(user_data)
        response.status_code = 201
        return response

    except ValidationError as e:
        # Handle validation errors
        if "already exists" in str(e):
            return conflict(str(e), instance="/api/v1/users")
        return bad_request(str(e), instance="/api/v1/users")
    except UpstreamError as e:
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        return internal_server_error(str(e))


@users_bp.get("/<int:user_id>")
def get_user(user_id: int):
    """Retrieve a user by ID"""
    try:
        user_data = UserService.get_user_by_id(user_id)

        if not user_data:
            return not_found(
                f"User with ID {user_id} not found",
                instance=f"/api/v1/users/{user_id}"
            )

        response = jsonify(user_data)
        response.status_code = 200
        return response
        
    except UpstreamError as e:
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        return internal_server_error(str(e))
