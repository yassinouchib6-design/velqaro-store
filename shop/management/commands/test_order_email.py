import smtplib
import socket

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a safe SMTP test email to ORDER_NOTIFICATION_EMAIL."

    def handle(self, *args, **options):
        missing = [
            name
            for name in ("EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "ORDER_NOTIFICATION_EMAIL")
            if not getattr(settings, name, "")
        ]
        if missing:
            raise CommandError(
                "Missing required email environment variable(s): "
                + ", ".join(missing)
            )

        try:
            sent = send_mail(
                subject="Test email VELQARO",
                message="This is a VELQARO order notification SMTP test.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ORDER_NOTIFICATION_EMAIL],
                fail_silently=False,
            )
        except smtplib.SMTPAuthenticationError as error:
            raise CommandError(
                "SMTP authentication failed. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD."
            ) from error
        except (smtplib.SMTPConnectError, socket.timeout, OSError) as error:
            raise CommandError(
                "SMTP connection failed. Check network access, EMAIL_HOST, EMAIL_PORT, TLS/SSL settings."
            ) from error
        except smtplib.SMTPException as error:
            raise CommandError(f"SMTP error: {error.__class__.__name__}") from error

        if sent != 1:
            raise CommandError("SMTP test did not send exactly one email.")

        self.stdout.write(self.style.SUCCESS("SMTP test email sent successfully."))
