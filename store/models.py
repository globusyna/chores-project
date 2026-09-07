from django.core.validators import MinValueValidator
from django.db import models


class Perk(models.Model):
    """An item a user can redeem points for (tasks.md #8).

    The `Purchase` model and its workflow are #9; this model is admin-only.
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    point_cost = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
