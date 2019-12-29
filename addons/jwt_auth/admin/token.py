from django.contrib import admin
from ..models import Token


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    list_display = ('id', 'subject', 'issued_at', 'expire_at', 'audience')
    fields = readonly_fields = list_display
