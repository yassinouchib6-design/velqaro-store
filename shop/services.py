from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from .models import Order, OrderItem, Product
from .notifications import schedule_order_notification


def get_delivery_fee():
    return Decimal(str(getattr(settings, "VELQARO_DELIVERY_FEE", "0.00")))


@transaction.atomic
def create_order_from_cart(cart, cleaned_data):
    cart_items = cart.as_order_items()
    if not cart_items:
        raise ValidationError("La commande ne peut pas etre vide.")

    product_ids = [item["product"].id for item in cart_items]
    locked_products = Product.objects.select_for_update().filter(
        id__in=product_ids,
        is_active=True,
    )
    product_map = {product.id: product for product in locked_products}

    subtotal = Decimal("0.00")
    checked_items = []
    for item in cart_items:
        product = product_map.get(item["product"].id)
        quantity = item["quantity"]
        if not product:
            raise ValidationError("Un produit dans votre panier n'est plus disponible.")
        if quantity > product.stock:
            raise ValidationError(f"Stock insuffisant pour {product.name}.")
        item_subtotal = product.price * quantity
        subtotal += item_subtotal
        checked_items.append((product, quantity, item_subtotal))

    delivery_fee = get_delivery_fee()
    order = Order.objects.create(
        full_name=cleaned_data["full_name"],
        phone=cleaned_data["phone"],
        city=cleaned_data["city"],
        address=cleaned_data["address"],
        note=cleaned_data.get("note", ""),
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=subtotal + delivery_fee,
    )

    for product, quantity, item_subtotal in checked_items:
        updated = Product.objects.filter(pk=product.pk, stock__gte=quantity).update(
            stock=F("stock") - quantity
        )
        if updated != 1:
            raise ValidationError(f"Stock insuffisant pour {product.name}.")
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=product.price,
            quantity=quantity,
            subtotal=item_subtotal,
        )

    schedule_order_notification(order)
    return order
