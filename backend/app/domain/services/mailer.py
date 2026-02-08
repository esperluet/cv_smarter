from typing import Protocol


class Mailer(Protocol):
    def send_welcome_email(self, to_email: str, first_name: str | None) -> None:
        ...
