# paysim/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Transaction, WebHookLog


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les transactions.
    Permet de visualiser et gérer facilement toutes les transactions.
    """
    
    list_display = [
        'tx_id_short',
        'client_reference',
        'amount_display',
        'status_badge',
        'customer_email',
        'created_at',
        'processed_at',
        'view_webhooks',
    ]
    
    list_filter = [
        'status',
        'currency',
        'created_at',
        'processed_at',
    ]
    
    search_fields = [
        'tx_id',
        'client_reference',
        'customer_email',
        'ip_address',
    ]
    
    readonly_fields = [
        'tx_id',
        'secret_hash',
        'created_at',
        'updated_at',
        'processed_at',
        'ip_address',
        'redirect_link',
        'webhook_count',
    ]
    
    fieldsets = (
        ('Identifiants', {
            'fields': ('tx_id', 'client_reference', 'secret_hash')
        }),
        ('Informations Financières', {
            'fields': ('amount', 'currency', 'status')
        }),
        ('Client', {
            'fields': ('customer_email', 'callback_url', 'ip_address')
        }),
        ('Traitement', {
            'fields': ('created_at', 'updated_at', 'processed_at', 'failure_reason')
        }),
        ('Actions', {
            'fields': ('redirect_link', 'webhook_count'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    
    actions = ['mark_as_cancelled']
    
    def tx_id_short(self, obj):
        """Affiche une version courte du tx_id"""
        return str(obj.tx_id)[:8] + "..."
    tx_id_short.short_description = "ID Transaction"
    
    def amount_display(self, obj):
        """Affiche le montant avec la devise"""
        return f"{obj.amount} {obj.currency}"
    amount_display.short_description = "Montant"
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        """Affiche le statut avec une couleur"""
        colors = {
            'PENDING': '#ffc107',    # Jaune
            'SUCCESS': '#28a745',    # Vert
            'FAILED': '#dc3545',     # Rouge
            'CANCELLED': '#6c757d',  # Gris
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    status_badge.admin_order_field = 'status'
    
    def redirect_link(self, obj):
        """Affiche un lien cliquable vers la page de simulation"""
        if obj.is_pending:
            url = reverse('paysim:payment_redirect', args=[obj.tx_id])
            return format_html(
                '<a href="{}" target="_blank" style="color: #007bff;">'
                '🔗 Ouvrir la page de simulation</a>',
                url
            )
        return "Transaction déjà traitée"
    redirect_link.short_description = "Lien de redirection"
    
    def webhook_count(self, obj):
        """Affiche le nombre de WebHooks envoyés"""
        count = obj.webhook_logs.count()
        if count > 0:
            return format_html(
                '<a href="{}?transaction__tx_id={}">{} WebHook(s)</a>',
                reverse('admin:paysim_webhooklog_changelist'),
                obj.tx_id,
                count
            )
        return "Aucun WebHook"
    webhook_count.short_description = "WebHooks envoyés"
    
    def view_webhooks(self, obj):
        """Bouton pour voir les WebHooks"""
        count = obj.webhook_logs.count()
        if count > 0:
            url = reverse('admin:paysim_webhooklog_changelist')
            return format_html(
                '<a class="button" href="{}?transaction__tx_id={}">'
                '📨 {} WebHook(s)</a>',
                url,
                obj.tx_id,
                count
            )
        return "-"
    view_webhooks.short_description = "Logs"
    
    def mark_as_cancelled(self, request, queryset):
        """Action pour annuler des transactions en masse"""
        updated = queryset.filter(status='PENDING').update(status='CANCELLED')
        self.message_user(
            request,
            f"{updated} transaction(s) annulée(s) avec succès."
        )
    mark_as_cancelled.short_description = "Annuler les transactions sélectionnées"


@admin.register(WebHookLog)
class WebHookLogAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les logs de WebHooks.
    Utile pour le debugging et l'audit.
    """
    
    list_display = [
        'id',
        'transaction_link',
        'url_display',
        'success_badge',
        'status_code',
        'sent_at',
    ]
    
    list_filter = [
        'success',
        'status_code',
        'sent_at',
    ]
    
    search_fields = [
        'transaction__tx_id',
        'transaction__client_reference',
        'url',
    ]
    
    readonly_fields = [
        'transaction',
        'url',
        'payload',
        'signature',
        'status_code',
        'response_body',
        'success',
        'sent_at',
        'formatted_payload',
        'formatted_response',
    ]
    
    fieldsets = (
        ('Transaction', {
            'fields': ('transaction',)
        }),
        ('Requête WebHook', {
            'fields': ('url', 'formatted_payload', 'signature')
        }),
        ('Réponse', {
            'fields': ('status_code', 'formatted_response', 'success')
        }),
        ('Métadonnées', {
            'fields': ('sent_at',)
        }),
    )
    
    date_hierarchy = 'sent_at'
    
    def has_add_permission(self, request):
        """Empêche la création manuelle de logs"""
        return False
    
    def transaction_link(self, obj):
        """Affiche un lien vers la transaction associée"""
        url = reverse('admin:paysim_transaction_change', args=[obj.transaction.tx_id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            str(obj.transaction.tx_id)[:8] + "..."
        )
    transaction_link.short_description = "Transaction"
    
    def url_display(self, obj):
        """Affiche une version tronquée de l'URL"""
        if len(obj.url) > 50:
            return obj.url[:47] + "..."
        return obj.url
    url_display.short_description = "URL Destination"
    
    def success_badge(self, obj):
        """Affiche le statut de succès avec une couleur"""
        if obj.success:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">✓ Succès</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">✗ Échec</span>'
        )
    success_badge.short_description = "Statut"
    success_badge.admin_order_field = 'success'
    
    def formatted_payload(self, obj):
        """Affiche le payload formaté en JSON"""
        import json
        try:
            formatted = json.dumps(obj.payload, indent=2, ensure_ascii=False)
            return format_html('<pre style="background: #f5f5f5; padding: 10px;">{}</pre>', formatted)
        except:
            return str(obj.payload)
    formatted_payload.short_description = "Payload (formaté)"
    
    def formatted_response(self, obj):
        """Affiche la réponse formatée"""
        if obj.response_body:
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; max-height: 300px; overflow: auto;">{}</pre>',
                obj.response_body
            )
        return "Aucune réponse"
    formatted_response.short_description = "Réponse (formatée)"


# Personnalisation du site d'administration
admin.site.site_header = "PaySim API - Administration"
admin.site.site_title = "PaySim Admin"
admin.site.index_title = "Gestion des Transactions et WebHooks"