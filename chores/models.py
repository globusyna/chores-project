from django.core.validators import MinValueValidator
from django.db import models


class ChoreTemplate(models.Model):
    """A recurring chore definition used to repopulate the board (tasks.md #6).

    Spawning `Bounty` rows from templates is #16; this model is admin-only.
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    default_point_value = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
