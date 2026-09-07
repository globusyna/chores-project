"""Role-based access control helpers (tasks.md #5).

Usage::

    from accounts.permissions import parent_required, child_required

    @parent_required
    def review_queue(request):
        ...

    @child_required
    def my_claims(request):
        ...

Anonymous users are redirected to ``settings.LOGIN_URL`` (same as
``login_required``). An authenticated user whose role does not match ---
including one with no ``Profile`` --- gets an HTTP 403 via
``PermissionDenied``.

Class-based views can use ``ParentRequiredMixin`` / ``ChildRequiredMixin``.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

from .models import Profile


def _role_of(user):
    """The user's role, or ``None`` if they have no Profile."""
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return None


def _role_required(required_role):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if _role_of(request.user) != required_role:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


parent_required = _role_required(Profile.Role.PARENT)
child_required = _role_required(Profile.Role.CHILD)


class _RoleRequiredMixin(AccessMixin):
    required_role = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if _role_of(request.user) != self.required_role:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ParentRequiredMixin(_RoleRequiredMixin):
    required_role = Profile.Role.PARENT


class ChildRequiredMixin(_RoleRequiredMixin):
    required_role = Profile.Role.CHILD
