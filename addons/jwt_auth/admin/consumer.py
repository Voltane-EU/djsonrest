from django.contrib import admin, messages
from django import forms
from django.utils.translation import gettext_lazy as _, gettext
from django.core.exceptions import PermissionDenied
from django.http.response import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from djutils.admin import one_to_many_link
from djutils.crypt import random_string_generator
from ..models import Consumer, ConsumerIPRule


class AdminCosumerChangeKeyForm(forms.Form):
    key = forms.CharField(
        label=_("Key"),
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'autofous': True,
            'readonly': True,
            'style': 'width: 100%; box-sizing: border-box; font-family: monospace;',
        }),
        initial=lambda: random_string_generator(size=128),
        help_text='Copy the key and note it, you wont be able to see it again',
    )

    def __init__(self, consumer, *args, **kwargs):
        self.consumer = consumer
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        self.consumer.set_key(self.cleaned_data["key"])
        if commit:
            self.consumer.save()
        return self.consumer


class ConsumerIPRuleInline(admin.TabularInline):
    model = ConsumerIPRule
    fiels = ('ip', 'type',)
    extra = 1


@admin.register(Consumer)
class ConsumerAdmin(admin.ModelAdmin):
    def name(self, obj=None):
        if not obj:
            return
        return obj.user.username

    change_key_form = AdminCosumerChangeKeyForm

    def get_urls(self):
        return [
            path(
                '<id>/change_key/',
                self.admin_site.admin_view(self.consumer_change_password),
                name='djsonrest_addons_jwt_auth_consumer_key_change',
            ),
        ] + super().get_urls()

    def change_key_link(self, obj=None):
        if not obj:
            return ""
        url = reverse('admin:djsonrest_addons_jwt_auth_consumer_key_change', args=[str(obj.pk)])
        return format_html('<a class="button" href="{}">Change Key</a>&nbsp;', url)

    change_key_link.short_description = _('Actions')

    def consumer_change_password(self, request, id, form_url=''):
        consumer = self.get_object(request, id)
        if not self.has_change_permission(request, consumer):
            raise PermissionDenied

        if consumer is None:
            raise Http404

        if request.method == 'POST':
            form = self.change_key_form(consumer, request.POST)
            if form.is_valid():
                form.save()
                msg = gettext('Key changed successfully.')
                messages.success(request, msg)
                return HttpResponseRedirect(
                    reverse(
                        '%s:%s_%s_change' % (
                            self.admin_site.name,
                            consumer._meta.app_label,
                            consumer._meta.model_name,
                        ),
                        args=(consumer.pk,),
                    )
                )
        else:
            form = self.change_key_form(consumer)

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['form'] = form
        context['consumer'] = consumer
        context['title'] = _('Change Consumer Key')

        return TemplateResponse(request, 'admin/consumer_change_key.html', context)

    tokens_link = one_to_many_link('tokens', 'consumer', description='Tokens', link='Show')
    list_display = ('uid', 'name',)
    fieldsets = (
        (_('General'), {'fields': ('uid', 'user', 'change_key_link',)}),
        (_('Access Control'), {'fields': ('ip_rules_active', 'tokens_link',)}),
    )
    readonly_fields = ('uid', 'name', 'tokens_link', 'change_key_link',)

    inlines = [
        ConsumerIPRuleInline,
    ]
