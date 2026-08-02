from django.db import migrations


def rename_chains_to_portefeuilles(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Category.objects.filter(slug="chains").update(name="Portefeuilles", slug="portefeuilles")


def rename_portefeuilles_to_chains(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Category.objects.filter(slug="portefeuilles").update(name="Chains", slug="chains")


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0004_alter_product_is_active"),
    ]

    operations = [
        migrations.RunPython(rename_chains_to_portefeuilles, rename_portefeuilles_to_chains),
    ]
