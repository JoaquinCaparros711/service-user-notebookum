"""Unit tests for app/utils/errors.py (RFC 9457 error handling)"""

import json
import pytest
from app import create_app
from app.utils.errors import (
    problem_details,
    bad_request,
    not_found,
    internal_server_error,
    conflict,
    unprocessable_entity,
)


@pytest.fixture
def app_context(app):
    """Create application context for tests"""
    with app.app_context():
        yield app


class TestProblemDetails:
    """Tests for problem_details function"""

    def test_problem_details_minimal(self, app_context):
        """Test problem_details with minimal required parameters"""
        response = problem_details(status=400, title="Bad Request")

        assert response.status_code == 400
        assert response.content_type == "application/problem+json"

        data = json.loads(response.data)
        assert data["type"] == "about:blank"
        assert data["title"] == "Bad Request"
        assert data["status"] == 400

    def test_problem_details_with_detail(self, app_context):
        """Test problem_details includes detail when provided"""
        response = problem_details(status=400, title="Bad Request", detail="Invalid email format")

        data = json.loads(response.data)
        assert data["detail"] == "Invalid email format"

    def test_problem_details_with_instance(self, app_context):
        """Test problem_details includes instance when provided"""
        response = problem_details(status=404, title="Not Found", instance="/api/v1/users/123")

        data = json.loads(response.data)
        assert data["instance"] == "/api/v1/users/123"

    def test_problem_details_with_custom_type_uri(self, app_context):
        """Test problem_details includes custom type URI"""
        response = problem_details(
            status=400,
            title="Invalid Request",
            type_uri="https://example.com/errors/invalid-request",
        )

        data = json.loads(response.data)
        assert data["type"] == "https://example.com/errors/invalid-request"

    def test_problem_details_with_additional_fields(self, app_context):
        """Test problem_details includes additional custom fields"""
        response = problem_details(
            status=400,
            title="Validation Error",
            detail="Multiple validation errors occurred",
            errors=[
                {"field": "email", "message": "Invalid format"},
                {"field": "age", "message": "Must be positive"},
            ],
        )

        data = json.loads(response.data)
        assert "errors" in data
        assert len(data["errors"]) == 2
        assert data["errors"][0]["field"] == "email"

    def test_problem_details_content_type(self, app_context):
        """Test problem_details returns correct content type"""
        response = problem_details(status=500, title="Server Error")

        assert response.content_type == "application/problem+json"


class TestBadRequest:
    """Tests for bad_request shortcut function"""

    def test_bad_request_basic(self, app_context):
        """Test bad_request creates 400 error"""
        response = bad_request(detail="Invalid input")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["title"] == "Bad Request"
        assert data["detail"] == "Invalid input"

    def test_bad_request_with_instance(self, app_context):
        """Test bad_request with instance parameter"""
        response = bad_request(detail="Missing required field", instance="/api/v1/users")

        data = json.loads(response.data)
        assert data["instance"] == "/api/v1/users"

    def test_bad_request_with_kwargs(self, app_context):
        """Test bad_request accepts additional keyword arguments"""
        response = bad_request(detail="Validation failed", field="email")

        data = json.loads(response.data)
        assert data["field"] == "email"


class TestNotFound:
    """Tests for not_found shortcut function"""

    def test_not_found_basic(self, app_context):
        """Test not_found creates 404 error"""
        response = not_found(detail="User not found")

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["title"] == "Not Found"
        assert data["detail"] == "User not found"

    def test_not_found_with_instance(self, app_context):
        """Test not_found with instance parameter"""
        response = not_found(detail="Resource does not exist", instance="/api/v1/users/999")

        data = json.loads(response.data)
        assert data["instance"] == "/api/v1/users/999"


class TestInternalServerError:
    """Tests for internal_server_error shortcut function"""

    def test_internal_server_error_basic(self, app_context):
        """Test internal_server_error creates 500 error"""
        response = internal_server_error()

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["title"] == "Internal Server Error"
        assert data["detail"] == "An unexpected error occurred"

    def test_internal_server_error_with_detail(self, app_context):
        """Test internal_server_error with custom detail"""
        response = internal_server_error(detail="Database connection failed")

        data = json.loads(response.data)
        assert data["detail"] == "Database connection failed"


class TestConflict:
    """Tests for conflict shortcut function"""

    def test_conflict_basic(self, app_context):
        """Test conflict creates 409 error"""
        response = conflict(detail="Email already exists")

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data["title"] == "Conflict"
        assert data["detail"] == "Email already exists"


class TestUnprocessableEntity:
    """Tests for unprocessable_entity shortcut function"""

    def test_unprocessable_entity_basic(self, app_context):
        """Test unprocessable_entity creates 422 error"""
        response = unprocessable_entity(detail="Cannot process request")

        assert response.status_code == 422
        data = json.loads(response.data)
        assert data["title"] == "Unprocessable Entity"
        assert data["detail"] == "Cannot process request"


class TestRFC9457Compliance:
    """Tests for RFC 9457 compliance"""

    def test_required_fields_present(self, app_context):
        """Test all RFC 9457 required fields are present"""
        response = problem_details(status=400, title="Test Error")

        data = json.loads(response.data)
        # Required fields according to RFC 9457
        assert "type" in data
        assert "title" in data
        assert "status" in data

    def test_status_matches_http_code(self, app_context):
        """Test status field matches HTTP status code"""
        test_cases = [
            (bad_request("test"), 400),
            (not_found("test"), 404),
            (internal_server_error("test"), 500),
            (conflict("test"), 409),
            (unprocessable_entity("test"), 422),
        ]

        for response, expected_status in test_cases:
            assert response.status_code == expected_status
            data = json.loads(response.data)
            assert data["status"] == expected_status

    def test_optional_fields_omitted_when_not_provided(self, app_context):
        """Test optional fields are not included when not provided"""
        response = problem_details(status=400, title="Test")

        data = json.loads(response.data)
        # detail and instance are optional and should not be present
        assert "detail" not in data or data["detail"] is None
        assert "instance" not in data
