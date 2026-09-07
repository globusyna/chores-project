from django.contrib import admin

from .models import ChoreTemplate


@admin.register(ChoreTemplate)
class ChoreTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "default_point_value", "active")
    list_editable = ("active",)
    list_filter = ("active",)
    search_fields = ("title",)
