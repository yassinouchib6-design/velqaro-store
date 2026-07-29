from decimal import Decimal

from django.conf import settings

from .models import Product


class Cart:
    session_key = "velqaro_cart"

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(self.session_key, {})

    def __len__(self):
        return sum(self.cart.values())

    def __iter__(self):
        product_ids = [int(product_id) for product_id in self.cart.keys()]
        products = Product.objects.filter(id__in=product_ids, is_active=True)
        product_map = {product.id: product for product in products}

        for product_id, quantity in list(self.cart.items()):
            product = product_map.get(int(product_id))
            if not product:
                self.remove(product_id)
                continue
            if quantity < 1:
                self.remove(product_id)
                continue
            yield {
                "product": product,
                "quantity": quantity,
                "subtotal": product.price * quantity,
            }

    def add(self, product, quantity=1, override_quantity=False):
        quantity = self._clean_quantity(quantity)
        product_id = str(product.id)
        current_quantity = self.cart.get(product_id, 0)
        new_quantity = quantity if override_quantity else current_quantity + quantity
        self.cart[product_id] = min(new_quantity, product.stock)
        self.save()

    def update(self, product, quantity):
        quantity = self._clean_quantity(quantity)
        self.cart[str(product.id)] = min(quantity, product.stock)
        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        self.session.pop(self.session_key, None)
        self.session.modified = True

    def save(self):
        self.session[self.session_key] = self.cart
        self.session.modified = True

    @property
    def subtotal(self):
        return sum((item["subtotal"] for item in self), Decimal("0.00"))

    @property
    def delivery_fee(self):
        if len(self) < 1:
            return Decimal("0.00")
        return Decimal(str(getattr(settings, "VELQARO_DELIVERY_FEE", "30.00")))

    @property
    def total(self):
        return self.subtotal + self.delivery_fee

    def as_order_items(self):
        return list(self)

    @staticmethod
    def _clean_quantity(quantity):
        try:
            return max(1, int(quantity))
        except (TypeError, ValueError):
            return 1
