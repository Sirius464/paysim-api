# paysim/models.py
import uuid
import hmac
import hashlib
from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    """
    Modèle représentant une transaction de paiement simulée.
    Chaque transaction passe par les états : PENDING -> SUCCESS/FAILED
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('SUCCESS', 'Succès'),
        ('FAILED', 'Échec'),
        ('CANCELLED', 'Annulé'),
    ]
    
    CURRENCY_CHOICES = [
        ('XOF', 'Franc CFA'),
        ('USD', 'Dollar US'),
        ('EUR', 'Euro'),
    ]
    
    # Identifiants
    tx_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID Transaction"
    )
    
    client_reference = models.CharField(
        max_length=100,
        verbose_name="Référence Client",
        help_text="Référence de commande fournie par le client"
    )
    
    # Informations financières
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant"
    )
    
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='XOF',
        verbose_name="Devise"
    )
    
    # État et traçabilité
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Statut"
    )
    
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de création"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )
    
    # Sécurité - Clé secrète pour signature WebHook
    secret_hash = models.CharField(
        max_length=64,
        editable=False,
        verbose_name="Hash Secret"
    )
    
    # Métadonnées optionnelles
    customer_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Email Client"
    )
    
    callback_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="URL de Callback",
        help_text="URL où envoyer la notification WebHook"
    )
    
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="Adresse IP"
    )
    
    # Informations de traitement
    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date de traitement"
    )
    
    failure_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Raison de l'échec"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=['client_reference']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.tx_id} - {self.amount} {self.currency} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Génère le secret_hash lors de la première sauvegarde"""
        if not self.secret_hash:
            self.secret_hash = self.generate_secret_hash()
        super().save(*args, **kwargs)
    
    def generate_secret_hash(self):
        """
        Génère un hash secret unique pour cette transaction.
        Ce hash sera utilisé pour signer les notifications WebHook.
        """
        base_string = f"{self.tx_id}{self.amount}{self.currency}{timezone.now().isoformat()}"
        return hashlib.sha256(base_string.encode()).hexdigest()
    
    def generate_webhook_signature(self, payload_data):
        """
        Génère la signature HMAC-SHA256 pour le WebHook.
        
        Args:
            payload_data (dict): Données du payload à signer
            
        Returns:
            str: Signature hexadécimale
        """
        # Construire la chaîne à signer (ordre alphabétique des clés)
        sorted_items = sorted(payload_data.items())
        message = '&'.join([f"{k}={v}" for k, v in sorted_items])
        
        signature = hmac.new(
            self.secret_hash.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def verify_webhook_signature(tx_id, payload_data, received_signature):
        """
        Vérifie la signature d'un WebHook reçu.
        
        Args:
            tx_id (UUID): ID de la transaction
            payload_data (dict): Données du payload reçu
            received_signature (str): Signature reçue dans le WebHook
            
        Returns:
            bool: True si la signature est valide
        """
        try:
            transaction = Transaction.objects.get(tx_id=tx_id)
            expected_signature = transaction.generate_webhook_signature(payload_data)
            
            # Comparaison sécurisée contre les attaques de timing
            return hmac.compare_digest(expected_signature, received_signature)
        except Transaction.DoesNotExist:
            return False
    
    def mark_as_success(self):
        """Marque la transaction comme réussie"""
        self.status = 'SUCCESS'
        self.processed_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, reason=None):
        """Marque la transaction comme échouée"""
        self.status = 'FAILED'
        self.processed_at = timezone.now()
        if reason:
            self.failure_reason = reason
        self.save()
    
    @property
    def is_pending(self):
        """Vérifie si la transaction est en attente"""
        return self.status == 'PENDING'
    
    @property
    def is_finalized(self):
        """Vérifie si la transaction a un état final"""
        return self.status in ['SUCCESS', 'FAILED', 'CANCELLED']


class WebHookLog(models.Model):
    """
    Modèle pour logger tous les WebHooks envoyés.
    Utile pour le debugging et l'audit.
    """
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='webhook_logs'
    )
    
    url = models.URLField(verbose_name="URL Destination")
    
    payload = models.JSONField(verbose_name="Contenu du Payload")
    
    signature = models.CharField(
        max_length=64,
        verbose_name="Signature Envoyée"
    )
    
    status_code = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Code HTTP de Réponse"
    )
    
    response_body = models.TextField(
        blank=True,
        null=True,
        verbose_name="Corps de la Réponse"
    )
    
    success = models.BooleanField(
        default=False,
        verbose_name="Succès de l'Envoi"
    )
    
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'Envoi"
    )
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = "Log WebHook"
        verbose_name_plural = "Logs WebHook"
    
    def __str__(self):
        return f"WebHook {self.transaction.tx_id} - {self.sent_at}"