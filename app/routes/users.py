"""Users API routes"""

from flask import Blueprint, request, jsonify, current_app
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
        name = validated_data["name"]

        current_app.logger.info(f"===> [USER-SERVICE] 👤 Intentando crear usuario - Email: {email}, Nombre: {name}")

        # Create user using UserService
        user_data = UserService.create_user(email, name)

        current_app.logger.info(f"===> [USER-SERVICE] ✅ Usuario creado exitosamente - ID: {user_data.get('id')}, Nombre: {user_data.get('name')} (Recibido por USER-SERVICE)")

        response = jsonify(user_data)
        response.status_code = 201
        return response

    except ValidationError as e:
        current_app.logger.warning(f"===> [USER-SERVICE] ⚠️ Error de validación al crear usuario: {str(e)}")
        # Handle validation errors
        if "already exists" in str(e):
            return conflict(str(e), instance="/api/v1/users")
        return bad_request(str(e), instance="/api/v1/users")
    except UpstreamError as e:
        current_app.logger.error(f"===> [USER-SERVICE] ❌ Error en servicio de persistencia al crear usuario: {str(e)}")
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Error inesperado al crear usuario: {str(e)}")
        return internal_server_error(str(e))


@users_bp.get("/<int:user_id>")
def get_user(user_id: int):
    """Retrieve a user by ID"""
    try:
        current_app.logger.info(f"===> [USER-SERVICE] 🔍 Buscando información de ID de usuario: {user_id}")
        user_data = UserService.get_user_by_id(user_id)

        if not user_data:
            current_app.logger.warning(f"===> [USER-SERVICE] ❌ Usuario con ID {user_id} NO encontrado")
            return not_found(
                f"User with ID {user_id} not found",
                instance=f"/api/v1/users/{user_id}"
            )

        current_app.logger.info(f"===> [USER-SERVICE] ✅ Usuario encontrado: {user_data.get('name')} (Recibido por USER-SERVICE)")
        response = jsonify(user_data)
        response.status_code = 200
        return response
        
    except UpstreamError as e:
        current_app.logger.error(f"===> [USER-SERVICE] ❌ Error en servicio de persistencia al buscar usuario {user_id}: {str(e)}")
        return problem_details(status=e.status_code, title="Upstream Service Error", detail=str(e))
    except Exception as e:
        current_app.logger.error(f"===> [USER-SERVICE] 💥 Error inesperado al buscar usuario {user_id}: {str(e)}")
        return internal_server_error(str(e))


@users_bp.get("/ping-redis")
def ping_redis():
    """Verify Redis connection"""
    try:
        r = UserService._get_redis_client()
        if r and r.ping():
            return jsonify({"status": "healthy", "message": "Successfully connected to Redis"}), 200
        else:
            return jsonify({"status": "unhealthy", "message": "Could not connect to Redis"}), 500
    except Exception as e:
        return jsonify({"status": "unhealthy", "message": f"Redis error: {str(e)}"}), 500

