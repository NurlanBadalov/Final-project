"""Django admin configuration: every model from the assignment is registered."""

from django.contrib import admin

from .models import Cart, CartItem, Category, Dish

admin.site.site_header = "Online Restaurant Administration"
admin.site.site_title = "Online Restaurant Admin"
admin.site.index_title = "Restaurant management"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Categories are a fixed taxonomy, so they are read-only in the admin."""

    list_display = ("name", "dish_count")
    search_fields = ("name",)

    @admin.display(description="Dishes")
    def dish_count(self, obj):
        return obj.dishes.count()

    def has_add_permission(self, request):
        # The eight categories are created by the seed data migration.
        return False

    def has_delete_permission(self, request, obj=None):
        # Deleting a category would break the required eight-category list.
        return False


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "spiciness",
        "contains_walnuts",
        "is_vegetarian",
    )
    list_filter = (
        "category",
        "spiciness",
        "contains_walnuts",
        "is_vegetarian",
    )
    search_fields = ("name",)
    list_select_related = ("category",)


class CartItemInline(admin.TabularInline):
    """Cart rows are edited together with their cart."""

    model = CartItem
    extra = 0
    fields = ("dish", "quantity", "line_total")
    readonly_fields = ("line_total",)

    @admin.display(description="Line total")
    def line_total(self, obj):
        return obj.total_price if obj.pk else "-"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "total_quantity", "total_price", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("user", "created_at", "total_quantity", "total_price")
    list_select_related = ("user",)
    inlines = (CartItemInline,)

    def has_add_permission(self, request):
        # Carts are created automatically by the post_save signal.
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "dish", "quantity", "line_total")
    list_filter = ("dish__category",)
    search_fields = ("cart__user__username", "dish__name")
    readonly_fields = ("line_total",)
    list_select_related = ("cart__user", "dish")

    @admin.display(description="Line total")
    def line_total(self, obj):
        return obj.total_price
