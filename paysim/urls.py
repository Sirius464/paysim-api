# paysim/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'paysim'

# Router DRF pour le ViewSet
router = DefaultRouter()
router.register(r'transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    # Documentation racine
    path('', views.api_documentation, name='api_docs'),
    
    # PHASE 1 : Création de transaction
    path('create-order/', views.create_order, name='create_order'),
    
    # PHASE 2 : Redirection et simulation (vues Django non-API)
    path('redirect/<uuid:tx_id>/', views.payment_redirect_view, name='payment_redirect'),
    path('process/<uuid:tx_id>/', views.process_payment_simulation, name='process_payment'),
    
    # PHASE 3 : Réception de WebHook (endpoint démo)
    path('webhook/', views.webhook_receiver, name='webhook_receiver'),
    
    # Inclusion du router pour le ViewSet
    path('', include(router.urls)),
]