from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "school", "region", "is_active")
    list_filter = ("role", "school", "region", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Platform profile", {"fields": ("role", "school", "region")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Platform profile", {"fields": ("role", "school", "region")}),
    )
