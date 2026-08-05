from django.conf import settings

from .cart import Cart
from .catalog import public_categories


def cart_counter(request):
    return {
        "cart_count": len(Cart(request)),
        "public_categories": public_categories(),
        "store_config": {
            "name": settings.STORE_NAME,
            "tagline": settings.STORE_TAGLINE,
            "meta_description": settings.STORE_META_DESCRIPTION,
            "currency": settings.STORE_CURRENCY_LABEL,
            "free_delivery_label": settings.STORE_FREE_DELIVERY_LABEL,
            "whatsapp_url": settings.STORE_WHATSAPP_URL,
            "instagram_url": settings.STORE_INSTAGRAM_URL,
            "instagram_handle": settings.STORE_INSTAGRAM_HANDLE,
        },
    }
