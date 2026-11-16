"""Template context shared by every page."""

from .models import Cart


def cart_summary(request):
    """Expose the total number of items so the navbar can show a badge.

    A user normally always has a cart (created by the post_save signal), but
    the lookup is defensive so legacy/admin-created users cannot break pages.
    """
    if not request.user.is_authenticated:
        return {"cart_item_count": 0}

    try:
        cart = request.user.cart
    except Cart.DoesNotExist:
        return {"cart_item_count": 0}

    return {"cart_item_count": cart.total_quantity}
