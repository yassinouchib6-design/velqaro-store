import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Order


logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_REQUEST_TIMEOUT = 10
TELEGRAM_ERROR_BODY_LIMIT = 500


def schedule_order_notification(order):
    order_id = order.pk

    def send_email_after_commit():
        return send_new_order_notification(order_id)

    def send_telegram_after_commit():
        return send_new_order_telegram_notification(order_id)

    transaction.on_commit(send_email_after_commit)
    transaction.on_commit(send_telegram_after_commit)


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
                subject=f"Nouvelle commande {settings.STORE_NAME} #{order.order_number}",
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

            sent = send_telegram_message(
                build_order_telegram_message(order),
                context=f"order {order.order_number}",
            )
            if not sent:
                return False

            order.telegram_notification_sent_at = timezone.now()
            order.save(update_fields=["telegram_notification_sent_at", "updated_at"])
            return True
    except Exception:
        logger.exception("Failed to send Telegram notification for order id %s.", order_id)
        return False


def send_telegram_message(text, context="manual test"):
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
    logger.info(
        "Telegram notification started for %s. token_configured=%s chat_id_configured=%s",
        context,
        bool(bot_token),
        bool(chat_id),
    )
    if not bot_token or not chat_id:
        logger.warning(
            "Telegram notification skipped for %s: bot token or chat id is not configured.",
            context,
        )
        return False

    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = Request(
        TELEGRAM_API_URL.format(token=bot_token),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=TELEGRAM_REQUEST_TIMEOUT) as response:
            status_code = _response_status_code(response)
            response_body = _read_response_text(response)
    except HTTPError as error:
        response_body = _read_error_text(error)
        logger.error(
            "Telegram notification failed for %s: status_code=%s error=%s",
            context,
            error.code,
            _telegram_error_message(response_body),
        )
        return False
    except TimeoutError:
        logger.exception(
            "Telegram notification failed for %s: request timed out after %s seconds.",
            context,
            TELEGRAM_REQUEST_TIMEOUT,
        )
        return False
    except URLError as error:
        logger.exception(
            "Telegram notification failed for %s: network_error=%s",
            context,
            _safe_error_text(error.reason),
        )
        return False
    except OSError as error:
        logger.exception(
            "Telegram notification failed for %s: network_error=%s",
            context,
            _safe_error_text(error),
        )
        return False

    if response_body:
        try:
            api_response = json.loads(response_body)
        except json.JSONDecodeError:
            api_response = {}
        if api_response.get("ok") is False:
            logger.error(
                "Telegram notification failed for %s: status_code=%s error=%s",
                context,
                status_code,
                _telegram_error_message(response_body),
            )
            return False

    logger.info(
        "Telegram notification succeeded for %s: status_code=%s",
        context,
        status_code,
    )
    return True


def _response_status_code(response):
    status_code = getattr(response, "status", None)
    if isinstance(status_code, int):
        return status_code
    getcode = getattr(response, "getcode", None)
    if callable(getcode):
        status_code = getcode()
        if isinstance(status_code, int):
            return status_code
    return 200


def _read_response_text(response):
    read = getattr(response, "read", None)
    if not callable(read):
        return ""
    body = read()
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")[:TELEGRAM_ERROR_BODY_LIMIT]
    if isinstance(body, str):
        return body[:TELEGRAM_ERROR_BODY_LIMIT]
    return ""


def _read_error_text(error):
    try:
        return error.read().decode("utf-8", errors="replace")[:TELEGRAM_ERROR_BODY_LIMIT]
    except Exception:
        return ""


def _telegram_error_message(response_body):
    try:
        data = json.loads(response_body)
    except json.JSONDecodeError:
        return response_body[:TELEGRAM_ERROR_BODY_LIMIT] or "No response body"
    return _safe_error_text(data.get("description") or data)


def _safe_error_text(error):
    return str(error).replace("\n", " ")[:TELEGRAM_ERROR_BODY_LIMIT]


def build_order_telegram_message(order):
    return (
        f"Nouvelle commande {settings.STORE_NAME} #{order.order_number}\n"
        f"Client: {order.full_name}\n"
        f"Telephone: {order.phone}\n"
        f"Ville: {order.city}\n"
        f"Livraison : {settings.STORE_FREE_DELIVERY_LABEL}\n"
        f"Total: {order.total} {settings.STORE_CURRENCY_LABEL}"
    )


def build_order_notification_body(order):
    ordered_products = "\n".join(
        f"- {item.product_name} x {item.quantity} | Unit price: {item.unit_price} {settings.STORE_CURRENCY_LABEL} | Subtotal: {item.subtotal} {settings.STORE_CURRENCY_LABEL}"
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
        f"Livraison : {settings.STORE_FREE_DELIVERY_LABEL}\n"
        f"Total amount: {order.total} {settings.STORE_CURRENCY_LABEL}\n"
        f"Order date: {order_date}\n"
    )
