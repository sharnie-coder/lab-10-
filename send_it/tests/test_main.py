from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    # Checks that the root route returns the HTML portfolio title
    assert "Backend Development Portfolio" in response.text