import io
from unittest.mock import AsyncMock, patch


# ==========================================================
# HELPER: CREATE AND LOGIN TEST USER
# ==========================================================

def get_auth_headers(client):
    user_data = {
        "username": "documentuser",
        "email": "documentuser@example.com",
        "password": "password123",
        "full_name": "Document User",
        "role": "staff",
    }

    # Register user
    register_response = client.post(
        "/register",
        json=user_data,
    )

    # User may already exist if the test database is reused
    assert register_response.status_code in [200, 201, 400]

    # Login
    login_response = client.post(
        "/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


# ==========================================================
# TEST DOCUMENT UPLOAD - INVALID FILE TYPE
# ==========================================================

@patch(
    "main.get_weather",
    new_callable=AsyncMock,
)
def test_upload_document(mock_weather, client):
    mock_weather.return_value = {
        "temperature": 25,
        "description": "Sunny",
    }

    headers = get_auth_headers(client)

    file_content = b"This is a test document."

    response = client.post(
        "/documents/upload",
        headers=headers,
        files={
            "file": (
                "test.txt",
                io.BytesIO(file_content),
                "text/plain",
            )
        },
        data={
            "city": "Nairobi",
            "country": "Kenya",
            "description": "Test document",
        },
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    # .txt is not allowed by the API
    assert response.status_code == 400


# ==========================================================
# TEST DOCUMENT UPLOAD - SUCCESS
# ==========================================================

@patch(
    "main.get_weather",
    new_callable=AsyncMock,
)
def test_upload_document_success(mock_weather, client):
    mock_weather.return_value = {
        "temperature": 25,
        "description": "Sunny",
    }

    headers = get_auth_headers(client)

    file_content = b"This is a test PDF document."

    response = client.post(
        "/documents/upload",
        headers=headers,
        files={
            "file": (
                "test.pdf",
                io.BytesIO(file_content),
                "application/pdf",
            )
        },
        data={
            "city": "Nairobi",
            "country": "Kenya",
            "description": "Test document",
        },
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 200

    data = response.json()

    assert "document_id" in data
    assert data["status"] in ["uploaded", "enriched"]


# ==========================================================
# TEST LIST DOCUMENTS
# ==========================================================

def test_list_documents(client):
    headers = get_auth_headers(client)

    response = client.get(
        "/documents",
        headers=headers,
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


# ==========================================================
# TEST SEARCH DOCUMENTS
# ==========================================================

@patch(
    "main.get_weather",
    new_callable=AsyncMock,
)
def test_search_documents(mock_weather, client):
    mock_weather.return_value = {
        "temperature": 25,
        "description": "Sunny",
    }

    headers = get_auth_headers(client)

    file_content = b"Searchable document."

    upload_response = client.post(
        "/documents/upload",
        headers=headers,
        files={
            "file": (
                "search_test.pdf",
                io.BytesIO(file_content),
                "application/pdf",
            )
        },
        data={
            "city": "Nairobi",
            "country": "Kenya",
            "description": "Search test",
        },
    )

    print("UPLOAD STATUS:", upload_response.status_code)
    print("UPLOAD RESPONSE:", upload_response.text)

    assert upload_response.status_code == 200

    response = client.get(
        "/documents/search",
        params={"keyword": "search_test"},
        headers=headers,
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


# ==========================================================
# TEST GET ONE DOCUMENT
# ==========================================================

@patch(
    "main.get_weather",
    new_callable=AsyncMock,
)
def test_get_document(mock_weather, client):
    mock_weather.return_value = {
        "temperature": 25,
        "description": "Sunny",
    }

    headers = get_auth_headers(client)

    file_content = b"Get document test."

    upload_response = client.post(
        "/documents/upload",
        headers=headers,
        files={
            "file": (
                "get_test.pdf",
                io.BytesIO(file_content),
                "application/pdf",
            )
        },
        data={
            "city": "Nairobi",
            "country": "Kenya",
            "description": "Get test",
        },
    )

    assert upload_response.status_code == 200

    document_id = upload_response.json()["document_id"]

    response = client.get(
        f"/documents/{document_id}",
        headers=headers,
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == document_id
    assert data["city"] == "Nairobi"


# ==========================================================
# TEST DOCUMENT WEATHER
# ==========================================================

@patch(
    "main.get_weather",
    new_callable=AsyncMock,
)
def test_document_weather(mock_weather, client):
    mock_weather.return_value = {
        "temperature": 25,
        "description": "Sunny",
    }

    headers = get_auth_headers(client)

    file_content = b"Weather test document."

    upload_response = client.post(
        "/documents/upload",
        headers=headers,
        files={
            "file": (
                "weather_test.pdf",
                io.BytesIO(file_content),
                "application/pdf",
            )
        },
        data={
            "city": "Nairobi",
            "country": "Kenya",
            "description": "Weather test",
        },
    )

    assert upload_response.status_code == 200

    document_id = upload_response.json()["document_id"]

    response = client.get(
        f"/documents/{document_id}/weather",
        headers=headers,
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 200

    data = response.json()

    assert data["document_id"] == document_id
    assert data["city"] == "Nairobi"
    assert "weather" in data


# ==========================================================
# TEST DELETE DOCUMENT
# ==========================================================

@patch(
    "main.get_weather",
    new_callable=AsyncMock,
)
def test_delete_document(mock_weather, client):
    mock_weather.return_value = {
        "temperature": 25,
        "description": "Sunny",
    }

    headers = get_auth_headers(client)

    file_content = b"Delete test document."

    upload_response = client.post(
        "/documents/upload",
        headers=headers,
        files={
            "file": (
                "delete_test.pdf",
                io.BytesIO(file_content),
                "application/pdf",
            )
        },
        data={
            "city": "Nairobi",
            "country": "Kenya",
            "description": "Delete test",
        },
    )

    assert upload_response.status_code == 200

    document_id = upload_response.json()["document_id"]

    response = client.delete(
        f"/documents/{document_id}",
        headers=headers,
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Document deleted successfully"

    # Confirm deletion
    get_response = client.get(
        f"/documents/{document_id}",
        headers=headers,
    )

    assert get_response.status_code == 404


# ==========================================================
# TEST DOCUMENT NOT FOUND
# ==========================================================

def test_get_document_not_found(client):
    headers = get_auth_headers(client)

    response = client.get(
        "/documents/99999",
        headers=headers,
    )

    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)

    assert response.status_code == 404
