from app.services.auth_service import hash_password, verify_password, user_id_from_token, create_access_token


def test_password_roundtrip():
    hashed = hash_password("correct-horse")
    assert verify_password("correct-horse", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token(user_id=42, email="a@b.com")
    assert user_id_from_token(token) == 42
