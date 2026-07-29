from .cart import Cart


def cart_counter(request):
    return {"cart_count": len(Cart(request))}
