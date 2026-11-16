"""Automated tests for the core business rules of the restaurant project."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import Cart, CartItem, Category, Dish


class RestaurantTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Categories are seeded by migration 0002; get() is enough here.
        cls.salads = Category.objects.get(name="Salads")
        cls.soups = Category.objects.get(name="Soups")
        cls.chicken = Category.objects.get(name="Chicken-Dishes")
        cls.beef = Category.objects.get(name="Beef-Dishes")
        cls.seafood = Category.objects.get(name="Seafood-Dishes")

        cls.garden_salad = Dish.objects.create(
            category=cls.salads,
            image="dishes/garden-salad.jpg",
            name="Garden Salad",
            price=Decimal("9.50"),
            spiciness=0,
            contains_walnuts=False,
            is_vegetarian=True,
        )
        cls.nut_salad = Dish.objects.create(
            category=cls.salads,
            image="dishes/nut-salad.jpg",
            name="Walnut Salad",
            price=Decimal("10.00"),
            spiciness=2,
            contains_walnuts=True,
            is_vegetarian=True,
        )
        cls.spicy_beef = Dish.objects.create(
            category=cls.beef,
            image="dishes/beef.jpg",
            name="Spicy Beef",
            price=Decimal("18.50"),
            spiciness=2,
            contains_walnuts=True,
            is_vegetarian=False,
        )
        cls.chicken_dish = Dish.objects.create(
            category=cls.chicken,
            image="dishes/chicken.jpg",
            name="Chicken Tabaka",
            price=Decimal("15.90"),
            spiciness=1,
            contains_walnuts=False,
            is_vegetarian=False,
        )
        cls.salmon = Dish.objects.create(
            category=cls.seafood,
            image="dishes/salmon.jpg",
            name="Grilled Salmon",
            price=Decimal("22.00"),
            spiciness=0,
            contains_walnuts=False,
            is_vegetarian=False,
        )

        cls.user = User.objects.create_user(
            username="alice", password="StrongPass123!"
        )
        cls.other_user = User.objects.create_user(
            username="bob", password="StrongPass123!"
        )

    # ------------------------------------------------------------------
    # Model / database rules
    # ------------------------------------------------------------------
    def test_signal_creates_an_empty_cart_for_each_user(self):
        self.assertTrue(Cart.objects.filter(user=self.user).exists())
        self.assertTrue(Cart.objects.filter(user=self.other_user).exists())
        self.assertEqual(self.user.cart.items.count(), 0)

    def test_category_rejects_values_outside_the_fixed_taxonomy(self):
        category = Category(name="Desserts")
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_dish_spiciness_must_be_between_zero_and_four(self):
        dish = Dish(
            category=self.salads,
            image="dishes/invalid.jpg",
            name="Too spicy",
            price=Decimal("5.00"),
            spiciness=5,
        )
        with self.assertRaises(ValidationError) as context:
            dish.full_clean()
        self.assertIn("spiciness", context.exception.message_dict)

    def test_cart_item_total_and_cart_total_use_decimals(self):
        item = CartItem.objects.create(
            cart=self.user.cart, dish=self.garden_salad, quantity=3
        )
        self.assertEqual(item.total_price, Decimal("28.50"))
        self.assertEqual(self.user.cart.total_price, Decimal("28.50"))
        self.assertEqual(self.user.cart.total_quantity, 3)

    def test_cart_item_is_unique_per_cart_and_dish(self):
        CartItem.objects.create(cart=self.user.cart, dish=self.garden_salad)
        # The unique constraint is enforced by the database layer.
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.user.cart, dish=self.garden_salad
            )

    # ------------------------------------------------------------------
    # Public menu and filtering
    # ------------------------------------------------------------------
    def test_menu_is_public(self):
        response = self.client.get(reverse("restaurant:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Garden Salad")

    def test_filter_by_category(self):
        response = self.client.get(
            reverse("restaurant:product_list"),
            {"category": self.salads.pk},
        )
        names = {dish.name for dish in response.context["dishes"]}
        self.assertEqual(names, {"Garden Salad", "Walnut Salad"})

    def test_filter_by_spiciness(self):
        response = self.client.get(
            reverse("restaurant:product_list"), {"spiciness": "0"}
        )
        names = {dish.name for dish in response.context["dishes"]}
        self.assertEqual(names, {"Garden Salad", "Grilled Salmon"})

    def test_filter_by_walnuts(self):
        response = self.client.get(
            reverse("restaurant:product_list"), {"contains_walnuts": "1"}
        )
        names = {dish.name for dish in response.context["dishes"]}
        self.assertEqual(names, {"Walnut Salad", "Spicy Beef"})

    def test_filter_by_vegetarian(self):
        response = self.client.get(
            reverse("restaurant:product_list"), {"is_vegetarian": "1"}
        )
        names = {dish.name for dish in response.context["dishes"]}
        self.assertEqual(names, {"Garden Salad", "Walnut Salad"})

    def test_all_filters_combine_with_and_semantics(self):
        response = self.client.get(
            reverse("restaurant:product_list"),
            {
                "category": self.salads.pk,
                "spiciness": "2",
                "contains_walnuts": "1",
                "is_vegetarian": "1",
            },
        )
        names = {dish.name for dish in response.context["dishes"]}
        self.assertEqual(names, {"Walnut Salad"})

    def test_invalid_filter_values_are_ignored(self):
        response = self.client.get(
            reverse("restaurant:product_list"),
            {"category": "abc", "spiciness": "9"},
        )
        self.assertEqual(len(response.context["dishes"]), 5)

    # ------------------------------------------------------------------
    # Authentication and permissions
    # ------------------------------------------------------------------
    def test_anonymous_user_is_redirected_from_cart(self):
        response = self.client.get(reverse("restaurant:cart_detail"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("restaurant:login"), response.url)

    def test_anonymous_user_is_redirected_when_adding_to_cart(self):
        response = self.client.post(
            reverse("restaurant:cart_add", args=[self.garden_salad.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("restaurant:login"), response.url)
        self.assertIn("next=", response.url)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_register_creates_user_cart_and_logs_in(self):
        response = self.client.post(
            reverse("restaurant:register"),
            {
                "username": "charlie",
                "password1": "AnotherPass123!",
                "password2": "AnotherPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("restaurant:product_list"))

        user = User.objects.get(username="charlie")
        self.assertTrue(Cart.objects.filter(user=user).exists())
        self.assertEqual(user.cart.items.count(), 0)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), user.pk
        )

    # ------------------------------------------------------------------
    # Cart operations
    # ------------------------------------------------------------------
    def test_add_to_cart_creates_then_increments_one_row(self):
        self.client.force_login(self.user)
        url = reverse("restaurant:cart_add", args=[self.garden_salad.pk])

        response = self.client.post(url)
        self.assertRedirects(response, reverse("restaurant:product_list"))
        item = CartItem.objects.get(cart=self.user.cart)
        self.assertEqual(item.quantity, 1)

        self.client.post(url)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_add_to_cart_honours_a_safe_next_url(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("restaurant:cart_add", args=[self.garden_salad.pk]),
            {"next": reverse("restaurant:product_list") + "?spiciness=0"},
        )
        self.assertRedirects(
            response,
            reverse("restaurant:product_list") + "?spiciness=0",
        )

    def test_add_to_cart_rejects_an_external_next_url(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("restaurant:cart_add", args=[self.garden_salad.pk]),
            {"next": "https://evil.example/"},
        )
        self.assertRedirects(response, reverse("restaurant:product_list"))

    def test_increase_decrease_and_remove_quantity(self):
        self.client.force_login(self.user)
        item = CartItem.objects.create(
            cart=self.user.cart, dish=self.garden_salad, quantity=2
        )

        self.client.post(
            reverse("restaurant:cart_item_increase", args=[item.pk])
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

        self.client.post(
            reverse("restaurant:cart_item_decrease", args=[item.pk])
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

        self.client.post(
            reverse("restaurant:cart_item_remove", args=[item.pk])
        )
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

    def test_decreasing_last_item_removes_the_row(self):
        self.client.force_login(self.user)
        item = CartItem.objects.create(
            cart=self.user.cart, dish=self.garden_salad, quantity=1
        )
        self.client.post(
            reverse("restaurant:cart_item_decrease", args=[item.pk])
        )
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

    def test_user_cannot_modify_another_users_cart_item(self):
        item = CartItem.objects.create(
            cart=self.other_user.cart, dish=self.garden_salad, quantity=1
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("restaurant:cart_item_increase", args=[item.pk])
        )
        self.assertEqual(response.status_code, 404)

        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)
