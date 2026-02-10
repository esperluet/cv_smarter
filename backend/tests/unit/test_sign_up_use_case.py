from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.application.errors import EmailAlreadyExistsError
from app.application.use_cases.auth.sign_up import SignUpUseCase
from app.domain.repositories.auth_registration_repository import DuplicateEmailError
from app.domain.models.user import User


class FakeRegistrationRepository:
    def __init__(self, should_raise_duplicate: bool = False) -> None:
        self.should_raise_duplicate = should_raise_duplicate
        now = datetime.now(timezone.utc)
        self.created_user = User(
            id="u1",
            email="john@example.com",
            password_hash="hashed",
            first_name="John",
            last_name="Doe",
            role="user",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def register_user_with_refresh_session(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str | None,
        last_name: str | None,
        refresh_token_hash: str,
        refresh_expires_at,
    ):
        if self.should_raise_duplicate:
            raise DuplicateEmailError("Email is already registered")
        self.created_user = replace(
            self.created_user,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )
        return self.created_user


class FakePasswordHasher:
    def hash(self, plain_password: str) -> str:
        return f"hashed-{plain_password}"


class FakeTokenService:
    def create_access_token(self, user_id: str, role: str):
        return ("access-token", datetime.now(timezone.utc))

    def generate_refresh_token(self) -> str:
        return "refresh-token"

    def hash_refresh_token(self, refresh_token: str) -> str:
        return f"hash-{refresh_token}"


class FakeMailer:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.sent_to: list[str] = []

    def send_welcome_email(self, to_email: str, first_name: str | None) -> None:
        if self.should_fail:
            raise RuntimeError("smtp down")
        self.sent_to.append(to_email)


def test_sign_up_sends_welcome_email() -> None:
    registration = FakeRegistrationRepository()
    mailer = FakeMailer()

    use_case = SignUpUseCase(
        registration=registration,
        password_hasher=FakePasswordHasher(),
        token_service=FakeTokenService(),
        mailer=mailer,
        refresh_token_expire_days=7,
        access_token_expire_minutes=15,
    )

    result = use_case.execute(
        email="John@Example.com",
        password="strong-password",
        first_name="John",
        last_name="Doe",
    )

    assert result.access_token == "access-token"
    assert registration.created_user.email == "john@example.com"
    assert mailer.sent_to == ["john@example.com"]


def test_sign_up_does_not_fail_if_mailer_fails() -> None:
    use_case = SignUpUseCase(
        registration=FakeRegistrationRepository(),
        password_hasher=FakePasswordHasher(),
        token_service=FakeTokenService(),
        mailer=FakeMailer(should_fail=True),
        refresh_token_expire_days=7,
        access_token_expire_minutes=15,
    )

    result = use_case.execute(
        email="john@example.com",
        password="strong-password",
        first_name="John",
        last_name="Doe",
    )

    assert result.refresh_token == "refresh-token"


def test_sign_up_maps_duplicate_email_to_application_error() -> None:
    use_case = SignUpUseCase(
        registration=FakeRegistrationRepository(should_raise_duplicate=True),
        password_hasher=FakePasswordHasher(),
        token_service=FakeTokenService(),
        mailer=FakeMailer(),
        refresh_token_expire_days=7,
        access_token_expire_minutes=15,
    )

    with pytest.raises(EmailAlreadyExistsError):
        use_case.execute(
            email="john@example.com",
            password="strong-password",
            first_name="John",
            last_name="Doe",
        )
