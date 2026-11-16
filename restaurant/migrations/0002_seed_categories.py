"""Seed the eight fixed categories required by the assignment.

The Category.name field also has choices and unique=True, so this migration is
what guarantees the table contains exactly the allowed taxonomy on every fresh
database (including test databases).
"""

from django.db import migrations

CATEGORY_NAMES = [
    "Salads",
    "Soups",
    "Chicken-Dishes",
    "Beef-Dishes",
    "Seafood-Dishes",
    "Vegetable-Dishes",
    "Bits&Bites",
    "On-The-Side",
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("restaurant", "Category")
    for name in CATEGORY_NAMES:
        Category.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("restaurant", "0001_initial"),
    ]

    operations = [
        # Reverse is a no-op: migration 0001 drops the table anyway, and
        # deleting categories with dishes would be blocked by PROTECT.
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
