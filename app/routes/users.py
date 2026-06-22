"""Users API routes"""

from flask import Blueprint, request, jsonify, current_app
from app.services.user_service import (
    UserService,
    ValidationError,
    UpstreamError,
    AuthenticationError,
)
from app.utils.errors import (
    bad_request,
    conflict,
    not_found,
    internal_server_error,
    problem_details,
)
from app.utils.jwt_handler import JWTHandler, require_auth, InvalidTokenError

users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")
user_service = UserService()


@users_bp.post("")
def create_user():
    """Create a new user"""
    data = request.get_json()

    try:
        # Validate user data using UserService
        validated_data = user_service.validate_user_data(data)
        email = validated_data["email"]
        name = validated_data["name"]
        password = validated_data["password"]

        current_app.logger.info(f"===> [USER-SERVICE] 👤 Creating user - Email: {email}, Name: {name}")

        # Create user using UserService
        user_data = user_service.create_user(email, name, password)

        current_app.logger.info(f"===> [USER-SERVICE] ✅ User created - ID: {user_data.get('id')}, Name: {user_data.get('name')}")

        response = jsonify(user_data)
        response.status_code = 201
        return response

    except ValidationError as e:
        current_app.logger.warning(f"===> [USER-SERVICE] ⚠️ Validation error: {str(e)}")
        if "already exists" in str(e):
            return conflict(str(e), instance="/api/v1/users")
        return bad_request(str(e), instance="/api/v1/users")
    except UpstreamError as e:
        current_app.logger.error(f"===> [USER-SERVICE] ❌ Upstream error: {str(e)}")
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Unexpected error: {str(e)}")
        return internal_server_error(str(e))


@users_bp.post("/login")
def login():
    """Login user and return JWT token"""
    data = request.get_json()

    try:
        validated_data = user_service.validate_login_data(data)
        email = validated_data["email"]
        password = validated_data["password"]

        current_app.logger.info(f"===> [USER-SERVICE] 🔑 Login attempt for email: {email}")

        # Authenticate user
        user_data = user_service.authenticate_user(email, password)
        user_id = user_data.get("id")

        # Generate tokens
        token, expires_in = JWTHandler.generate_token(user_id, email)
        refresh_token, refresh_expires_in = JWTHandler.generate_refresh_token(user_id, email)

        current_app.logger.info(f"===> [USER-SERVICE] ✅ Login successful - User ID: {user_id}")

        response = jsonify({
            "user_id": user_id,
            "email": email,
            "name": user_data.get("name"),
            "token": token,
            "expires_in": expires_in,
            "refresh_token": refresh_token,
            "refresh_expires_in": refresh_expires_in,
        })
        response.status_code = 200
        return response

    except ValidationError as e:
        current_app.logger.warning(f"===> [USER-SERVICE] ⚠️ Login validation error: {str(e)}")
        return bad_request(str(e), instance="/api/v1/users/login")
    except AuthenticationError as e:
        current_app.logger.warning(f"===> [USER-SERVICE] ⚠️ Authentication failed: {str(e)}")
        return problem_details(
            status=401,
            title="Unauthorized",
            detail=str(e),
            instance="/api/v1/users/login",
        )
    except UpstreamError as e:
        current_app.logger.error(f"===> [USER-SERVICE] ❌ Upstream error: {str(e)}")
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Unexpected error: {str(e)}")
        return internal_server_error(str(e))


@users_bp.post("/refresh")
def refresh_token():
    """Refresh JWT token"""
    data = request.get_json()

    try:
        refresh_token_str = data.get("refresh_token", "").strip()
        if not refresh_token_str:
            return bad_request("refresh_token is required", instance="/api/v1/users/refresh")

        # Verify refresh token
        payload = JWTHandler.verify_token(refresh_token_str)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            return problem_details(
                status=401,
                title="Unauthorized",
                detail="Invalid token type",
                instance="/api/v1/users/refresh",
            )

        user_id = payload.get("user_id")
        email = payload.get("email")

        current_app.logger.info(f"===> [USER-SERVICE] 🔄 Refreshing token for user: {user_id}")

        # Generate new access token
        new_token, expires_in = JWTHandler.generate_token(user_id, email)

        response = jsonify({
            "token": new_token,
            "expires_in": expires_in,
        })
        response.status_code = 200
        return response

    except InvalidTokenError as e:
        current_app.logger.warning(f"===> [USER-SERVICE] ⚠️ Invalid token: {str(e)}")
        return problem_details(
            status=401,
            title="Unauthorized",
            detail=str(e),
            instance="/api/v1/users/refresh",
        )
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Unexpected error: {str(e)}")
        return internal_server_error(str(e))


