from django.db import migrations


def create_chaines_and_move_products(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Product = apps.get_model("shop", "Product")

    chaines, _ = Category.objects.get_or_create(
        slug="chaines",
        defaults={"name": "Chaînes", "is_active": True},
    )

    portefeuilles = Category.objects.filter(slug="portefeuilles").first()
    if portefeuilles:
        Product.objects.filter(category=portefeuilles).update(category=chaines)


def remove_chaines_and_restore_products(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Product = apps.get_model("shop", "Product")

    chaines = Category.objects.filter(slug="chaines").first()
    portefeuilles = Category.objects.filter(slug="portefeuilles").first()

    if chaines and portefeuilles:
        Product.objects.filter(category=chaines).update(category=portefeuilles)
    if chaines:
        chaines.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0005_rename_chains_category"),
    ]

    operations = [
        migrations.RunPython(create_chaines_and_move_products, remove_chaines_and_restore_products),
    ]
