"""
Database models for the Online Restaurant project.

Architecture overview:
    User (Django auth) 1 --- 1 Cart 1 --- N CartItem N --- 1 Dish N --- 1 Category

* A cart belongs to a registered user (OneToOneField), never to a session.
* A cart item is unique per (cart, dish) pair so the same dish is stored once
  and its quantity is increased instead of creating duplicate rows.
* Categories are a fixed taxonomy from the assignment and are limited with
  TextChoices; a data migration seeds exactly the eight allowed rows.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum


class Category(models.Model):
    """One of the eight fixed menu categories required by the assignment."""

    class Name(models.TextChoices):
        SALADS = "Salads", "Salads"
        SOUPS = "Soups", "Soups"
        CHICKEN_DISHES = "Chicken-Dishes", "Chicken-Dishes"
        BEEF_DISHES = "Beef-Dishes", "Beef-Dishes"
        SEAFOOD_DISHES = "Seafood-Dishes", "Seafood-Dishes"
        VEGETABLE_DISHES = "Vegetable-Dishes", "Vegetable-Dishes"
        BITS_AND_BITES = "Bits&Bites", "Bits&Bites"
        ON_THE_SIDE = "On-The-Side", "On-The-Side"

    # choices + unique = only the eight names above can ever be stored.
    name = models.CharField(max_length=50, unique=True, choices=Name.choices)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Dish(models.Model):
    """A menu item shown on the product list page."""

    class Spiciness(models.IntegerChoices):
        NONE = 0, "Not spicy"
        MILD = 1, "Mild"
        MEDIUM = 2, "Medium"
        HOT = 3, "Hot"
        EXTREME = 4, "Extreme"

    # PROTECT keeps a category from being deleted while dishes reference it.
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="dishes",
    )
    image = models.ImageField(upload_to="dishes/")
    name = models.CharField(max_length=120)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    # The assignment explicitly requires 0..4 spiciness.
    spiciness = models.PositiveSmallIntegerField(
        choices=Spiciness.choices,
        default=Spiciness.NONE,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text="0 = not spicy, 4 = extreme",
    )
    contains_walnuts = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "dishes"

    def __str__(self):
        return self.name


class Cart(models.Model):
    """The shopping cart of exactly one registered user."""

    # OneToOneField guarantees that a user cannot own more than one cart.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Cart of {self.user}"

    @property
    def total_quantity(self) -> int:
        """Sum of quantities of all rows; used by the navbar badge."""
        result = self.items.aggregate(total=Sum("quantity"))["total"]
        return result or 0

    @property
    def total_price(self) -> Decimal:
        """Grand total of the cart. Decimal is used end-to-end for money."""
        return sum(
            (item.total_price for item in self.items.all()),
            Decimal("0.00"),
        )


class CartItem(models.Model):
    """A dish inside a cart together with its ordered quantity."""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    # If a dish is removed from the menu it disappears from all carts too.
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ("id",)
        constraints = [
            # Database-level protection against duplicate dish rows.
            models.UniqueConstraint(
                fields=("cart", "dish"),
                name="unique_cart_item_per_dish",
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.dish.name}"

    @property
    def total_price(self) -> Decimal:
        """Price of this row: unit price multiplied by quantity."""
        return self.dish.price * self.quantity
