"""
Views for the Online Restaurant project.

Access rules:
* The menu (product list) is public.
* Everything that reads or mutates a cart is protected with @login_required.
* All mutations are POST-only and every CartItem lookup is scoped to
  request.user, which prevents one user from editing another user's cart (IDOR).
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .forms import RegisterForm
from .models import Cart, CartItem, Category, Dish

# Allowed spiciness values are strings because GET parameters are strings.
_SPICINESS_VALUES = {str(value) for value, _label in Dish.Spiciness.choices}


def _get_cart(user):
    """Return the user's cart, creating it if it is missing.

    The post_save signal creates carts for new users; this helper keeps the
    views safe for older users or carts deleted manually from the admin.
    """
    cart, _created = Cart.objects.get_or_create(user=user)
    return cart


def _redirect_back(request, fallback="restaurant:product_list"):
    """Redirect to a validated `next` URL or to a safe fallback page.

    Validating the host prevents open-redirect attacks through a crafted
    ?next= parameter.
    """
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(fallback)


def _filtered_dishes(request):
    """Build the product queryset from the four optional GET filters.

    All filters are applied to the same queryset with chained .filter() calls,
    so they combine with AND semantics (category + spiciness + walnuts +
    vegetarian at the same time).
    """
    dishes = Dish.objects.select_related("category")

    category = request.GET.get("category", "").strip()
    if category.isdigit():
        dishes = dishes.filter(category_id=int(category))
    else:
        category = ""

    spiciness = request.GET.get("spiciness", "").strip()
    if spiciness in _SPICINESS_VALUES:
        dishes = dishes.filter(spiciness=int(spiciness))
    else:
        spiciness = ""

    contains_walnuts = request.GET.get("contains_walnuts") == "1"
    is_vegetarian = request.GET.get("is_vegetarian") == "1"

    if contains_walnuts:
        dishes = dishes.filter(contains_walnuts=True)
    if is_vegetarian:
        dishes = dishes.filter(is_vegetarian=True)

    filters = {
        "category": category,
        "spiciness": spiciness,
        "contains_walnuts": contains_walnuts,
        "is_vegetarian": is_vegetarian,
    }
    return dishes, filters


def product_list(request):
    """Public menu page with combined filtering."""
    dishes, filters = _filtered_dishes(request)
    spiciness_options = [
        (value, f"{value} / 4 - {label}")
        for value, label in Dish.Spiciness.choices
    ]

    context = {
        "dishes": dishes,
        "categories": Category.objects.all(),
        "spiciness_options": spiciness_options,
        "filters": filters,
        "has_active_filters": any(
            (
                filters["category"],
                filters["spiciness"],
                filters["contains_walnuts"],
                filters["is_vegetarian"],
            )
        ),
    }
    return render(request, "restaurant/product_list.html", context)


@login_required
def cart_detail(request):
    """Show the authenticated user's cart and its dynamically calculated total."""
    cart = _get_cart(request.user)
    # select_related avoids one query per item when total_price is calculated.
    items = list(cart.items.select_related("dish"))
    total = sum((item.total_price for item in items), Decimal("0.00"))

    return render(
        request,
        "restaurant/cart.html",
        {"cart": cart, "items": items, "total": total},
    )


@login_required
def cart_add(request, dish_id):
    """Add a dish to the cart, or increase its quantity if already present."""
    # Only POST may change data. A GET is redirected to the cart because the
    # login flow can land here with GET after an anonymous POST attempt.
    if request.method != "POST":
        return redirect("restaurant:cart_detail")

    dish = get_object_or_404(Dish, pk=dish_id)
    cart = _get_cart(request.user)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        dish=dish,
        defaults={"quantity": 1},
    )
    if not created:
        # The unique (cart, dish) constraint guarantees one row per dish.
        item.quantity += 1
        item.save(update_fields=["quantity"])

    messages.success(
        request,
        f'"{dish.name}" is in your cart (quantity: {item.quantity}).',
    )
    return _redirect_back(request)


@login_required
def cart_item_increase(request, item_id):
    """Increase the quantity of one cart row by one."""
    if request.method != "POST":
        return redirect("restaurant:cart_detail")

    # cart__user=request.user is the ownership check that prevents IDOR.
    item = get_object_or_404(
        CartItem.objects.select_related("dish"),
        pk=item_id,
        cart__user=request.user,
    )
    item.quantity += 1
    item.save(update_fields=["quantity"])
    return redirect("restaurant:cart_detail")


@login_required
def cart_item_decrease(request, item_id):
    """Decrease quantity by one, removing the row when it reaches zero."""
    if request.method != "POST":
        return redirect("restaurant:cart_detail")

    item = get_object_or_404(
        CartItem.objects.select_related("dish"),
        pk=item_id,
        cart__user=request.user,
    )
    if item.quantity > 1:
        item.quantity -= 1
        item.save(update_fields=["quantity"])
    else:
        dish_name = item.dish.name
        item.delete()
        messages.info(request, f'"{dish_name}" was removed from your cart.')

    return redirect("restaurant:cart_detail")


@login_required
def cart_item_remove(request, item_id):
    """Remove a dish from the cart completely."""
    if request.method != "POST":
        return redirect("restaurant:cart_detail")

    item = get_object_or_404(
        CartItem.objects.select_related("dish"),
        pk=item_id,
        cart__user=request.user,
    )
    dish_name = item.dish.name
    item.delete()
    messages.success(request, f'"{dish_name}" was removed from your cart.')
    return redirect("restaurant:cart_detail")


@require_http_methods(["GET", "POST"])
def register(request):
    """Register a user, log them in and make sure an empty cart exists."""
    if request.user.is_authenticated:
        return redirect("restaurant:product_list")

    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Primary cart creation happens in restaurant.signals. This call is
            # a safety net and returns the existing cart without adding items,
            # so every new account starts with a clean, empty cart.
            Cart.objects.get_or_create(user=user)

            auth_login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            messages.success(
                request,
                "Your account was created. You are now logged in.",
            )

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("restaurant:product_list")
    else:
        form = RegisterForm()

    return render(
        request,
        "restaurant/register.html",
        {"form": form, "next": next_url},
    )
