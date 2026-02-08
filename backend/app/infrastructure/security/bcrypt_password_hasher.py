import base64
import hashlib
import hmac
import secrets


class PBKDF2PasswordHasher:
    def __init__(self, iterations: int = 390_000) -> None:
        self._iterations = iterations

    def hash(self, plain_password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, self._iterations)

        salt_b64 = base64.b64encode(salt).decode("ascii")
        digest_b64 = base64.b64encode(digest).decode("ascii")
        return f"pbkdf2_sha256${self._iterations}${salt_b64}${digest_b64}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            algorithm, iterations_str, salt_b64, digest_b64 = hashed_password.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False

            iterations = int(iterations_str)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected_digest = base64.b64decode(digest_b64.encode("ascii"))
        except (ValueError, TypeError):
            return False

        computed_digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(computed_digest, expected_digest)
