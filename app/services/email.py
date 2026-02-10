import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_email: str,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email

    async def send_verification_email(
        self, to_email: str, username: str, token: str, base_url: str
    ) -> None:
        verify_url = f"{base_url}/auth/verify?token={token}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your PDF Processor account"
        msg["From"] = self.from_email
        msg["To"] = to_email

        text = (
            f"Hi {username},\n\n"
            f"Please verify your account by visiting:\n{verify_url}\n\n"
            "If you did not register, please ignore this email."
        )
        html = (
            f"<p>Hi {username},</p>"
            f'<p><a href="{verify_url}">Click here to verify your account</a></p>'
            "<p>If you did not register, please ignore this email.</p>"
        )

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            msg,
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            start_tls=True,
        )
        logger.info("Verification email sent to %s", to_email)
