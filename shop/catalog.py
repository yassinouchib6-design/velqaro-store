from django.conf import settings
from django.db.models import Count, Q

from .models import Category


CATEGORY_CARD_META = {
    "bracelets": {
        "image_path": "img/category-bracelets.png",
        "description": "Acier 316L, lignes nettes, presence quotidienne.",
    },
    "chaines": {
        "image_path": "img/category-chains.png",
        "description": "Mailles puissantes, finitions silver et gunmetal.",
    },
    "packs": {
        "image_path": "img/category-rings.png",
        "description": "Combinaisons premium pour un style complet.",
    },
}


def categories_with_active_product_counts():
    return Category.objects.filter(is_active=True).annotate(
        active_product_count=Count(
            "products",
            filter=Q(products__is_active=True),
        )
    )


def public_categories():
    return categories_with_active_product_counts()


def category_cards(categories):
    cards = []
    for category in categories:
        meta = CATEGORY_CARD_META.get(
            category.slug,
            {
                "image_path": "img/category-rings.png",
                "description": f"Selection {settings.STORE_NAME} disponible maintenant.",
            },
        )
        cards.append(
            {
                "slug": category.slug,
                "title": category.name,
                "image_path": meta["image_path"],
                "description": meta["description"],
                "alt": f"{category.name} {settings.STORE_NAME}",
            }
        )
    return cards
