"""URL routes for the restaurant app."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "restaurant"

urlpatterns = [
    # Public menu
    path("", views.product_list, name="product_list"),
    # Cart (all views are @login_required)
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:dish_id>/", views.cart_add, name="cart_add"),
    path(
        "cart/item/<int:item_id>/increase/",
        views.cart_item_increase,
        name="cart_item_increase",
    ),
    path(
        "cart/item/<int:item_id>/decrease/",
        views.cart_item_decrease,
        name="cart_item_decrease",
    ),
    path(
        "cart/item/<int:item_id>/remove/",
        views.cart_item_remove,
        name="cart_item_remove",
    ),
    # Authentication
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="restaurant/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("register/", views.register, name="register"),
    # Django 5+ LogoutView accepts POST only; the navbar uses a POST form.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
