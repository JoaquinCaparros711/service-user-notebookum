"""Unit tests for UserService"""

import pytest
import requests
from app.services.user_service import UserService, ValidationError, UpstreamError

@pytest.mark.unit
class TestUserServiceValidation:
    """Tests for UserService.validate_user_data"""

    def test_validate_user_data_success(self):
        """Test validation with valid data"""
        data = {"email": "test@example.com", "nombre": "Test User"}
        result = UserService.validate_user_data(data)
        assert result["email"] == "test@example.com"
        assert result["nombre"] == "Test User"

    def test_validate_user_data_missing_email(self):
        """Test validation when email is missing"""
        data = {"nombre": "Test User"}
        with pytest.raises(ValidationError) as exc:
            UserService.validate_user_data(data)
        assert "email is required" in str(exc.value).lower()

    def test_validate_user_data_missing_nombre(self):
        """Test validation when nombre is missing"""
        data = {"email": "test@example.com"}
        with pytest.raises(ValidationError) as exc:
            UserService.validate_user_data(data)
        assert "name (nombre) is required" in str(exc.value).lower()

    def test_validate_user_data_invalid_email(self):
        """Test validation with invalid email formats"""
        invalid_emails = ["test", "test@", "@example.com", "test@example", "test.example.com"]
        for email in invalid_emails:
            data = {"email": email, "nombre": "Test User"}
            with pytest.raises(ValidationError) as exc:
                UserService.validate_user_data(data)
            assert "email format is invalid" in str(exc.value).lower()

    def test_validate_user_data_nombre_too_short(self):
        """Test validation when nombre is too short"""
        data = {"email": "test@example.com", "nombre": "A"}
        with pytest.raises(ValidationError) as exc:
            UserService.validate_user_data(data)
        assert "must be at least 2 characters" in str(exc.value).lower()


@pytest.mark.unit
class TestUserServiceCreateUser:
    """Tests for UserService.create_user"""

    def test_create_user_success(self, app, mocker):
        """Test successful user creation via requests"""
        mock_response = mocker.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 1,
            "email": "create@example.com",
            "nombre": "Create User",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        mock_post = mocker.patch("requests.post", return_value=mock_response)

        with app.app_context():
            result = UserService.create_user("create@example.com", "Create User")

        assert result["id"] == 1
        assert result["email"] == "create@example.com"
        mock_post.assert_called_once_with(
            "http://persistence:5003/api/v1/db/users",
            json={"email": "create@example.com", "nombre": "Create User"},
            timeout=5
        )

    def test_create_user_duplicate_email(self, app, mocker):
        """Test user creation fails when email already exists"""
        mock_response = mocker.Mock()
        mock_response.status_code = 409
        mock_post = mocker.patch("requests.post", return_value=mock_response)

        with app.app_context():
            with pytest.raises(ValidationError) as exc:
                UserService.create_user("duplicate@example.com", "Duplicate User")

        assert "already exists" in str(exc.value).lower()

    def test_create_user_upstream_error(self, app, mocker):
        """Test handling of upstream service errors"""
        mock_post = mocker.patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused"))

        with app.app_context():
            with pytest.raises(UpstreamError) as exc:
                UserService.create_user("test@example.com", "Test")
                
        assert "failed to connect" in str(exc.value).lower()
        assert exc.value.status_code == 503


@pytest.mark.unit
class TestUserServiceGetUserById:
    """Tests for UserService.get_user_by_id"""

    def test_get_user_by_id_success(self, app, mocker):
        """Test successful user retrieval"""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "email": "get@example.com",
            "nombre": "Get User"
        }
        mock_get = mocker.patch("requests.get", return_value=mock_response)

        with app.app_context():
            result = UserService.get_user_by_id(1)

        assert result["id"] == 1
        assert result["email"] == "get@example.com"
        mock_get.assert_called_once_with("http://persistence:5003/api/v1/db/users/1", timeout=5)

    def test_get_user_by_id_not_found(self, app, mocker):
        """Test user retrieval when not found"""
        mock_response = mocker.Mock()
        mock_response.status_code = 404
        mocker.patch("requests.get", return_value=mock_response)

        with app.app_context():
            result = UserService.get_user_by_id(999)

        assert result is None
