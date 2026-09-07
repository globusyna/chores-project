from django.contrib import admin

from .models import Perk, Purchase


@admin.register(Perk)
class PerkAdmin(admin.ModelAdmin):
    list_display = ("title", "point_cost", "active")
    list_editable = ("active",)
    list_filter = ("active",)
    search_fields = ("title",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("perk", "user", "status", "purchased_at", "fulfilled_by")
    list_filter = ("status",)
    search_fields = ("perk__title", "user__username")
    readonly_fields = ("purchased_at",)
