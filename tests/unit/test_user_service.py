"""Unit tests for UserService"""

import pytest
import requests
import json
from app.services.user_service import UserService, ValidationError, UpstreamError

@pytest.fixture(autouse=True)
def mock_redis(mocker):
    """Automatically mock Redis client for all unit tests"""
    mock_client = mocker.Mock()
    mocker.patch("app.services.user_service.UserService._get_redis_client", return_value=mock_client)
    return mock_client

@pytest.mark.unit
class TestUserServiceValidation:
    """Tests for UserService.validate_user_data"""

    def test_validate_user_data_success(self):
        """Test validation with valid data"""
        data = {"email": "test@example.com", "name": "Test User"}
        result = UserService.validate_user_data(data)
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"

    def test_validate_user_data_missing_email(self):
        """Test validation when email is missing"""
        data = {"name": "Test User"}
        with pytest.raises(ValidationError) as exc:
            UserService.validate_user_data(data)
        assert "email is required" in str(exc.value).lower()

    def test_validate_user_data_missing_name(self):
        """Test validation when name is missing"""
        data = {"email": "test@example.com"}
        with pytest.raises(ValidationError) as exc:
            UserService.validate_user_data(data)
        assert "name is required" in str(exc.value).lower()

    def test_validate_user_data_invalid_email(self):
        """Test validation with invalid email formats"""
        invalid_emails = ["test", "test@", "@example.com", "test@example", "test.example.com"]
        for email in invalid_emails:
            data = {"email": email, "name": "Test User"}
            with pytest.raises(ValidationError) as exc:
                UserService.validate_user_data(data)
            assert "email format is invalid" in str(exc.value).lower()

    def test_validate_user_data_name_too_short(self):
        """Test validation when name is too short"""
        data = {"email": "test@example.com", "name": "A"}
        with pytest.raises(ValidationError) as exc:
            UserService.validate_user_data(data)
        assert "must be at least 2 characters" in str(exc.value).lower()


@pytest.mark.unit
class TestUserServiceCreateUser:
    """Tests for UserService.create_user"""

    def test_create_user_success(self, app, mocker, mock_redis):
        """Test successful user creation via requests and write-through cache"""
        mock_response = mocker.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 1,
            "email": "create@example.com",
            "name": "Create User",
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
            json={"email": "create@example.com", "name": "Create User"},
            timeout=5,
            verify=False
        )
        # Check write-through caching in Redis
        mock_redis.setex.assert_called_once_with("user:1", 300, json.dumps(result))

    def test_create_user_duplicate_email(self, app, mocker):
        """Test user creation fails when email already exists"""
        mock_response = mocker.Mock()
        mock_response.status_code = 409
        mocker.patch("requests.post", return_value=mock_response)

        with app.app_context():
            with pytest.raises(ValidationError) as exc:
                UserService.create_user("duplicate@example.com", "Duplicate User")

        assert "already exists" in str(exc.value).lower()

    def test_create_user_upstream_error(self, app, mocker):
        """Test handling of upstream service errors"""
        mocker.patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused"))

        with app.app_context():
            with pytest.raises(UpstreamError) as exc:
                UserService.create_user("test@example.com", "Test")
                
        assert "failed to connect" in str(exc.value).lower()
        assert exc.value.status_code == 503


@pytest.mark.unit
class TestUserServiceGetUserById:
    """Tests for UserService.get_user_by_id"""

    def test_get_user_by_id_cache_hit(self, app, mock_redis, mocker):
        """Test user retrieval from Redis cache directly (cache hit)"""
        user_data = {
            "id": 1,
            "email": "cached@example.com",
            "name": "Cached User"
        }
        mock_redis.get.return_value = json.dumps(user_data)
        mock_get = mocker.patch("requests.get")

        with app.app_context():
            result = UserService.get_user_by_id(1)

        assert result == user_data
        mock_redis.get.assert_called_once_with("user:1")
        mock_get.assert_not_called()  # Verifies we bypassed DB/persistence completely

    def test_get_user_by_id_cache_miss(self, app, mock_redis, mocker):
        """Test user retrieval from persistence on cache miss and saving to Redis"""
        mock_redis.get.return_value = None  # Cache miss
        
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "email": "get@example.com",
            "name": "Get User"
        }
        mock_get = mocker.patch("requests.get", return_value=mock_response)

        with app.app_context():
            result = UserService.get_user_by_id(1)

        assert result["id"] == 1
        assert result["email"] == "get@example.com"
        mock_get.assert_called_once_with("http://persistence:5003/api/v1/db/users/1", timeout=5)
        # Verify it was saved to Redis
        mock_redis.setex.assert_called_once_with("user:1", 300, json.dumps(result))

    def test_get_user_by_id_not_found(self, app, mock_redis, mocker):
        """Test user retrieval when not found"""
        mock_redis.get.return_value = None
        mock_response = mocker.Mock()
        mock_response.status_code = 404
        mocker.patch("requests.get", return_value=mock_response)

        with app.app_context():
            result = UserService.get_user_by_id(999)

        assert result is None
