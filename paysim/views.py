# paysim/views.py
import requests
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Transaction, WebHookLog
from .serializers import (
    TransactionCreateSerializer,
    TransactionResponseSerializer,
    TransactionDetailSerializer,
    WebHookReceiveSerializer,
    WebHookLogSerializer,
    TransactionStatusSerializer,
)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour consulter les transactions.
    
    Endpoints:
    - GET /api/paysim/transactions/ : Liste toutes les transactions
    - GET /api/paysim/transactions/{tx_id}/ : Détails d'une transaction
    """
    
    queryset = Transaction.objects.all()
    serializer_class = TransactionDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'tx_id'
    
    def get_queryset(self):
        """Permet de filtrer par statut ou référence client"""
        queryset = super().get_queryset()
        
        # Filtrage par statut
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filtrage par référence client
        client_ref = self.request.query_params.get('client_reference', None)
        if client_ref:
            queryset = queryset.filter(client_reference=client_ref)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def webhook_logs(self, request, tx_id=None):
        """
        Retourne les logs de WebHooks pour une transaction donnée.
        Endpoint: GET /api/paysim/transactions/{tx_id}/webhook_logs/
        """
        transaction = self.get_object()
        logs = transaction.webhook_logs.all()
        serializer = WebHookLogSerializer(logs, many=True)
        return Response(serializer.data)


@api_view(['POST'])
def create_order(request):
    """
    PHASE 1 : Création d'une transaction
    
    Endpoint: POST /api/paysim/create-order/
    
    Body (JSON):
    {
        "client_reference": "ORDER-12345",
        "amount": 25000,
        "currency": "XOF",
        "customer_email": "client@example.com",
        "callback_url": "https://client-app.com/payment/webhook"
    }
    
    Response (201):
    {
        "tx_id": "uuid-here",
        "client_reference": "ORDER-12345",
        "amount": "25000.00",
        "currency": "XOF",
        "status": "PENDING",
        "created_at": "2025-01-15T10:30:00Z",
        "redirect_url": "http://localhost:8000/paysim/redirect/uuid-here/"
    }
    """
    
    serializer = TransactionCreateSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        transaction = serializer.save()
        
        response_serializer = TransactionResponseSerializer(
            transaction,
            context={'request': request}
        )
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


def payment_redirect_view(request, tx_id):
    """
    PHASE 2 : Page de simulation de paiement
    
    Vue Django simple (non-API) qui affiche un formulaire permettant
    de simuler le succès ou l'échec du paiement.
    
    URL: GET /paysim/redirect/{tx_id}/
    """
    
    transaction = get_object_or_404(Transaction, tx_id=tx_id)
    
    # Vérifier que la transaction est toujours en attente
    if transaction.is_finalized:
        return render(request, 'paysim/already_processed.html', {
            'transaction': transaction
        })
    
    context = {
        'transaction': transaction,
    }
    
    return render(request, 'paysim/payment_form.html', context)



@csrf_exempt
@api_view(['POST'])
def process_payment_simulation(request, tx_id):
    """
    Endpoint interne appelé par le formulaire de simulation.
    
    Endpoint: POST /paysim/process/{tx_id}/
    
    Body (JSON):
    {
        "status": "SUCCESS",  // ou "FAILED"
        "failure_reason": "Carte expirée"  // optionnel, requis si FAILED
    }
    """
    
    transaction = get_object_or_404(Transaction, tx_id=tx_id)
    
    # Vérifier que la transaction n'est pas déjà finalisée
    if transaction.is_finalized:
        return Response(
            {'error': 'Cette transaction a déjà été traitée.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = TransactionStatusSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    payment_status = serializer.validated_data['status']
    failure_reason = serializer.validated_data.get('failure_reason', '')
    
    # Mettre à jour la transaction
    if payment_status == 'SUCCESS':
        transaction.mark_as_success()
    else:
        transaction.mark_as_failed(reason=failure_reason)
    
    # PHASE 3 : Envoyer le WebHook au client
    send_webhook_notification(transaction)
    
    return Response({
        'success': True,
        'tx_id': transaction.tx_id,
        'status': transaction.status,
        'message': f'Transaction {transaction.status.lower()}. WebHook envoyé.'
    })


def send_webhook_notification(transaction):
    """
    PHASE 3 : Envoie la notification WebHook au client.
    
    Cette fonction construit le payload, le signe avec le secret_hash,
    et envoie une requête POST à l'URL de callback du client.
    """
    
    if not transaction.callback_url:
        return
    
    # Construction du payload
    payload = {
        'tx_id': str(transaction.tx_id),
        'client_reference': transaction.client_reference,
        'amount': str(transaction.amount),
        'currency': transaction.currency,
        'status': transaction.status,
        'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None,
    }
    
    if transaction.failure_reason:
        payload['failure_reason'] = transaction.failure_reason
    
    # Génération de la signature
    signature = transaction.generate_webhook_signature(payload)
    payload['signature'] = signature
    
    # Création du log avant l'envoi
    webhook_log = WebHookLog.objects.create(
        transaction=transaction,
        url=transaction.callback_url,
        payload=payload,
        signature=signature
    )
    
    try:
        # Envoi du WebHook avec timeout de 10 secondes
        response = requests.post(
            transaction.callback_url,
            json=payload,
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        # Mise à jour du log avec la réponse
        webhook_log.status_code = response.status_code
        webhook_log.response_body = response.text[:1000]  # Limite à 1000 caractères
        webhook_log.success = (200 <= response.status_code < 300)
        webhook_log.save()
        
    except requests.RequestException as e:
        # En cas d'erreur réseau
        webhook_log.success = False
        webhook_log.response_body = f"Erreur: {str(e)}"
        webhook_log.save()


@api_view(['POST'])
def webhook_receiver(request):
    """
    Endpoint de démonstration pour recevoir un WebHook.
    
    Dans une vraie application cliente, c'est cet endpoint que vous
    implémenterez pour recevoir les notifications de PaySim.
    
    Endpoint: POST /api/paysim/webhook/
    
    Body (JSON):
    {
        "tx_id": "uuid-here",
        "client_reference": "ORDER-12345",
        "amount": "25000.00",
        "currency": "XOF",
        "status": "SUCCESS",
        "processed_at": "2025-01-15T10:35:00Z",
        "signature": "signature-hex-here"
    }
    
    IMPORTANT : Ce endpoint valide la signature avant d'accepter le WebHook.
    """
    
    serializer = WebHookReceiveSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {
                'success': False,
                'error': 'Signature invalide ou données incorrectes',
                'details': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Si la validation passe, la signature est correcte
    tx_id = serializer.validated_data['tx_id']
    
    return Response({
        'success': True,
        'message': f'WebHook accepté pour la transaction {tx_id}',
        'verified': True
    })


@api_view(['GET'])
def api_documentation(request):
    """
    Endpoint racine fournissant une documentation interactive.
    
    Endpoint: GET /api/paysim/
    """
    
    docs = {
        'name': 'PaySim API',
        'version': '1.0.0',
        'description': 'Simulateur de passerelle de paiement avec flux asynchrone',
        'endpoints': {
            'create_order': {
                'method': 'POST',
                'url': '/api/paysim/create-order/',
                'description': 'PHASE 1 - Créer une nouvelle transaction de paiement',
                'authentication': 'Aucune (pour la démo)',
            },
            'payment_form': {
                'method': 'GET',
                'url': '/api/paysim/redirect/{tx_id}/',
                'description': 'PHASE 2 - Interface de simulation du paiement',
                'type': 'Page HTML'
            },
            'webhook': {
                'method': 'POST',
                'url': '/api/paysim/webhook/',
                'description': 'PHASE 3 - Recevoir les notifications de paiement',
                'authentication': 'Signature HMAC-SHA256',
            },
            'transactions': {
                'method': 'GET',
                'url': '/api/paysim/transactions/',
                'description': 'Lister toutes les transactions',
            },
            'transaction_detail': {
                'method': 'GET',
                'url': '/api/paysim/transactions/{tx_id}/',
                'description': 'Détails d\'une transaction spécifique',
            },
        },
        'security': {
            'signature_algorithm': 'HMAC-SHA256',
            'signature_key': 'secret_hash (unique par transaction)',
            'verification': 'Utilisez Transaction.verify_webhook_signature()'
        }
    }
    
    return Response(docs)