"""
Signals that keep the user/cart invariant in one place.

Every newly created user receives an empty Cart immediately. RegisterView also
uses get_or_create as a safety net, but the signal is the primary mechanism so
that users created from the admin or the shell are covered as well.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Cart


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_cart_for_new_user(sender, instance, created, raw=False, **kwargs):
    if raw:
        # Do not touch the database while fixtures are being loaded.
        return
    if created:
        Cart.objects.get_or_create(user=instance)
