from django.contrib import admin

from .models import PointTransaction


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    """Read-only: the ledger is append-only and only ``record_transaction``
    may write to it (tasks.md #10)."""

    list_display = (
        "created_at",
        "user",
        "amount",
        "reason",
        "related_bounty",
        "related_purchase",
    )
    list_filter = ("reason",)
    search_fields = ("user__username",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
