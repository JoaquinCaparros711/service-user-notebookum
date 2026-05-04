"""Contract tests for POST /api/v1/users endpoint"""

import pytest

@pytest.mark.contract
class TestPostUsers:
    """Contract tests for POST /api/v1/users"""

    def test_create_user_success(self, client, mocker):
        """Test successful user creation with valid data"""
        mock_response = mocker.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 1,
            "email": "test@example.com",
            "nombre": "Test User",
            "created_at": "2023-01-01",
            "updated_at": "2023-01-01"
        }
        mocker.patch("requests.post", return_value=mock_response)

        user_data = {
            "email": "test@example.com",
            "nombre": "Test User"
        }

        response = client.post("/api/v1/users", json=user_data)
        assert response.status_code == 201
        
        data = response.get_json()
        assert data is not None
        assert "id" in data
        assert data["email"] == "test@example.com"
        assert data["nombre"] == "Test User"

    def test_create_user_missing_email(self, client):
        """Test user creation fails when email is missing (no upstream call expected)"""
        user_data = {"nombre": "Test User"}
        response = client.post("/api/v1/users", json=user_data)

        assert response.status_code == 400
        data = response.get_json()
        assert data is not None
        assert data["type"] == "about:blank"
        assert data["title"] == "Bad Request"
        assert data["status"] == 400
        assert "email" in data["detail"].lower()
        
    def test_create_user_missing_nombre(self, client):
        """Test user creation fails when nombre is missing"""
        user_data = {"email": "test@example.com"}
        response = client.post("/api/v1/users", json=user_data)

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == 400
        assert "nombre" in data["detail"].lower()

    def test_create_user_duplicate_email(self, client, mocker):
        """Test user creation fails when email already exists upstream"""
        mock_response = mocker.Mock()
        mock_response.status_code = 409
        mocker.patch("requests.post", return_value=mock_response)

        duplicate_user = {
            "email": "duplicate@example.com",
            "nombre": "Duplicate User"
        }
        response2 = client.post("/api/v1/users", json=duplicate_user)

        assert response2.status_code == 409
        data = response2.get_json()
        assert data is not None
        assert data["title"] == "Conflict"
        assert data["status"] == 409
        assert "duplicate@example.com" in data["detail"]


@pytest.mark.contract
class TestGetUsers:
    """Contract tests for GET /api/v1/users/{id}"""

    def test_get_user_success(self, client, mocker):
        """Test successful user retrieval"""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "email": "get_test@example.com",
            "nombre": "Get Test User"
        }
        mocker.patch("requests.get", return_value=mock_response)

        response = client.get("/api/v1/users/1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == 1
        assert data["email"] == "get_test@example.com"

    def test_get_user_not_found(self, client, mocker):
        """Test user retrieval fails when user does not exist upstream"""
        mock_response = mocker.Mock()
        mock_response.status_code = 404
        mocker.patch("requests.get", return_value=mock_response)

        response = client.get("/api/v1/users/99999")

        assert response.status_code == 404
        data = response.get_json()
        assert data["title"] == "Not Found"
        assert data["status"] == 404


@pytest.mark.contract
class TestRFC9457Compliance:
    """Tests to verify RFC 9457 Problem Details compliance"""

    def test_error_response_content_type_bad_request(self, client):
        """Test that error responses have application/problem+json content-type"""
        user_data = {"nombre": "Test User"}
        response = client.post("/api/v1/users", json=user_data)
        assert response.content_type == "application/problem+json"
        assert response.status_code == 400

    def test_error_response_content_type_not_found(self, client, mocker):
        """Test that not found errors have application/problem+json content-type"""
        mock_response = mocker.Mock()
        mock_response.status_code = 404
        mocker.patch("requests.get", return_value=mock_response)

        response = client.get("/api/v1/users/99999")
        assert response.content_type == "application/problem+json"
        assert response.status_code == 404
