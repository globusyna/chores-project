from django import forms

from chores.models import Bounty


class BountyCreateForm(forms.ModelForm):
    """Parent posts a one-off chore outside the weekly template cycle
    (tasks.md #15). ``point_value`` must be at least 1."""

    point_value = forms.IntegerField(min_value=1)

    class Meta:
        model = Bounty
        fields = ["title", "description", "point_value"]
