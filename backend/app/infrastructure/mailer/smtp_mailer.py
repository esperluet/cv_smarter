import smtplib
from email.message import EmailMessage


class SMTPMailer:
    def __init__(
        self,
        host: str,
        port: int,
        from_email: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._from_email = from_email
        self._username = username
        self._password = password
        self._use_tls = use_tls

    def send_welcome_email(self, to_email: str, first_name: str | None) -> None:
        greeting = first_name.strip() if first_name else "there"
        body = (
            f"Hi {greeting},\\n\\n"
            "Welcome to CV Optimizer. Your account has been created successfully.\\n\\n"
            "Best regards,\\n"
            "CV Optimizer Team"
        )

        message = EmailMessage()
        message["Subject"] = "Welcome to CV Optimizer"
        message["From"] = self._from_email
        message["To"] = to_email
        message.set_content(body)

        with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.send_message(message)
