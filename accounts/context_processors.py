from .models import Profile


def points_balance(request):
    """Expose the signed-in user's point balance to every template so
    full-page loads render the current number (tasks.md #20).

    Nothing is added for anonymous users, so their pages have no balance
    element.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    try:
        return {"points_balance": user.profile.points_balance}
    except Profile.DoesNotExist:
        return {}
