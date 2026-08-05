from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .admin import ProductAdmin, archive_products, restore_products
from .models import Category, Order, OrderItem, Product
from .notifications import send_new_order_notification, send_new_order_telegram_notification
from .services import create_order_from_cart


@override_settings(
    VELQARO_DELIVERY_FEE="0.00",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="orders@velqaro.test",
    ORDER_NOTIFICATION_EMAIL="owner@velqaro.test",
    TELEGRAM_BOT_TOKEN="test-bot-token",
    TELEGRAM_CHAT_ID="123456",
)
class ShopCartOrderTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Bracelets", slug="bracelets")
        self.product = Product.objects.create(
            category=self.category,
            name="Bracelet Noir",
            slug="bracelet-noir",
            short_description="Bracelet minimal.",
            description="Bracelet homme.",
            price=Decimal("120.00"),
            material="Steel",
            color="Gunmetal",
            stock=3,
            is_active=True,
        )

    def add_to_cart(self, quantity=1):
        return self.client.post(
            reverse("shop:cart"),
            {
                "action": "add",
                "product_id": self.product.id,
                "quantity": quantity,
            },
        )

    def valid_checkout_payload(self):
        token = self.client.session["checkout_token"]
        return {
            "full_name": "Ali Ben",
            "phone": "0612345678",
            "city": "Casablanca",
            "address": "12 Rue Test",
            "note": "",
            "checkout_token": token,
        }

    def service_checkout_payload(self):
        return {
            "full_name": "Ali Ben",
            "phone": "0612345678",
            "city": "Casablanca",
            "address": "12 Rue Test",
            "note": "",
        }

    def test_add_product_to_cart(self):
        self.add_to_cart(quantity=1)

        session_cart = self.client.session["velqaro_cart"]

        self.assertEqual(session_cart[str(self.product.id)], 1)

    def test_cart_prevents_quantity_above_stock(self):
        self.add_to_cart(quantity=10)

        session_cart = self.client.session["velqaro_cart"]

        self.assertEqual(session_cart[str(self.product.id)], self.product.stock)

    def test_cart_total_is_calculated_from_database_prices(self):
        self.add_to_cart(quantity=2)

        response = self.client.get(reverse("shop:cart"))
        cart = response.context["cart"]

        self.assertEqual(cart.subtotal, Decimal("240.00"))
        self.assertEqual(cart.delivery_fee, Decimal("0.00"))
        self.assertEqual(cart.total, Decimal("240.00"))

    def test_valid_checkout_creates_order(self):
        self.add_to_cart(quantity=2)
        self.client.get(reverse("shop:checkout"))

        response = self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())

        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse("shop:order_success", kwargs={"order_number": order.order_number}),
        )
        self.assertEqual(order.subtotal, Decimal("240.00"))
        self.assertEqual(order.delivery_fee, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("240.00"))
        self.assertEqual(order.items.count(), 1)

    def test_successful_checkout_sends_one_order_notification_email(self):
        self.add_to_cart(quantity=2)
        self.client.get(reverse("shop:checkout"))

        with patch("shop.notifications.urlopen"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())

        order = Order.objects.get()
        order.refresh_from_db()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f"Nouvelle commande VELQARO #{order.order_number}")
        self.assertEqual(mail.outbox[0].to, ["owner@velqaro.test"])
        self.assertIn(order.order_number, mail.outbox[0].body)
        self.assertIn("Ali Ben", mail.outbox[0].body)
        self.assertIn("0612345678", mail.outbox[0].body)
        self.assertIn("Casablanca", mail.outbox[0].body)
        self.assertIn("12 Rue Test", mail.outbox[0].body)
        self.assertIn("Bracelet Noir x 2", mail.outbox[0].body)
        self.assertIn("Unit price: 120.00 DH", mail.outbox[0].body)
        self.assertIn("Livraison : Gratuite", mail.outbox[0].body)
        self.assertIn("240.00 DH", mail.outbox[0].body)
        self.assertIsNotNone(order.notification_email_sent_at)

        sent_again = send_new_order_notification(order.pk)

        self.assertFalse(sent_again)
        self.assertEqual(len(mail.outbox), 1)

    def test_order_notification_is_sent_only_after_transaction_commit(self):
        self.add_to_cart(quantity=1)
        self.client.get(reverse("shop:checkout"))

        with patch("shop.notifications.urlopen"):
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())

            order = Order.objects.get()
            self.assertEqual(len(callbacks), 2)
            self.assertEqual(len(mail.outbox), 0)
            self.assertIsNone(order.notification_email_sent_at)

            for callback in callbacks:
                callback()
            order.refresh_from_db()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIsNotNone(order.notification_email_sent_at)

    def test_email_failure_does_not_block_order_creation(self):
        self.add_to_cart(quantity=1)
        self.client.get(reverse("shop:checkout"))

        with patch("shop.notifications.send_mail", side_effect=RuntimeError("SMTP down")):
            with patch("shop.notifications.urlopen"):
                with self.assertLogs("shop.notifications", level="ERROR"):
                    with self.captureOnCommitCallbacks(execute=True):
                        response = self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())

        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse("shop:order_success", kwargs={"order_number": order.order_number}),
        )
        self.assertIsNone(order.notification_email_sent_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_successful_checkout_sends_one_telegram_notification(self):
        self.add_to_cart(quantity=2)
        self.client.get(reverse("shop:checkout"))

        with patch("shop.notifications.urlopen") as mock_urlopen:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())

        order = Order.objects.get()
        order.refresh_from_db()

        self.assertEqual(mock_urlopen.call_count, 1)
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://api.telegram.org/bottest-bot-token/sendMessage")
        body = request.data.decode("utf-8")
        self.assertIn(order.order_number, body)
        self.assertIn("Ali Ben", body)
        self.assertIn("0612345678", body)
        self.assertIn("Casablanca", body)
        self.assertIn("Livraison : Gratuite", body)
        self.assertIn("240.00 DH", body)
        self.assertIsNotNone(order.telegram_notification_sent_at)

        sent_again = send_new_order_telegram_notification(order.pk)

        self.assertFalse(sent_again)
        self.assertEqual(mock_urlopen.call_count, 1)

    def test_telegram_notification_is_sent_only_after_transaction_commit(self):
        self.add_to_cart(quantity=1)
        self.client.get(reverse("shop:checkout"))

        with patch("shop.notifications.urlopen") as mock_urlopen:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())

            order = Order.objects.get()
            self.assertEqual(mock_urlopen.call_count, 0)
            self.assertIsNone(order.telegram_notification_sent_at)

            for callback in callbacks:
                callback()

        order.refresh_from_db()
        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertIsNotNone(order.telegram_notification_sent_at)

    def test_service_order_registers_telegram_on_commit_callback(self):
        class ServiceCart:
            def __init__(self, product):
                self.product = product

            def as_order_items(self):
                return [
                    {
                        "product": self.product,
                        "quantity": 1,
                        "subtotal": self.product.price,
                    }
                ]

        with patch("shop.notifications.send_telegram_message", return_value=True) as mock_sender:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                order = create_order_from_cart(
                    ServiceCart(self.product),
                    self.service_checkout_payload(),
                )

            self.assertEqual(len(callbacks), 2)
            self.assertEqual(mock_sender.call_count, 0)

            for callback in callbacks:
                callback()

        order.refresh_from_db()
        self.assertEqual(mock_sender.call_count, 1)
        self.assertIsNotNone(order.telegram_notification_sent_at)

    def test_telegram_failure_does_not_block_order_creation(self):
        self.add_to_cart(quantity=1)
        self.client.get(reverse("shop:checkout"))

        with patch("shop.notifications.urlopen", side_effect=OSError("Telegram unreachable")):
            with self.assertLogs("shop.notifications", level="ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())

        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse("shop:order_success", kwargs={"order_number": order.order_number}),
        )
        self.assertIsNone(order.telegram_notification_sent_at)

    def test_order_number_is_generated(self):
        order = Order.objects.create(
            full_name="Ali Ben",
            phone="0612345678",
            city="Casablanca",
            address="12 Rue Test",
            subtotal=Decimal("120.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("120.00"),
        )

        self.assertRegex(order.order_number, r"^VEL-\d{6}$")

    def test_stock_decreases_once_after_checkout(self):
        self.add_to_cart(quantity=1)
        self.client.get(reverse("shop:checkout"))
        payload = self.valid_checkout_payload()

        self.client.post(reverse("shop:checkout"), payload)
        self.client.post(reverse("shop:checkout"), payload)
        self.product.refresh_from_db()

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.product.stock, 2)
        self.assertNotIn("velqaro_cart", self.client.session)

    def test_checkout_rejects_empty_cart(self):
        response = self.client.get(reverse("shop:checkout"))

        self.assertRedirects(response, reverse("shop:cart"))
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_rejects_insufficient_stock(self):
        self.add_to_cart(quantity=3)
        self.client.get(reverse("shop:checkout"))
        self.product.stock = 1
        self.product.save(update_fields=["stock"])

        response = self.client.post(reverse("shop:checkout"), self.valid_checkout_payload())
        self.product.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stock insuffisant")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.product.stock, 1)


class ProductArchiveTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Bracelets", slug="bracelets")
        self.product = Product.objects.create(
            category=self.category,
            name="Bracelet Noir",
            slug="bracelet-noir",
            short_description="Bracelet minimal.",
            description="Bracelet homme.",
            price=Decimal("120.00"),
            material="Steel",
            color="Gunmetal",
            stock=3,
            is_active=True,
            is_featured=True,
        )
        self.admin = ProductAdmin(Product, admin.site)

    def _admin_request(self, user=None):
        request = RequestFactory().get("/admin/shop/product/")
        request.session = {}
        request._messages = FallbackStorage(request)
        request.user = user
        return request

    def test_archive_action_hides_product_from_storefront(self):
        response = self.client.get(reverse("shop:product_list"))
        self.assertContains(response, "Bracelet Noir")

        archive_products(self.admin, self._admin_request(), Product.objects.filter(pk=self.product.pk))
        self.product.refresh_from_db()

        self.assertFalse(self.product.is_active)
        self.assertFalse(self.product.is_featured)

        response = self.client.get(reverse("shop:product_list"))
        self.assertNotContains(response, "Bracelet Noir")
        self.assertEqual(
            self.client.get(reverse("shop:product_detail", args=[self.product.slug])).status_code,
            404,
        )

    def test_restore_action_shows_product_on_storefront_again(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        restore_products(self.admin, self._admin_request(), Product.objects.filter(pk=self.product.pk))
        self.product.refresh_from_db()

        self.assertTrue(self.product.is_active)
        response = self.client.get(reverse("shop:product_list"))
        self.assertContains(response, "Bracelet Noir")

    def test_admin_still_shows_archived_products(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        self.assertIn(self.product, Product.objects.all())

    def test_cannot_delete_product_referenced_by_order_items(self):
        order = Order.objects.create(
            full_name="Ali Ben",
            phone="0612345678",
            city="Casablanca",
            address="12 Rue Test",
            subtotal=Decimal("120.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("120.00"),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1,
            subtotal=self.product.price,
        )

        self.assertFalse(self.admin.has_delete_permission(self._admin_request(), obj=self.product))

    def test_can_delete_product_with_no_order_history(self):
        User = get_user_model()
        superuser = User.objects.create_superuser(
            username="owner", email="owner@velqaro.test", password="pass1234"
        )

        self.assertTrue(
            self.admin.has_delete_permission(self._admin_request(user=superuser), obj=self.product)
        )
