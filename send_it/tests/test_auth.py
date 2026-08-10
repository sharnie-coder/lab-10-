
def test_register_success(client):
    user_data = {
        "username": "testuser456",
        "email": "testuser456@example.com",
        "password": "password123",
        "full_name": "Test User",
        "role": "staff"
    }

    response = client.post("/register", json=user_data)

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 200


def test_register_duplicate_email(client):
    user_data = {
        "username": "duplicateuser",
        "email": "duplicate@example.com",
        "password": "password123",
        "full_name": "Duplicate User",
        "role": "staff"
    }

    # First registration
    response1 = client.post("/register", json=user_data)
    assert response1.status_code == 200

    # Try registering the same email again
    user_data["username"] = "differentuser"

    response2 = client.post("/register", json=user_data)

    print("STATUS:", response2.status_code)
    print("RESPONSE:", response2.text)

    assert response2.status_code == 400


def test_register_invalid_data(client):
    user_data = {
        "username": "ab",
        "email": "invalid-email",
        "password": "123",
        "full_name": "A",
        "role": "staff"
    }

    response = client.post("/register", json=user_data)

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 422


def test_login_success(client):
    # Register a user first
    user_data = {
        "username": "loginuser",
        "email": "loginuser@example.com",
        "password": "password123",
        "full_name": "Login User",
        "role": "staff"
    }

    register_response = client.post("/register", json=user_data)

    print("REGISTER STATUS:", register_response.status_code)
    print("REGISTER RESPONSE:", register_response.text)

    assert register_response.status_code == 200

    # Login
    login_data = {
        "username": "loginuser",
        "password": "password123"
    }

    response = client.post("/login", data=login_data)

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    # Include response body if the test fails
    assert response.status_code == 200, response.text

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    # Register a user
    user_data = {
        "username": "wrongpassuser",
        "email": "wrongpass@example.com",
        "password": "password123",
        "full_name": "Wrong Password User",
        "role": "staff"
    }

    register_response = client.post("/register", json=user_data)

    print("REGISTER STATUS:", register_response.status_code)
    print("REGISTER RESPONSE:", register_response.text)

    assert register_response.status_code == 200

    # Try to login with the wrong password
    login_data = {
        "username": "wrongpassuser",
        "password": "wrongpassword"
    }

    response = client.post("/login", data=login_data)

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 401




