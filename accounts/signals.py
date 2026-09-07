from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    """Give every newly created User exactly one Profile (default CHILD).

    Only fires on creation, so re-saving a User never adds a second Profile
    or resets ``role``. ``get_or_create`` keeps it safe if the signal is
    somehow delivered twice.
    """
    if created:
        Profile.objects.get_or_create(user=instance)
