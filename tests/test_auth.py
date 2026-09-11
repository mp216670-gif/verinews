from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import UserRole


def test_password_hashing():
    raw_pass = "SecureNewsSecret2026!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongSecret", hashed) is False


def test_jwt_token_generation_and_decoding():
    data = {"sub": "reporter_alice", "role": "reporter"}
    token = create_access_token(data)
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "reporter_alice"
    assert decoded["role"] == "reporter"


def test_user_registration_and_login(client):
    # 1. Register first user (should become ADMIN automatically)
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "superadmin",
            "email": "superadmin@example.com",
            "password": "Password123!",
        },
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["username"] == "superadmin"
    assert user_data["role"] == "admin"

    # 2. Login via JSON endpoint
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "superadmin", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Check /me endpoint with token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "superadmin@example.com"
