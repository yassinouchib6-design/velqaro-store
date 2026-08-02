import random
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from shop.models import Category, Product, ProductImage


class Command(BaseCommand):
    help = "Populate the VELQARO store with realistic demo categories and products."

    CATEGORY_SPECS = {
        "Bracelets": {"slug": "bracelets", "count": 15},
        "Chaînes": {"slug": "chaines", "count": 15},
        "Rings": {"slug": "rings", "count": 10},
        "Packs": {"slug": "packs", "count": 10},
    }

    COLORS = ["Silver", "Black", "Gunmetal"]
    MATERIALS = ["316L Stainless Steel"]

    BRACELET_NAMES = [
        "Bracelet Atlas Noir",
        "Bracelet Mirage Silver",
        "Bracelet Carbon Edge",
        "Bracelet Rivage Acier",
        "Bracelet Nova Gunmetal",
        "Bracelet Oryx 316L",
        "Bracelet Ligne Nocturne",
        "Bracelet Vesper Mat",
        "Bracelet Sillage Steel",
        "Bracelet Ardent Noir",
        "Bracelet Monolithe",
        "Bracelet Aero Slim",
        "Bracelet Heritage Noir",
        "Bracelet Tempus Silver",
        "Bracelet Apex Gun",
    ]

    CHAIN_NAMES = [
        "Chaine Signature Cuban",
        "Chaine Noire Maillon",
        "Chaine Atlas Fine",
        "Chaine Vesper Box",
        "Chaine Horizon Steel",
        "Chaine Obsidienne",
        "Chaine Nova Link",
        "Chaine Rivage 316L",
        "Chaine Sombre Ligne",
        "Chaine Eclat Control",
        "Chaine Maison Silver",
        "Chaine Apex Noire",
        "Chaine Heritage Box",
        "Chaine Tempo Gunmetal",
        "Chaine Initiale Steel",
    ]

    RING_NAMES = [
        "Bague Chevaliere Noire",
        "Bague Ligne Argent",
        "Bague Monolithe Steel",
        "Bague Nova Gun",
        "Bague Atlas Square",
        "Bague Vesper Slim",
        "Bague Rivage Polie",
        "Bague Oryx Textured",
        "Bague Heritage Noire",
        "Bague Apex Silver",
    ]

    PACK_NAMES = [
        "Pack Signature Noir",
        "Pack Silver Essential",
        "Pack Urban Steel",
        "Pack Nocturne Duo",
        "Pack Prestige 316L",
        "Pack Atlas Complet",
        "Pack Gunmetal Elite",
        "Pack Weekend Noir",
        "Pack Maison Silver",
        "Pack Premiere Ligne",
    ]

    NAME_MAP = {
        "Bracelets": BRACELET_NAMES,
        "Chaînes": CHAIN_NAMES,
        "Rings": RING_NAMES,
        "Packs": PACK_NAMES,
    }

    SHORT_TEMPLATES = [
        "{name} en acier 316L, concu pour une presence masculine nette.",
        "{name} avec finition premium et lignes sobres pour le quotidien.",
        "{name} pense pour ajouter une signature discrete et luxueuse.",
        "{name} aux details precis, ideal pour un style moderne et affirme.",
    ]

    LONG_TEMPLATES = [
        "{name} associe une silhouette moderne a une finition {color}. Sa construction en {material} offre un rendu premium, durable et facile a porter avec une tenue casual ou habillee. Une piece concue pour rester sobre, forte et parfaitement masculine.",
        "Avec {name}, VELQARO propose une piece equilibree entre minimalisme et presence. Le {material} apporte une sensation solide, tandis que la teinte {color} donne du relief au poignet ou a la silhouette. Chaque detail est pense pour un usage quotidien elegant.",
        "{name} a ete imagine pour ceux qui veulent un accessoire clair, propre et haut de gamme. La finition {color} capte la lumiere avec retenue, et le {material} conserve son aspect premium au fil des ports.",
        "Piece essentielle de la selection VELQARO, {name} complete une garde-robe masculine sans surcharge. Son design privilegie la matiere, la ligne et la proportion pour creer une impression de luxe calme.",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            type=int,
            default=20260719,
            help="Random seed used for repeatable demo data.",
        )
        parser.add_argument(
            "--clear-seed",
            action="store_true",
            help="Delete products matching the generated seed slugs before recreating them.",
        )

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        image_pool = self._collect_images()
        product_specs = self._build_product_specs(rng)
        slugs = [spec["slug"] for spec in product_specs]

        with transaction.atomic():
            categories = self._get_or_create_categories()

            if options["clear_seed"]:
                ProductImage.objects.filter(product__slug__in=slugs).delete()
                Product.objects.filter(slug__in=slugs).delete()

            created_count = 0
            updated_count = 0
            gallery_count = 0

            for spec in product_specs:
                category = categories[spec["category"]]
                main_image = self._pick_image(image_pool["main"], category.slug, rng)
                defaults = {
                    "category": category,
                    "short_description": spec["short_description"],
                    "description": spec["description"],
                    "price": spec["price"],
                    "old_price": spec["old_price"],
                    "material": spec["material"],
                    "color": spec["color"],
                    "stock": spec["stock"],
                    "main_image": main_image,
                    "is_active": True,
                    "is_featured": spec["is_featured"],
                }
                product, created = Product.objects.update_or_create(
                    slug=spec["slug"],
                    defaults={"name": spec["name"], **defaults},
                )
                created_count += int(created)
                updated_count += int(not created)

                ProductImage.objects.filter(product=product).delete()
                gallery_images = self._pick_gallery_images(
                    image_pool["gallery"], category.slug, rng, count=rng.randint(2, 3)
                )
                for index, image in enumerate(gallery_images, start=1):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        alt_text=f"{product.name} detail {index}",
                    )
                    gallery_count += 1

        self.stdout.write(self.style.SUCCESS("VELQARO demo store seeded successfully."))
        self.stdout.write(f"Categories: {Category.objects.filter(slug__in=[c['slug'] for c in self.CATEGORY_SPECS.values()]).count()}")
        self.stdout.write(f"Products generated: {len(product_specs)}")
        self.stdout.write(f"Created products: {created_count}")
        self.stdout.write(f"Updated products: {updated_count}")
        self.stdout.write(f"Gallery images attached: {gallery_count}")
        self.stdout.write(f"Featured / best seller products: {Product.objects.filter(slug__in=slugs, is_featured=True).count()}")
        self.stdout.write("New products are represented by active, recently seeded products without an old price.")

    def _get_or_create_categories(self):
        categories = {}
        for name, spec in self.CATEGORY_SPECS.items():
            category = Category.objects.filter(slug=spec["slug"]).first()
            if category is None:
                category = Category.objects.filter(name__iexact=name).first()
                if category is not None:
                    category.slug = spec["slug"]
                    category.name = name
                    category.is_active = True
                    category.save(update_fields=["slug", "name", "is_active"])
                else:
                    category = Category.objects.create(
                        slug=spec["slug"],
                        name=name,
                        is_active=True,
                    )
            if category.name != name or not category.is_active:
                category.name = name
                category.is_active = True
                category.save(update_fields=["name", "is_active"])

            for duplicate in Category.objects.filter(name__iexact=name).exclude(pk=category.pk):
                if duplicate.products.count() == 0:
                    duplicate.delete()

            categories[name] = category
        return categories

    def _build_product_specs(self, rng):
        product_specs = []
        for category_name, category_spec in self.CATEGORY_SPECS.items():
            names = self.NAME_MAP[category_name]
            for index, name in enumerate(names[: category_spec["count"]], start=1):
                color = rng.choice(self.COLORS)
                material = rng.choice(self.MATERIALS)
                price = Decimal(rng.randrange(149, 400)).quantize(Decimal("0.01"))
                has_old_price = rng.random() < 0.38
                old_price = None
                if has_old_price:
                    old_price_value = min(499, int(price) + rng.choice([40, 50, 60, 80, 100]))
                    old_price = Decimal(old_price_value).quantize(Decimal("0.01"))
                is_featured = index in {1, 3, 5} or rng.random() < 0.22
                slug = slugify(name)
                short_description = rng.choice(self.SHORT_TEMPLATES).format(name=name)
                description = rng.choice(self.LONG_TEMPLATES).format(
                    name=name,
                    color=color.lower(),
                    material=material,
                )
                if not old_price and index % 4 == 0:
                    short_description = f"Nouveaute VELQARO: {short_description}"
                if is_featured and index % 2 == 1:
                    description = f"Best seller de la collection, {description[0].lower()}{description[1:]}"

                product_specs.append(
                    {
                        "category": category_name,
                        "name": name,
                        "slug": slug,
                        "short_description": short_description,
                        "description": description,
                        "price": price,
                        "old_price": old_price,
                        "stock": rng.randint(4, 35),
                        "material": material,
                        "color": color,
                        "is_featured": is_featured,
                    }
                )
        return product_specs

    def _collect_images(self):
        media_root = Path(settings.MEDIA_ROOT)
        main_images = list((media_root / "products" / "main").glob("*"))
        gallery_images = list((media_root / "products" / "gallery").glob("*"))
        fallback_images = list((Path(settings.BASE_DIR) / "static" / "img").glob("*"))
        return {
            "main": self._group_images(main_images or fallback_images),
            "gallery": self._group_images(gallery_images or main_images or fallback_images),
        }

    def _group_images(self, paths):
        grouped = {"bracelets": [], "chaines": [], "rings": [], "packs": [], "all": []}
        for path in paths:
            if not path.is_file():
                continue
            relative = self._relative_media_path(path)
            if not relative:
                continue
            lower_name = path.name.lower()
            grouped["all"].append(relative)
            if "bracelet" in lower_name:
                grouped["bracelets"].append(relative)
            elif "chaine" in lower_name or "chain" in lower_name:
                grouped["chaines"].append(relative)
            elif "bague" in lower_name or "ring" in lower_name:
                grouped["rings"].append(relative)
            elif "pack" in lower_name or "hero" in lower_name:
                grouped["packs"].append(relative)
        return grouped

    def _relative_media_path(self, path):
        media_root = Path(settings.MEDIA_ROOT)
        try:
            return str(path.relative_to(media_root)).replace("\\", "/")
        except ValueError:
            return ""

    def _pick_image(self, grouped_images, category_slug, rng):
        category_images = grouped_images.get(category_slug) or grouped_images.get("all") or []
        return rng.choice(category_images) if category_images else ""

    def _pick_gallery_images(self, grouped_images, category_slug, rng, count):
        category_images = grouped_images.get(category_slug) or grouped_images.get("all") or []
        if not category_images:
            return []
        if len(category_images) <= count:
            return category_images
        return rng.sample(category_images, count)
