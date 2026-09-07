from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    """Show the role on the User admin page (tasks.md #4)."""

    model = Profile
    can_delete = False
    verbose_name_plural = "profile"
    # points_balance is ledger-owned (tasks.md #10) -- never hand-edited.
    readonly_fields = ("points_balance",)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "points_balance")
    list_editable = ("role",)
    list_select_related = ("user",)
    search_fields = ("user__username",)
    readonly_fields = ("points_balance",)


class UserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
