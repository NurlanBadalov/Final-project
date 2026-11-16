"""Create a small, realistic demo menu for presentations and local testing.

Usage:
    python manage.py seed_demo

The command is idempotent (existing dishes are skipped) and never downloads
anything from the internet: each dish image is generated locally with Pillow.
Real restaurant photos can later be uploaded through the admin.
"""

from decimal import Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from restaurant.models import Category, Dish

IMAGE_SIZE = (800, 600)

DEMO_DISHES = [
    {
        "name": "Garden Salad",
        "category": "Salads",
        "price": "9.50",
        "spiciness": 0,
        "contains_walnuts": False,
        "is_vegetarian": True,
        "top": (52, 94, 63),
        "bottom": (24, 55, 36),
    },
    {
        "name": "Spicy Tomato Soup",
        "category": "Soups",
        "price": "8.00",
        "spiciness": 2,
        "contains_walnuts": False,
        "is_vegetarian": True,
        "top": (185, 75, 43),
        "bottom": (98, 32, 20),
    },
    {
        "name": "Chicken Tabaka",
        "category": "Chicken-Dishes",
        "price": "15.90",
        "spiciness": 1,
        "contains_walnuts": False,
        "is_vegetarian": False,
        "top": (176, 132, 55),
        "bottom": (92, 62, 22),
    },
    {
        "name": "Beef Stew with Walnuts",
        "category": "Beef-Dishes",
        "price": "18.50",
        "spiciness": 2,
        "contains_walnuts": True,
        "is_vegetarian": False,
        "top": (112, 66, 46),
        "bottom": (54, 30, 21),
    },
    {
        "name": "Grilled Salmon",
        "category": "Seafood-Dishes",
        "price": "22.00",
        "spiciness": 0,
        "contains_walnuts": False,
        "is_vegetarian": False,
        "top": (46, 108, 122),
        "bottom": (19, 52, 66),
    },
    {
        "name": "Roasted Vegetable Plate",
        "category": "Vegetable-Dishes",
        "price": "11.00",
        "spiciness": 1,
        "contains_walnuts": False,
        "is_vegetarian": True,
        "top": (120, 132, 56),
        "bottom": (58, 68, 26),
    },
    {
        "name": "Walnut Spinach Bites",
        "category": "Bits&Bites",
        "price": "7.50",
        "spiciness": 1,
        "contains_walnuts": True,
        "is_vegetarian": True,
        "top": (63, 110, 74),
        "bottom": (29, 58, 40),
    },
    {
        "name": "Adjika Sauce",
        "category": "On-The-Side",
        "price": "3.50",
        "spiciness": 4,
        "contains_walnuts": False,
        "is_vegetarian": True,
        "top": (158, 45, 36),
        "bottom": (78, 20, 16),
    },
]


def _load_font(size):
    """Use a bold system font when available, otherwise Pillow's default."""
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Pillow < 10.1 does not accept a size for the default font.
        return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width, max_lines=2):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:max_lines]


def _build_image(dish):
    """Create a simple branded placeholder image for one demo dish."""
    width, height = IMAGE_SIZE
    image = Image.new("RGB", IMAGE_SIZE)
    draw = ImageDraw.Draw(image)

    top = dish["top"]
    bottom = dish["bottom"]
    for y in range(height):
        ratio = y / (height - 1)
        color = tuple(
            round(top[channel] + (bottom[channel] - top[channel]) * ratio)
            for channel in range(3)
        )
        draw.line([(0, y), (width, y)], fill=color)

    image = image.convert("RGBA")

    # Soft decorative circles and a bottom shade keep the text readable.
    overlay = Image.new("RGBA", IMAGE_SIZE, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse((-140, -170, 360, 330), fill=(255, 255, 255, 24))
    overlay_draw.ellipse((520, 330, 960, 770), fill=(0, 0, 0, 34))
    overlay_draw.rectangle((0, 330, width, height), fill=(0, 0, 0, 62))
    image = Image.alpha_composite(image, overlay)

    draw = ImageDraw.Draw(image)
    category_font = _load_font(24)
    name_font = _load_font(58)
    footer_font = _load_font(19)

    # Category pill
    category_text = dish["category"].upper()
    text_width = draw.textlength(category_text, font=category_font)
    draw.rounded_rectangle(
        (46, 42, 46 + text_width + 36, 94),
        radius=26,
        fill=(255, 253, 249, 230),
    )
    draw.text((64, 56), category_text, font=category_font, fill=(33, 28, 23, 255))

    # Dish name
    lines = _wrap_text(draw, dish["name"], name_font, width - 120)
    y = 398 if len(lines) == 1 else 352
    for line in lines:
        draw.text((60, y), line, font=name_font, fill=(255, 255, 255, 255))
        y += 68

    # Footer
    draw.text(
        (62, height - 58),
        "ONLINE RESTAURANT  |  DEMO IMAGE",
        font=footer_font,
        fill=(255, 255, 255, 175),
    )

    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=90, optimize=True)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Seed the database with eight demo dishes and generated images."

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for demo in DEMO_DISHES:
            if Dish.objects.filter(name=demo["name"]).exists():
                skipped_count += 1
                continue

            category = Category.objects.get(name=demo["category"])
            dish = Dish(
                category=category,
                name=demo["name"],
                price=Decimal(demo["price"]),
                spiciness=demo["spiciness"],
                contains_walnuts=demo["contains_walnuts"],
                is_vegetarian=demo["is_vegetarian"],
            )
            image_name = f"{slugify(demo['name'])}.jpg"
            dish.image.save(image_name, _build_image(demo), save=False)
            dish.save()
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'  created "{dish.name}" ({category.name})')
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {created_count} created, "
                f"{skipped_count} already existed."
            )
        )
