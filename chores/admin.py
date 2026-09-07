from django.contrib import admin

from .models import Bounty, ChoreTemplate


@admin.register(ChoreTemplate)
class ChoreTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "default_point_value", "active")
    list_editable = ("active",)
    list_filter = ("active",)
    search_fields = ("title",)


@admin.register(Bounty)
class BountyAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "point_value", "claimed_by")
    list_filter = ("status",)
    search_fields = ("title",)
    autocomplete_fields = ("source_template",)
    readonly_fields = ("created_at",)
