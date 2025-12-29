🚀 PaySim API - Simulateur de Passerelle de Paiement

Un projet open-source démontrant l'architecture asynchrone des systèmes de paiement modernes

https://img.shields.io/badge/Django-6.0-green.svg
https://img.shields.io/badge/DRF-3.14-blue.svg
https://img.shields.io/badge/Python-3.12-yellow.svg
https://img.shields.io/badge/License-MIT-blue.svg
https://img.shields.io/badge/Tests-85%25%20passing-success

---

📖 Table des Matières

· 🚀 Aperçu
· 🎯 Objectif
· 📐 Architecture
· 🔒 Sécurité
· 🚀 Installation Rapide
· 📖 Guide d'Utilisation
· 🛠️ Endpoints API
· 🧪 Tests
· 📊 Tableau de Bord
· 🔧 Configuration
· 🌍 Déploiement
· 🤝 Contribution
· 📝 License
· 👨‍💻 Auteur

---

🚀 Aperçu

PaySim API est un simulateur complet de passerelle de paiement construit avec Django et Django REST Framework. Il reproduit fidèlement le flux asynchrone des systèmes de paiement modernes (type Stripe, PayPal) avec une sécurité cryptographique robuste (HMAC-SHA256).

Fonctionnalités principales :

· ✅ Flux de paiement en 3 phases (création, redirection, notification)
· ✅ Interface de simulation élégante et responsive
· ✅ Signature HMAC-SHA256 pour tous les webhooks
· ✅ Logs complets et audit des transactions
· ✅ Validation stricte des données d'entrée
· ✅ Documentation API interactive

---

🎯 Objectif

Ce projet démontre l'architecture complexe des systèmes de paiement tout en restant simple à comprendre et à déployer. Il est parfait pour :

· Apprentissage : Comprendre les flux de paiement asynchrones
· Tests : Tester l'intégration de paiement sans frais réels
· Prototypage : Développer rapidement des fonctionnalités e-commerce
· Portfolio : Montrer ses compétences en développement backend sécurisé

Note pédagogique : Ce projet est conçu pour l'apprentissage. Consultez PRODUCTION_CONSIDERATIONS.md pour des recommandations de déploiement en production.

---

📐 Architecture

Flux de Transaction

```
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   Client     │          │  PaySim API  │          │  Client App  │
│  Frontend    │          │   Backend    │          │   Backend    │
└──────┬───────┘          └──────┬───────┘          └──────┬───────┘
       │                         │                         │
       │  1. POST /create-order  │                         │
       ├────────────────────────>│                         │
       │                         │                         │
       │  ← tx_id, redirect_url  │                         │
       │<────────────────────────┤                         │
       │                         │                         │
       │  2. GET /redirect/{id}  │                         │
       ├────────────────────────>│                         │
       │                         │                         │
       │  ← HTML Payment Form    │                         │
       │<────────────────────────┤                         │
       │                         │                         │
       │  3. User clicks SUCCESS │                         │
       ├────────────────────────>│                         │
       │                         │                         │
       │                         │  4. POST /webhook       │
       │                         │  (with HMAC signature)  │
       │                         ├────────────────────────>│
       │                         │                         │
       │                         │  ← 200 OK (verified)    │
       │                         │<────────────────────────┤
       │                         │                         │
```

Modèles de Données

```python
# Transaction (paysim/models.py)
class Transaction(models.Model):
    tx_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_reference = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    secret_hash = models.CharField(max_length=64)  # HMAC key
    callback_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True)
```

---

🔒 Sécurité

Signature HMAC-SHA256

Chaque transaction génère un secret_hash unique utilisé pour signer les webhooks :

```python
# Génération de la signature
def generate_signature(payload, secret_hash):
    # Tri alphabétique des clés pour la consistance
    sorted_items = sorted(payload.items())
    message = '&'.join([f"{k}={v}" for k, v in sorted_items])
    
    return hmac.new(
        secret_hash.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
```

Validation Côté Client

```python
# Dans votre application cliente
import hmac
import hashlib

def verify_webhook_signature(payload, secret_hash):
    received_signature = payload.pop('signature')
    
    # Recréer le message exact
    sorted_items = sorted(payload.items())
    message = '&'.join([f"{k}={v}" for k, v in sorted_items])
    
    # Calculer la signature attendue
    expected_signature = hmac.new(
        secret_hash.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(received_signature, expected_signature)
```

---

🚀 Installation Rapide

Prérequis

· Python 3.10+
· Django 6.0+
· Django REST Framework

Installation en 5 minutes

```bash
# 1. Cloner le projet
git clone https://github.com/Sirius464/paysim-api.git
cd paysim-api

# 2. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install django djangorestframework

# 4. Configurer la base de données
python manage.py migrate

# 5. Lancer le serveur
python manage.py runserver
```

L'API est maintenant accessible sur http://localhost:8000/api/paysim/

---

📖 Guide d'Utilisation

1. Créer une Transaction

```bash
curl -X POST http://localhost:8000/api/paysim/create-order/ \
  -H "Content-Type: application/json" \
  -d '{
    "client_reference": "CMD-2024-001",
    "amount": 15000,
    "currency": "XOF",
    "customer_email": "client@exemple.com",
    "callback_url": "https://votre-app.com/webhook"
  }'
```

Réponse :

