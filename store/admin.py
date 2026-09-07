from django.contrib import admin

from .models import Perk


@admin.register(Perk)
class PerkAdmin(admin.ModelAdmin):
    list_display = ("title", "point_cost", "active")
    list_editable = ("active",)
    list_filter = ("active",)
    search_fields = ("title",)
