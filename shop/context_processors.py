from .cart import Cart
from .catalog import public_categories


def cart_counter(request):
    return {
        "cart_count": len(Cart(request)),
        "public_categories": public_categories(),
    }
