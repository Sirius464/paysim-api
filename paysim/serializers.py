from rest_framework import serializers
from .models import Transaction, WebHookLog


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'une nouvelle transaction.
    """
    
    class Meta:
        model = Transaction
        fields = [
            'client_reference',
            'amount',
            'currency',
            'customer_email',
            'callback_url',
        ]
        extra_kwargs = {
            'callback_url': {'required': True},
        }
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Le montant doit être supérieur à zéro."
            )
        return value
    
    def validate_callback_url(self, value):
        if not value:
            raise serializers.ValidationError(
                "L'URL de callback est obligatoire."
            )
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                validated_data['ip_address'] = x_forwarded_for.split(',')[0]
            else:
                validated_data['ip_address'] = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        return super().create(validated_data)


class TransactionResponseSerializer(serializers.ModelSerializer):
    """
    Serializer pour la réponse après création.
    """
    
    redirect_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'tx_id',
            'client_reference',
            'amount',
            'currency',
            'status',
            'created_at',
            'redirect_url',
        ]
        # ✅ CORRECTION : Liste au lieu de string
        read_only_fields = ['tx_id', 'status', 'created_at']
    
    def get_redirect_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(
                f'/api/paysim/redirect/{obj.tx_id}/'
            )
        return f'/api/paysim/redirect/{obj.tx_id}/'


class TransactionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les détails.
    """
    
    class Meta:
        model = Transaction
        fields = [
            'tx_id',
            'client_reference',
            'amount',
            'currency',
            'status',
            'customer_email',
            'callback_url',
            'ip_address',
            'created_at',
            'updated_at',
            'processed_at',
            'failure_reason',
        ]
        # ✅ CORRECTION : Tous les champs en read-only pour consultation
        read_only_fields = fields  # Tous les champs sont read-only


class WebHookPayloadSerializer(serializers.Serializer):
    """
    Serializer pour le payload du WebHook.
    """
    
    tx_id = serializers.UUIDField()
    client_reference = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.ChoiceField(choices=['SUCCESS', 'FAILED'])
    processed_at = serializers.DateTimeField()
    signature = serializers.CharField()
    failure_reason = serializers.CharField(required=False, allow_blank=True)


class WebHookReceiveSerializer(serializers.Serializer):
    """
    Serializer pour recevoir et valider un WebHook.
    """
    
    tx_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=['SUCCESS', 'FAILED'])
    signature = serializers.CharField()
    failure_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        tx_id = data.get('tx_id')
        signature = data.get('signature')
        
        payload_data = {
            'tx_id': str(tx_id),
            'status': data.get('status'),
        }
        
        if 'failure_reason' in data:
            payload_data['failure_reason'] = data.get('failure_reason')
        
        is_valid = Transaction.verify_webhook_signature(
            tx_id=tx_id,
            payload_data=payload_data,
            received_signature=signature
        )
        
        if not is_valid:
            raise serializers.ValidationError({
                'signature': 'Signature invalide.'
            })
        
        return data


class WebHookLogSerializer(serializers.ModelSerializer):
    """
    Serializer pour les logs de WebHooks.
    """
    
    transaction_id = serializers.UUIDField(source='transaction.tx_id', read_only=True)
    
    class Meta:
        model = WebHookLog
        fields = [
            'id',
            'transaction_id',
            'url',
            'payload',
            'signature',
            'status_code',
            'response_body',
            'success',
            'sent_at',
        ]
        # ✅ CORRECTION : Liste complète des champs read-only
        read_only_fields = fields  # Tous les champs


class TransactionStatusSerializer(serializers.Serializer):
    """
    Serializer pour les mises à jour de statut.
    """
    
    status = serializers.ChoiceField(choices=['SUCCESS', 'FAILED'])
    failure_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data.get('status') == 'FAILED' and not data.get('failure_reason'):
            raise serializers.ValidationError({
                'failure_reason': 'Une raison doit être fournie en cas d\'échec.'
            })
        return data