import requests
import json
import time
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# URL de base de votre serveur Django
# Si vous testez sur le même téléphone: http://127.0.0.1:8000
# Si depuis un autre appareil: http://192.168.X.X:8000 (votre IP WiFi)
BASE_URL = "http://127.0.0.1:8000"

# Votre URL WebHook unique
WEBHOOK_URL = "https://webhook.site/4b3df3d7-4e1a-43e0-b845-5474aaff81f1"

# Couleurs pour terminal (optionnel)
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def print_header(text):
    """Affiche un header formaté."""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_test(number, name):
    """Affiche le nom du test."""
    print()
    print(f"{BLUE}🧪 TEST {number} : {name}{RESET}")
    print("-" * 60)

def print_success(message):
    """Affiche un message de succès."""
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    """Affiche un message d'erreur."""
    print(f"{RED}❌ {message}{RESET}")

def print_warning(message):
    """Affiche un avertissement."""
    print(f"{YELLOW}⚠️  {message}{RESET}")

def print_info(key, value):
    """Affiche une information clé-valeur."""
    print(f"   {key}: {value}")

# ============================================================================
# TESTS
# ============================================================================

def test_1_api_root():
    """Test 1 : Vérifier que l'API est accessible."""
    print_test(1, "API Root - Documentation")
    
    try:
        response = requests.get(f"{BASE_URL}/api/paysim/", timeout=5)
        
        if response.status_code == 200:
            print_success("API accessible")
            data = response.json()
            
            if 'name' in data:
                print_info("Nom API", data['name'])
            if 'version' in data:
                print_info("Version", data['version'])
            
            print()
            print("📄 Documentation complète:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            return True
        else:
            print_error(f"Code de statut inattendu: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Impossible de se connecter au serveur")
        print_info("Vérifiez", "1. Serveur Django lancé (python manage.py runserver)")
        print_info("", "2. URL correcte dans BASE_URL")
        print_info("", "3. Port 8000 ouvert")
        return False
    except Exception as e:
        print_error(f"Erreur inattendue: {str(e)}")
        return False


def test_2_create_transaction():
    """Test 2 : Créer une nouvelle transaction."""
    print_test(2, "Création de Transaction")
    
    # Générer référence unique
    timestamp = int(time.time())
    client_ref = f"TEST-ORDER-{timestamp}"
    
    payload = {
        "client_reference": client_ref,
        "amount": 15000,
        "currency": "XOF",
        "customer_email": "test@paysim.com",
        "callback_url": WEBHOOK_URL
    }
    
    print("📤 Envoi de la requête...")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/paysim/create-order/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 201:
            print_success("Transaction créée avec succès")
            data = response.json()
            
            print_info("Transaction ID", data.get('tx_id', 'N/A'))
            print_info("Statut", data.get('status', 'N/A'))
            print_info("Montant", f"{data.get('amount', 'N/A')} {data.get('currency', 'N/A')}")
            print_info("URL Redirection", data.get('redirect_url', 'N/A'))
            
            print()
            print("🔗 Pour tester la simulation, ouvrez dans un navigateur:")
            print(f"   {data.get('redirect_url', 'N/A')}")
            
            return data.get('tx_id')
            
        elif response.status_code == 400:
            print_error("Requête invalide (400 Bad Request)")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return None
        else:
            print_error(f"Code de statut inattendu: {response.status_code}")
            print(response.text)
            return None
            
    except requests.exceptions.Timeout:
        print_error("Timeout - Le serveur met trop de temps à répondre")
        return None
    except Exception as e:
        print_error(f"Erreur: {str(e)}")
        return None


def test_3_transaction_status(tx_id):
    """Test 3 : Consulter le statut d'une transaction."""
    if not tx_id:
        print_warning("Test 3 ignoré (pas de transaction créée)")
        return False
    
    print_test(3, f"Consultation Statut Transaction")
    print_info("TX ID", tx_id[:8] + "...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/paysim/transactions/{tx_id}/",
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("Statut récupéré")
            data = response.json()
            
            print_info("Référence Client", data.get('client_reference', 'N/A'))
            print_info("Montant", f"{data.get('amount', 'N/A')} {data.get('currency', 'N/A')}")
            print_info("Statut", data.get('status', 'N/A'))
            print_info("Date Création", data.get('created_at', 'N/A'))
            
            if data.get('processed_at'):
                print_info("Date Traitement", data.get('processed_at'))
            
            return True
            
        elif response.status_code == 404:
            print_error("Transaction non trouvée")
            return False
        else:
            print_error(f"Code de statut inattendu: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {str(e)}")
        return False


def test_4_list_transactions():
    """Test 4 : Lister toutes les transactions."""
    print_test(4, "Liste des Transactions")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/paysim/transactions/",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Gérer pagination DRF
            if isinstance(data, dict) and 'results' in data:
                transactions = data['results']
                count = data.get('count', len(transactions))
            else:
                transactions = data if isinstance(data, list) else []
                count = len(transactions)
            
            print_success(f"{count} transaction(s) trouvée(s)")
            
            if transactions:
                print()
                print("📋 Dernières transactions:")
                for i, tx in enumerate(transactions[:5], 1):
                    print(f"   {i}. {tx.get('client_reference', 'N/A')} - "
                          f"{tx.get('amount', 'N/A')} {tx.get('currency', 'N/A')} - "
                          f"{tx.get('status', 'N/A')}")
            
            return True
        else:
            print_error(f"Code de statut inattendu: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {str(e)}")
        return False


def test_5_signature_validation():
    """Test 5 : Vérifier la validation de signature WebHook."""
    print_test(5, "Validation Signature WebHook")
    
    # Payload de test avec signature invalide
    fake_payload = {
        "tx_id": "00000000-0000-0000-0000-000000000000",
        "status": "SUCCESS",
        "signature": "INVALID_SIGNATURE_FOR_TESTING"
    }
    
    print("📤 Envoi d'un WebHook avec signature invalide...")
    print(json.dumps(fake_payload, indent=2))
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/paysim/webhook/",
            json=fake_payload,
            timeout=5
        )
        
        if response.status_code == 400:
            print_success("Signature invalide correctement rejetée")
            data = response.json()
            print_info("Raison", data.get('error', 'N/A'))
            return True
            
        elif response.status_code == 200:
            print_warning("Signature acceptée (vérifier la logique de validation)")
            return False
        else:
            print_error(f"Code de statut inattendu: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erreur: {str(e)}")
        return False


def test_6_webhook_sent():
    """Test 6 : Vérifier qu'on peut voir les WebHooks envoyés."""
    print_test(6, "Vérification WebHook.site")
    
    print("🌐 Ouvrez dans un navigateur:")
    print(f"   {WEBHOOK_URL}")
    print()
    print("📝 Instructions:")
    print("   1. Créez une transaction (Test 2)")
    print("   2. Ouvrez l'URL de redirection dans un navigateur")
    print("   3. Cliquez sur 'Succès' ou 'Échec'")
    print("   4. Vérifiez que le WebHook apparaît sur webhook.site")
    print()
    print("✅ Le payload devrait contenir:")
    print("   - tx_id")
    print("   - client_reference")
    print("   - amount")
    print("   - currency")
    print("   - status")
    print("   - signature (HMAC-SHA256)")
    
    return True


def test_7_edge_cases():
    """Test 7 : Cas limites et validation."""
    print_test(7, "Cas Limites et Validation")
    
    tests_passed = 0
    tests_total = 3
    
    # Test 7.1 : Montant négatif
    print("   7.1 - Montant négatif...")
    payload = {
        "client_reference": "TEST-NEGATIVE",
        "amount": -1000,
        "currency": "XOF",
        "customer_email": "test@example.com",
        "callback_url": WEBHOOK_URL
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/paysim/create-order/",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 400:
            print_success("       Montant négatif correctement rejeté")
            tests_passed += 1
        else:
            print_warning(f"       Montant négatif accepté (code {response.status_code})")
    except Exception as e:
        print_error(f"       Erreur: {str(e)}")
    
    # Test 7.2 : Callback URL manquante
    print("   7.2 - Callback URL manquante...")
    payload = {
        "client_reference": "TEST-NO-CALLBACK",
        "amount": 1000,
        "currency": "XOF",
        "customer_email": "test@example.com"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/paysim/create-order/",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 400:
            print_success("       Callback URL obligatoire vérifiée")
            tests_passed += 1
        else:
            print_warning(f"       Callback URL optionnelle (code {response.status_code})")
            tests_passed += 1  # Acceptable si optionnel
    except Exception as e:
        print_error(f"       Erreur: {str(e)}")
    
    # Test 7.3 : Devise invalide
    print("   7.3 - Devise invalide...")
    payload = {
        "client_reference": "TEST-INVALID-CURRENCY",
        "amount": 1000,
        "currency": "INVALID",
        "customer_email": "test@example.com",
        "callback_url": WEBHOOK_URL
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/paysim/create-order/",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 400:
            print_success("       Devise invalide correctement rejetée")
            tests_passed += 1
        else:
            print_warning(f"       Devise invalide acceptée (code {response.status_code})")
    except Exception as e:
        print_error(f"       Erreur: {str(e)}")
    
    print()
    print(f"   Résultats: {tests_passed}/{tests_total} validations passées")
    
    return tests_passed == tests_total


# ============================================================================
# PROGRAMME PRINCIPAL
# ============================================================================

def main():
    """Programme principal de test."""
    
    print_header("🚀 TESTS PaySim API")
    print()
    print(f"Configuration:")
    print(f"  - Serveur : {BASE_URL}")
    print(f"  - WebHook : {WEBHOOK_URL}")
    print(f"  - Date    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Statistiques
    tests_run = 0
    tests_passed = 0
    
    # Test 1 : API accessible
    if test_1_api_root():
        tests_passed += 1
    tests_run += 1
    time.sleep(1)
    
    # Test 2 : Créer transaction
    tx_id = test_2_create_transaction()
    if tx_id:
        tests_passed += 1
    tests_run += 1
    time.sleep(1)
    
    # Test 3 : Statut transaction
    if test_3_transaction_status(tx_id):
        tests_passed += 1
    tests_run += 1
    time.sleep(1)
    
    # Test 4 : Liste transactions
    if test_4_list_transactions():
        tests_passed += 1
    tests_run += 1
    time.sleep(1)
    
    # Test 5 : Validation signature
    if test_5_signature_validation():
        tests_passed += 1
    tests_run += 1
    time.sleep(1)
    
    # Test 6 : Instructions WebHook
    test_6_webhook_sent()
    tests_run += 1
    time.sleep(1)
    
    # Test 7 : Cas limites
    if test_7_edge_cases():
        tests_passed += 1
    tests_run += 1
    
    # Résumé final
    print_header("📊 RÉSUMÉ DES TESTS")
    print()
    print(f"   Tests exécutés : {tests_run}")
    print(f"   Tests réussis  : {tests_passed}")
    print(f"   Taux de succès : {(tests_passed/tests_run*100):.1f}%")
    print()
    
    if tests_passed == tests_run:
        print(f"{GREEN}🎉 TOUS LES TESTS SONT PASSÉS !{RESET}")
        print()
        print("✅ Prochaines étapes:")
        print("   1. Testez l'interface de simulation dans un navigateur")
        print("   2. Vérifiez les WebHooks sur webhook.site")
        print("   3. Ajoutez des screenshots au README")
        print("   4. Pushez sur GitHub")
    else:
        print(f"{YELLOW}⚠️  Certains tests ont échoué{RESET}")
        print()
        print("🔧 Vérifiez:")
        print("   1. Les migrations sont appliquées (python manage.py migrate)")
        print("   2. Les serializers sont corrects")
        print("   3. Les URLs sont bien configurées")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print(f"{YELLOW}⚠️  Tests interrompus par l'utilisateur{RESET}")
    except Exception as e:
        print()
        print(f"{RED}❌ ERREUR FATALE : {str(e)}{RESET}")
        import traceback
        traceback.print_exc()