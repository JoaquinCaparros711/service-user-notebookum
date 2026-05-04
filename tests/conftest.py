"""Pytest configuration and common fixtures."""

import pytest
from app import create_app

class TestConfig:
    TESTING = True
    PERSISTENCE_URL = "http://persistence:5003"
    SECRET_KEY = "test-secret-key"

@pytest.fixture
def app():
    """Create and configure a test application instance"""
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    """Create a test client for the app"""
    return app.test_client()
