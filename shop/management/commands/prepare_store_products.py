from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from shop.models import Category, Product


TARGET_STOREFRONT_PRODUCTS = 3


class Command(BaseCommand):
    help = "Prepare launch storefront data with exactly 3 active products per category."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show products that would be kept, created, deactivated, or deleted without changing data.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Apply the cleanup. Required for database writes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        confirm = options["confirm"]
        if dry_run and confirm:
            raise CommandError("Use either --dry-run or --confirm, not both.")
        if not dry_run and not confirm:
            raise CommandError("Run with --dry-run to preview or --confirm to apply changes.")

        plan = self._build_plan()
        self._print_plan(plan)

        has_writes = any(plan[action] for action in ("create", "deactivate", "delete"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run only. No database changes were made."))
            return
        if has_writes and not confirm:
            raise CommandError("Destructive cleanup requires --confirm.")

        with transaction.atomic():
            for item in plan["create"]:
                Product.objects.create(
                    category=item["category"],
                    name=item["name"],
                    slug=item["slug"],
                    short_description=item["short_description"],
                    description=item["description"],
                    price=item["price"],
                    old_price=None,
                    material=item["material"],
                    color=item["color"],
                    stock=item["stock"],
                    is_active=True,
                    is_featured=False,
                )

            for product in plan["deactivate"]:
                if product.is_active:
                    product.is_active = False
                    product.is_featured = False
                    product.save(update_fields=["is_active", "is_featured", "updated_at"])

            for product in plan["delete"]:
                product.delete()

        self.stdout.write(self.style.SUCCESS("Store products prepared successfully."))

    def _build_plan(self):
        plan = {
            "categories": [],
            "keep": [],
            "create": [],
            "deactivate": [],
            "delete": [],
        }
        for category in Category.objects.order_by("name", "id"):
            products = list(
                Product.objects.filter(category=category)
                .select_related("category")
                .prefetch_related("order_items")
            )
            ranked_products = sorted(
                [product for product in products if product.is_active],
                key=self._product_rank,
                reverse=True,
            )
            keep = ranked_products[:TARGET_STOREFRONT_PRODUCTS]
            keep_ids = {product.id for product in keep}

            for product in keep:
                plan["keep"].append(product)

            for product in products:
                if product.id in keep_ids:
                    continue
                if product.order_items.exists():
                    if product.is_active:
                        plan["deactivate"].append(product)
                else:
                    plan["delete"].append(product)

            placeholder_count = max(0, TARGET_STOREFRONT_PRODUCTS - len(keep))
            for index in range(placeholder_count):
                placeholder_number = len(keep) + index + 1
                plan["create"].append(self._placeholder_for(category, placeholder_number))

            plan["categories"].append(
                {
                    "category": category,
                    "current_products": len(products),
                    "current_active": sum(1 for product in products if product.is_active),
                    "planned_keep": len(keep),
                    "planned_create": placeholder_count,
                }
            )
        return plan

    def _product_rank(self, product):
        return (
            int(product.is_active),
            int(self._has_valid_image(product)),
            int(self._is_complete(product)),
            int(product.stock > 0),
            int(product.is_featured),
            int(product.order_items.exists()),
            product.stock,
            product.created_at,
            product.id,
        )

    def _has_valid_image(self, product):
        if not product.main_image:
            return False
        try:
            return product.main_image.storage.exists(product.main_image.name)
        except Exception:
            return False

    def _is_complete(self, product):
        return all(
            [
                bool(product.name),
                bool(product.short_description),
                bool(product.description),
                product.price is not None,
                product.stock is not None,
            ]
        )

    def _placeholder_for(self, category, number):
        name = f"Produit {number}"
        return {
            "category": category,
            "name": name,
            "slug": self._unique_slug(category, name),
            "short_description": "Produit temporaire a remplacer avant le lancement.",
            "description": "Description temporaire. Remplacez ce produit depuis Django Admin.",
            "price": Decimal("199.00"),
            "material": "A definir",
            "color": "A definir",
            "stock": 10,
        }

    def _unique_slug(self, category, name):
        base = slugify(f"{category.slug}-{name}") or f"{category.slug}-produit"
        slug = base
        counter = 2
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def _print_plan(self, plan):
        self.stdout.write("Categories processed:")
        for item in plan["categories"]:
            category = item["category"]
            self.stdout.write(
                f"- {category.name} ({category.slug}): "
                f"{item['current_products']} products, {item['current_active']} active; "
                f"keep {item['planned_keep']}, create {item['planned_create']}"
            )

        self._print_products("Products kept", plan["keep"])
        self._print_placeholders("Products created", plan["create"])
        self._print_products("Products deactivated because they are referenced by orders", plan["deactivate"])
        self._print_products("Products deleted", plan["delete"])

    def _print_products(self, title, products):
        self.stdout.write("")
        self.stdout.write(f"{title}: {len(products)}")
        for product in products:
            refs = product.order_items.count()
            self.stdout.write(f"- [{product.category.name}] #{product.id} {product.name} ({product.slug}) refs={refs}")

    def _print_placeholders(self, title, placeholders):
        self.stdout.write("")
        self.stdout.write(f"{title}: {len(placeholders)}")
        for item in placeholders:
            self.stdout.write(f"- [{item['category'].name}] {item['name']} ({item['slug']})")