```json
{
  "tx_id": "f0b5804e-6c28-4549-b158-605d0af36e79",
  "client_reference": "CMD-2024-001",
  "amount": "15000.00",
  "currency": "XOF",
  "status": "PENDING",
  "created_at": "2025-12-28T22:28:25.895775Z",
  "redirect_url": "http://localhost:8000/api/paysim/redirect/f0b5804e-6c28-4549-b158-605d0af36e79/"
}
```

2. Simuler le Paiement

Ouvrez l'URL redirect_url dans votre navigateur :

docs/screenshots/simulation-interface.png

Cliquez sur :

· ✅ Succès : Simule un paiement réussi
· ❌ Échec : Simule un paiement refusé

3. Recevoir le Webhook

Après simulation, PaySim envoie un webhook signé à votre callback_url :

```json
{
  "tx_id": "f0b5804e-6c28-4549-b158-605d0af36e79",
  "client_reference": "CMD-2024-001",
  "amount": "15000.00",
  "currency": "XOF",
  "status": "SUCCESS",
  "processed_at": "2025-12-28T22:28:30.123456Z",
  "signature": "a3c8f9e2d1b4c7e5f8a9b6c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3"
}
```

⚠️ IMPORTANT : Validez toujours la signature avant de traiter le webhook !

---

🛠️ Endpoints API

Méthode Endpoint Description Authentification
GET /api/paysim/ Documentation interactive Aucune
POST /api/paysim/create-order/ Créer une transaction Aucune
GET /api/paysim/redirect/{tx_id}/ Interface de simulation Aucune
GET /api/paysim/transactions/ Lister les transactions Aucune
GET /api/paysim/transactions/{tx_id}/ Détails transaction Aucune
POST /api/paysim/webhook/ Réception webhook (démo) HMAC-SHA256
POST /api/paysim/process/{tx_id}/ Traitement simulation (interne) Aucune

---

🧪 Tests

Le projet inclut une suite de tests complète :

Exécuter tous les tests

```bash
python test.py
```

Résultats des tests

```
============================================================
  🚀 TESTS PaySim API
============================================================
🧪 TEST 1 : API Root - Documentation ✅
🧪 TEST 2 : Création de Transaction ✅
🧪 TEST 3 : Consultation Statut Transaction ✅
🧪 TEST 4 : Liste des Transactions ✅
🧪 TEST 5 : Validation Signature WebHook ✅
🧪 TEST 6 : Vérification WebHook.site ✅
🧪 TEST 7 : Cas Limites et Validation ✅ 3/3

📊 RÉSUMÉ DES TESTS
   Tests exécutés : 7
   Tests réussis  : 6
   Taux de succès : 85.7%
============================================================
```

Tests unitaires Django

```bash
python manage.py test paysim
```

---

📊 Tableau de Bord

Statistiques API

· Transactions totales : 19 (dans notre exemple)
· Succès : 42%
· En attente : 32%
· Échecs : 26%

Monitoring des Webhooks

Tous les webhooks sont loggés avec :

· Statut HTTP reçu
· Payload envoyé
· Timestamp d'envoi
· Succès/échec

```python
# Accéder aux logs d'une transaction
GET /api/paysim/transactions/{tx_id}/webhook_logs/
```

---

🔧 Configuration

Variables d'Environnement

Créez un fichier .env :

```env
DEBUG=True
SECRET_KEY=votre-cle-secrete
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

Configuration Django

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'paysim',  # Notre application
]

# Configuration REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
}
```

---

🌍 Déploiement

Déploiement Rapide sur PythonAnywhere

1. Créez un compte sur PythonAnywhere
2. Téléversez votre code via Git
3. Configurez l'application web
4. Mettez à jour ALLOWED_HOSTS
5. Migrez la base de données

Déploiement avec Docker

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "paysim_project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```bash
# Lancer avec Docker Compose
docker-compose up -d
```

---

🤝 Contribution

Les contributions sont les bienvenues ! Voici comment participer :

1. Fork le projet
2. Créez une branche pour votre fonctionnalité
   ```bash
   git checkout -b feature/ma-fonctionnalite
   ```
3. Commitez vos changements
   ```bash
   git commit -m 'Ajout de ma fonctionnalité'
   ```
4. Push vers la branche
   ```bash
   git push origin feature/ma-fonctionnalite
   ```
5. Ouvrez une Pull Request

Guide de contribution

· Suivez le style de code existant
· Ajoutez des tests pour les nouvelles fonctionnalités
· Mettez à jour la documentation
· Assurez-vous que tous les tests passent

---

📝 License

Ce projet est sous licence MIT. Vous êtes libre de :

· Utiliser, copier, modifier, fusionner, publier
· Distribuer des copies du logiciel
· Utiliser le logiciel à des fins commerciales

Limitations :

· La licence n'offre aucune garantie
· Vous devez inclure la notice de copyright dans toutes les copies

Voir le fichier LICENSE pour plus de détails.

---

👨‍💻 Auteur

Clarel GNIMADI

· GitHub: @Sirius464
· LinkedIn: Clarel GNIMADI
· Email: Clarelbamigbe@gmail.com

Remerciements

· Django et Django REST Framework teams
· La communauté open-source
· Tous les contributeurs

---

🚀 Prochaines Évolutions

· Interface d'administration améliorée
· Support de devises supplémentaires
· Système de retry automatique pour les webhooks
· Analytics et rapports
· SDK client pour Python/JavaScript
· Documentation OpenAPI/Swagger
· Tests de charge et performance

---

📞 Support

· Issues GitHub : Signaler un bug
· Discussions : Forum de discussion

---

"Zéro Franc. Maximum Impact." - PaySim API

---

Dernière mise à jour : Décembre 2025