@users_bp.get("/<int:user_id>")
def get_user(user_id: int):
    """Retrieve a user by ID"""
    try:
        current_app.logger.info(f"===> [USER-SERVICE] 🔍 Fetching user: {user_id}")
        user_data = user_service.get_user_by_id(user_id)

        if not user_data:
            current_app.logger.warning(f"===> [USER-SERVICE] ❌ User not found: {user_id}")
            return not_found(
                f"User with ID {user_id} not found",
                instance=f"/api/v1/users/{user_id}"
            )

        current_app.logger.info(f"===> [USER-SERVICE] ✅ User found: {user_data.get('name')}")
        response = jsonify(user_data)
        response.status_code = 200
        return response
        
    except UpstreamError as e:
        current_app.logger.error(f"===> [USER-SERVICE] ❌ Upstream error: {str(e)}")
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Unexpected error: {str(e)}")
        return internal_server_error(str(e))


@users_bp.patch("/<int:user_id>")
@require_auth
def update_user(user_id: int):
    """Update user information (requires authentication)"""
    data = request.get_json()

    try:
        email = data.get("email", "").strip() if data.get("email") else None
        name = data.get("name", "").strip() if data.get("name") else None
        password = data.get("password", "").strip() if data.get("password") else None

        current_app.logger.info(f"===> [USER-SERVICE] ✏️ Updating user: {user_id}")

        user_data = user_service.update_user(user_id, email=email, name=name, password=password)

        current_app.logger.info(f"===> [USER-SERVICE] ✅ User updated: {user_id}")
        response = jsonify(user_data)
        response.status_code = 200
        return response

    except ValidationError as e:
        current_app.logger.warning(f"===> [USER-SERVICE] ⚠️ Validation error: {str(e)}")
        if "already in use" in str(e):
            return conflict(str(e), instance=f"/api/v1/users/{user_id}")
        return bad_request(str(e), instance=f"/api/v1/users/{user_id}")
    except UpstreamError as e:
        current_app.logger.error(f"===> [USER-SERVICE] ❌ Upstream error: {str(e)}")
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Unexpected error: {str(e)}")
        return internal_server_error(str(e))


@users_bp.delete("/<int:user_id>")
@require_auth
def delete_user(user_id: int):
    """Delete a user (requires authentication)"""
    try:
        current_app.logger.info(f"===> [USER-SERVICE] 🗑️ Deleting user: {user_id}")

        user_service.delete_user(user_id)

        current_app.logger.info(f"===> [USER-SERVICE] ✅ User deleted: {user_id}")
        response = jsonify({"message": f"User {user_id} deleted successfully"})
        response.status_code = 204
        return response

    except ValidationError as e:
        current_app.logger.warning(f"===> [USER-SERVICE] ⚠️ Error: {str(e)}")
        return not_found(str(e), instance=f"/api/v1/users/{user_id}")
    except UpstreamError as e:
        current_app.logger.error(f"===> [USER-SERVICE] ❌ Upstream error: {str(e)}")
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Unexpected error: {str(e)}")
        return internal_server_error(str(e))


@users_bp.get("/ping-redis")
def ping_redis():
    """Verify Redis connection"""
    try:
        r = user_service._get_redis_client()
        if r and r.ping():
            return jsonify({"status": "healthy", "message": "Successfully connected to Redis"}), 200
        else:
            return jsonify({"status": "unhealthy", "message": "Could not connect to Redis"}), 500
    except Exception as e:
        return jsonify({"status": "unhealthy", "message": f"Redis error: {str(e)}"}), 500

