import json
import logging
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Order


logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_REQUEST_TIMEOUT = 10


def schedule_order_notification(order):
    transaction.on_commit(lambda: send_new_order_notification(order.pk))
    transaction.on_commit(lambda: send_new_order_telegram_notification(order.pk))


def send_new_order_notification(order_id):
    try:
        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .prefetch_related("items")
                .get(pk=order_id)
            )
            if order.notification_email_sent_at:
                return False

            recipient = getattr(settings, "ORDER_NOTIFICATION_EMAIL", "")
            if not recipient:
                logger.warning("Order notification email skipped for order %s: recipient is not configured.", order.order_number)
                return False

            send_mail(
                subject=f"Nouvelle commande VELQARO #{order.order_number}",
                message=build_order_notification_body(order),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient],
                fail_silently=False,
            )

            order.notification_email_sent_at = timezone.now()
            order.save(update_fields=["notification_email_sent_at", "updated_at"])
            return True
    except Exception:
        logger.exception("Failed to send order notification email for order id %s.", order_id)
        return False


def send_new_order_telegram_notification(order_id):
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            if order.telegram_notification_sent_at:
                return False

            bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
            chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
            if not bot_token or not chat_id:
                logger.warning("Telegram order notification skipped for order %s: bot token or chat id is not configured.", order.order_number)
                return False

            payload = json.dumps(
                {"chat_id": chat_id, "text": build_order_telegram_message(order)}
            ).encode("utf-8")
            request = Request(
                TELEGRAM_API_URL.format(token=bot_token),
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=TELEGRAM_REQUEST_TIMEOUT):
                pass

            order.telegram_notification_sent_at = timezone.now()
            order.save(update_fields=["telegram_notification_sent_at", "updated_at"])
            return True
    except Exception:
        logger.exception("Failed to send Telegram notification for order id %s.", order_id)
        return False


def build_order_telegram_message(order):
    return (
        f"Nouvelle commande VELQARO #{order.order_number}\n"
        f"Client: {order.full_name}\n"
        f"Telephone: {order.phone}\n"
        f"Ville: {order.city}\n"
        f"Total: {order.total} DH"
    )


def build_order_notification_body(order):
    ordered_products = "\n".join(
        f"- {item.product_name} x {item.quantity} | Unit price: {item.unit_price} DH | Subtotal: {item.subtotal} DH"
        for item in order.items.all()
    )
    order_date = timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M")
    return (
        f"Order number: {order.order_number}\n"
        f"Customer full name: {order.full_name}\n"
        f"Phone number: {order.phone}\n"
        f"City: {order.city}\n"
        f"Full address: {order.address}\n"
        f"Ordered products with quantities:\n{ordered_products}\n"
        f"Total amount: {order.total} DH\n"
        f"Order date: {order_date}\n"
    )
