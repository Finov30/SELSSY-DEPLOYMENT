import requests
import hashlib
import time
import json
import urllib.parse
import base64
import sys
from typing import Dict, List, Optional
from config import SELLSY_CONFIG

# Forcer l'affichage immédiat des logs
def log_print(*args, **kwargs):
    """Fonction de log qui force l'affichage immédiat"""
    print(*args, **kwargs, flush=True)
    sys.stdout.flush()

class SellsyAPI:
    def __init__(self, consumer_token: str, consumer_secret: str):
        self.consumer_token = consumer_token
        self.consumer_secret = consumer_secret
        self.base_url = "https://apifeed.sellsy.com/0"
        # Pour une application privée, nous utilisons les tokens utilisateur
        self.oauth_token = SELLSY_CONFIG['user_token']  # Token utilisateur
        self.oauth_token_secret = SELLSY_CONFIG['user_secret']  # Secret utilisateur
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Effectue une requête vers l'API Sellsy selon la documentation V1"""
        url = f"{self.base_url}{endpoint}"
        
        # Paramètres OAuth 1.0 selon la documentation exacte
        timestamp = str(int(time.time()))
        nonce = str(int(time.time() * 1000))
        
        # Signature PLAINTEXT selon la doc
        oauth_signature = f"{urllib.parse.quote(self.consumer_secret, safe='')}&{urllib.parse.quote(self.oauth_token_secret, safe='')}"
        
        # Headers OAuth exacts selon la documentation
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'OAuth oauth_consumer_key="{self.consumer_token}", '
                           f'oauth_token="{self.oauth_token}", '
                           f'oauth_signature_method="PLAINTEXT", '
                           f'oauth_timestamp="{timestamp}", '
                           f'oauth_nonce="{nonce}", '
                           f'oauth_version="1.0", '
                           f'oauth_signature="{oauth_signature}"'
        }
        
        # Format de requête exact selon la doc Sellsy V1
        request_data = {
            "request": 1,
            "io_mode": "json",
            "do_in": json.dumps(data) if data else "{}"
        }
        
        # Pause pour éviter le Rate Limit API Sellsy
        time.sleep(1.0)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=request_data, timeout=SELLSY_CONFIG['timeout'])
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, data=request_data, timeout=SELLSY_CONFIG['timeout'])
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            response.raise_for_status()
            
            # Vérifier si la réponse est du JSON valide
            if response.text.strip():
                return response.json()
            else:
                return {"success": False, "error": "Réponse vide de l'API Sellsy"}
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête API Sellsy: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Réponse d'erreur: {e.response.text}")
            return {"success": False, "error": f"Erreur de connexion: {str(e)}"}
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")
            print(f"Réponse reçue: {response.text}")
            return {"success": False, "error": f"Réponse invalide de l'API: {response.text[:200]}"}
    
    def create_client(self, client_data: Dict) -> Dict:
        """Crée un client tiers dans Sellsy"""
        third_type = 'corporation' if client_data.get('company_name') else 'person'

        third_params = {
            "name": client_data.get('company_name') or client_data.get('name', ''),
            "email": client_data.get('email', ''),
            "mobile": client_data.get('phone', ''),
            "tel": client_data.get('phone', ''),
            "type": third_type
        }

        if client_data.get('siren'):
            third_params["siren"] = client_data.get('siren')
        if client_data.get('siret'):
            third_params["siret"] = client_data.get('siret')

        if client_data.get('address'):
            third_params["address"] = {
                "name": "Adresse principale",
                "part1": client_data.get('address', ''),
                "zip": client_data.get('postal_code', ''),
                "town": client_data.get('city', ''),
                "countrycode": "FR" if client_data.get('country') == 'France' else (client_data.get('country', 'FR')[:2].upper() if client_data.get('country') else 'FR')
            }
            if client_data.get('first_name') or client_data.get('last_name'):
                part2 = f"{client_data.get('first_name', '')} {client_data.get('last_name', '')}".strip()
                if client_data.get('company_name'):
                    part2 += f" - {client_data.get('company_name')}"
                if part2:
                    third_params["address"]["part2"] = part2

        if client_data.get('notes'):
            third_params["stickyNote"] = client_data.get('notes')

        if third_type == 'person':
            third_params["people_forename"] = client_data.get('first_name', '')
            third_params["people_name"] = client_data.get('last_name', '')

        sellsy_request = {
            "method": "Client.create",
            "params": {
                "third": third_params
            }
        }
        
        return self._make_request('POST', '', sellsy_request)

    def create_contact(self, contact_data: Dict, third_id: str) -> Dict:
        """Crée un contact (personne physique)"""
        people_data = {
            "forename": contact_data.get('first_name', ''),
            "name": contact_data.get('last_name', ''),
            "email": contact_data.get('email', ''),
            "tel": contact_data.get('phone', ''),
            "mobile": contact_data.get('phone', ''),
            "thirdids": [third_id]
        }

        if contact_data.get('position'):
            people_data["position"] = contact_data.get('position')

        sellsy_request = {
            "method": "Peoples.create",
            "params": {
                "people": people_data
            }
        }

        return self._make_request('POST', '', sellsy_request)
    
    def add_address_to_client(self, address_data: Dict, third_id: str, address_type: str = "billing") -> Dict:
        """Ajoute une adresse à un client existant"""
        address_name = "Adresse de facturation" if address_type == "billing" else "Adresse de livraison"
        part1 = address_data.get('address', '')
        
        part2 = ""
        if address_type == "delivery":
            if address_data.get('first_name') or address_data.get('last_name'):
                part2 = f"{address_data.get('first_name', '')} {address_data.get('last_name', '')}".strip()
            if address_data.get('company_name'):
                if part2:
                    part2 += f" - {address_data.get('company_name')}"
                else:
                    part2 = address_data.get('company_name')
        
        address_params = {
            "thirdid": third_id,
            "name": address_name,
            "part1": part1,
            "zip": address_data.get('postal_code', ''),
            "town": address_data.get('city', ''),
            "countrycode": "FR" if address_data.get('country') == 'France' else (address_data.get('country', 'FR')[:2].upper() if address_data.get('country') else 'FR')
        }
        
        if part2:
            address_params["part2"] = part2
        
        sellsy_request = {
            "method": "Client.addAddress",
            "params": {
                "clientid": int(third_id),
                "address": address_params
            }
        }
        
        return self._make_request('POST', '', sellsy_request)

    def get_current_opportunity_ident(self) -> Optional[str]:
        sellsy_request = {
            "method": "Opportunities.getCurrentIdent",
            "params": {}
        }
        try:
            response = self._make_request('GET', '', sellsy_request)
            if response.get('response'):
                return response['response']
            return None
        except Exception as e:
            print(f"Erreur ident opportunité: {e}")
            return None
    
    def get_opportunities_list(self) -> Optional[Dict]:
        sellsy_request = {
            "method": "Opportunities.getList",
            "params": {"search": {"limit": 1}}
        }
        try:
            return self._make_request('GET', '', sellsy_request)
        except Exception as e:
            print(f"Erreur liste opportunités: {e}")
            return None
    
    def find_product_by_code(self, product_code: str, catalog: Optional[Dict] = None) -> Optional[Dict]:
        """
        Trouve un produit dans le catalogue Sellsy par son code (référence) via l'API (Recherche optimisée)
        """
        # Convertir DC en 123 pour la recherche dans Sellsy
        search_code = product_code
        if product_code.endswith('DC'):
            search_code = product_code[:-2] + '123'
        
        # Recherche via l'API Catalogue.getList
        sellsy_request = {
            "method": "Catalogue.getList",
            "params": {
                "type": "item",
                "search": {
                    "name": search_code  # Recherche dans le nom/référence
                },
                "pagination": {
                    "nbperpage": 5,
                    "pagenum": 1
                }
            }
        }
        
        try:
            response = self._make_request('POST', '', sellsy_request)
            if response.get('status') == 'success' and response.get('response'):
                result = response['response'].get('result', {})
                
                # Parcourir les résultats pour trouver celui qui commence par le code exact
                if isinstance(result, dict):
                    for prod_id, prod_data in result.items():
                        product_name = prod_data.get('name', '')
                        if product_name.startswith(search_code):
                            return {
                                'id': prod_data.get('id'),
                                'name': product_name,
                                'unitAmount': prod_data.get('unitAmount'),
                                'taxid': prod_data.get('taxid')
                            }
                elif isinstance(result, list):
                    for prod_data in result:
                        product_name = prod_data.get('name', '')
                        if product_name.startswith(search_code):
                            return {
                                'id': prod_data.get('id'),
                                'name': product_name,
                                'unitAmount': prod_data.get('unitAmount'),
                                'taxid': prod_data.get('taxid')
                            }
            return None
        except Exception as e:
            print(f"Erreur recherche produit {product_code}: {e}")
            return None

    def create_estimate(self, estimate_data: Dict) -> Dict:
        """
        Crée un devis (estimate) dans Sellsy avec les produits du catalogue
        """
        rows = []
        for idx, product in enumerate(estimate_data.get('products', [])):
            product_code = product.get('code_produit', '')

            if not product_code and product.get('sellsy_reference'):
                sellsy_ref = product.get('sellsy_reference', '')
                if ' - ' in sellsy_ref:
                    product_code = sellsy_ref.split(' - ')[0].strip()
                else:
                    product_code = sellsy_ref.strip()

            # Recherche optimisée produit par produit
            sellsy_product = None
            if product_code:
                sellsy_product = self.find_product_by_code(product_code)

            if sellsy_product:
                row = {
                    "row_type": "item",
                    "row_linkedid": sellsy_product['id'],
                    "row_qt": product.get('quantity', 1),
                    "row_unitAmount": sellsy_product['unitAmount'],
                    "row_tax": "20.00"
                }
                
                reference_atelier = product.get('reference_atelier', '')
                if reference_atelier:
                    row["row_name"] = reference_atelier
                
                description_maison = product.get('description_maison_raphael', '')
                if description_maison:
                    row["row_notes"] = description_maison
                else:
                    product_details = []
                    if product.get('code_produit'):
                        product_details.append(f"Code: {product.get('code_produit')}")
                        if 'DC' in str(product.get('code_produit')):
                            product_details.append("Variante: DOS AVEC CHEVALET")
                    if product.get('frame_size'):
                        product_details.append(f"Taille: {product.get('frame_size')}")
                    if product.get('nom_commercial'):
                        product_details.append(f"Nom: {product.get('nom_commercial')}")

                    if product_details:
                        row["row_notes"] = " | ".join(product_details)
            else:
                # Produit non trouvé - texte libre
                reference_atelier = product.get('reference_atelier', '')
                row_name = reference_atelier if reference_atelier else product.get('nom_commercial', product.get('product', 'Produit'))
                
                row = {
                    "row_type": "item",
                    "row_name": row_name,
                    "row_qt": product.get('quantity', 1),
                    "row_unitAmount": "0.01",
                    "row_unit": "unité",
                    "row_tax": "20.00"
                }

                description_maison = product.get('description_maison_raphael', '')
                if description_maison:
                    row["row_notes"] = description_maison
                else:
                    product_details = []
                    if product.get('code_produit'):
                        product_details.append(f"Réf: {product.get('code_produit')}")
                    if product.get('frame_size'):
                        product_details.append(f"Taille: {product.get('frame_size')}")

                    if product_details:
                        row["row_notes"] = " | ".join(product_details)

            rows.append(row)

        product_notes = estimate_data.get('product_notes', '')
        if product_notes:
            rows.append({
                "row_type": "comment",
                "row_comment": f"Notes du client:\n{product_notes}"
            })

        rows_dict = {str(i+1): row for i, row in enumerate(rows)}

        document_params = {
            "document": {
                "doctype": "estimate",
                "thirdid": estimate_data.get('client_id'),
                "subject": estimate_data.get('name', 'Demande de devis'),
                "displayedDate": int(time.time()),
                "notes": estimate_data.get('notes', '')
            },
            "row": rows_dict
        }

        if estimate_data.get('contact_id'):
            document_params["document"]["contactid"] = estimate_data.get('contact_id')
        
        if estimate_data.get('billing_address_id'):
            document_params["document"]["thirdaddressid"] = estimate_data.get('billing_address_id')
        
        if estimate_data.get('delivery_address_id'):
            document_params["document"]["shipaddressid"] = estimate_data.get('delivery_address_id')

        sellsy_request = {
            "method": "Document.create",
            "params": document_params
        }

        return self._make_request('POST', '', sellsy_request)
    
    def search_client_by_email(self, email: str) -> Optional[Dict]:
        """Recherche un client par email"""
        sellsy_request = {
            "method": "Client.getList",
            "params": {
                "search": {"contains": email},
                "pagination": {"nbperpage": 10, "pagenum": 1}
            }
        }

        try:
            response = self._make_request('POST', '', sellsy_request)
            if response.get('status') == 'success' and response.get('response'):
                result = response['response'].get('result', {})
                if isinstance(result, list) and len(result) == 0:
                    return None
                if isinstance(result, dict):
                    for client_id, client_data in result.items():
                        if client_data.get('email', '').lower() == email.lower():
                            return {'id': client_id, **client_data}
            return None
        except Exception as e:
            print(f"Erreur recherche client: {e}")
            return None
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict]:
        """Récupère les infos client"""
        sellsy_request = {
            "method": "Client.getOne",
            "params": {"clientid": client_id}
        }
        
        try:
            response = self._make_request('POST', '', sellsy_request)
            if response.get('status') == 'success' and response.get('response'):
                client_data = response.get('response', {})
                return {'id': client_id, **client_data}
            return None
        except Exception as e:
            print(f"Erreur récupération client {client_id}: {e}")
            return None
    
    def get_client_addresses(self, client_id: str) -> Optional[Dict]:
        """Récupère les adresses d'un client"""
        sellsy_request = {
            "method": "Address.getList",
            "params": {"search": {"thirdid": client_id}}
        }
        try:
            response = self._make_request('POST', '', sellsy_request)
            if response.get('status') == 'success' and response.get('response'):
                return response.get('response', {})
            return None
        except Exception:
            return None
    
    def update_client(self, client_id: str, client_data: Dict) -> Dict:
        """Met à jour un client"""
        third_params = {}
        for field in ['maindelivaddressid', 'name', 'email', 'mobile', 'tel']:
            if client_data.get(field):
                third_params[field] = client_data.get(field)
        
        sellsy_request = {
            "method": "Client.update",
            "params": {
                "clientid": client_id,
                "third": third_params
            }
        }
        return self._make_request('POST', '', sellsy_request)
    
    def get_full_catalog(self) -> Dict[str, Dict]:
        return {}

# Instance globale
sellsy_api = SellsyAPI(SELLSY_CONFIG['consumer_token'], SELLSY_CONFIG['consumer_secret'])

def create_client_and_opportunity(order_data: Dict) -> Dict:
    """Fonction principale de création de commande"""
    try:
        print("\n=== TRAITEMENT COMMANDE ===", flush=True)
        
        delivery_address = order_data.get('delivery_address', {})
        selected_products = order_data.get('selected_products', [])
        
        client_data = {
            'first_name': delivery_address.get('firstName', ''),
            'last_name': delivery_address.get('lastName', ''),
            'name': f"{delivery_address.get('firstName', '')} {delivery_address.get('lastName', '')}".strip(),
            'company_name': delivery_address.get('companyName', ''),
            'siren': delivery_address.get('siren', ''),
            'siret': delivery_address.get('siret', ''),
            'email': delivery_address.get('email', ''),
            'phone': delivery_address.get('phone', ''),
            'address': delivery_address.get('address', ''),
            'city': delivery_address.get('city', ''),
            'postal_code': delivery_address.get('postalCode', ''),
            'country': delivery_address.get('country', 'France'),
            'notes': delivery_address.get('notes', '')
        }
        
        same_billing_address = delivery_address.get('sameBillingAddress', 'on') == 'on'
        billing_address = None
        if not same_billing_address:
            billing_address = {
                'first_name': delivery_address.get('billingFirstName', ''),
                'last_name': delivery_address.get('billingLastName', ''),
                'company_name': delivery_address.get('billingCompanyName', ''),
                'siren': delivery_address.get('billingSiren', ''),
                'siret': delivery_address.get('billingSiret', ''),
                'address': delivery_address.get('billingAddress', ''),
                'city': delivery_address.get('billingCity', ''),
                'postal_code': delivery_address.get('billingPostalCode', ''),
                'country': delivery_address.get('billingCountry', 'France')
            }
        
        # 1. Gestion Client
        print(f"Client: {client_data['email']}")
        existing_client = sellsy_api.search_client_by_email(client_data['email'])
        client_id = None
        default_address_id = None
        
        if existing_client:
            client_id = existing_client.get('id') or existing_client.get('thirdid')
            print(f"✓ Client existant: {client_id}")
            
            # Récupérer adresse principale existante (logique simplifiée)
            addr = existing_client.get('address')
            if existing_client.get('addressid'):
                default_address_id = existing_client.get('addressid')
            elif isinstance(addr, dict):
                default_address_id = addr.get('id')
            elif isinstance(addr, list) and addr:
                default_address_id = addr[0].get('id')
        else:
            print("→ Nouveau client...")
            resp = sellsy_api.create_client(client_data)
            if resp.get('status') == 'success':
                client_id = resp.get('response', {}).get('client_id')
                default_address_id = resp.get('response', {}).get('addressid')
                print(f"✓ Client créé: {client_id}")
                
                # Contact associé
                if client_data.get('company_name'):
                    sellsy_api.create_contact(client_data, str(client_id))
            else:
                raise Exception(f"Erreur création client: {resp.get('error')}")

        if not client_id:
            raise Exception("ID client introuvable")

        # 2. Adresse Livraison
        delivery_address_id = None
        if delivery_address.get('address'):
            print("→ Adresse livraison...")
            da_data = {
                'address': delivery_address.get('address', ''),
                'city': delivery_address.get('city', ''),
                'postal_code': delivery_address.get('postalCode', ''),
                'country': delivery_address.get('country', 'France'),
                'first_name': delivery_address.get('firstName', ''),
                'last_name': delivery_address.get('lastName', ''),
                'company_name': delivery_address.get('companyName', '')
            }
            resp = sellsy_api.add_address_to_client(da_data, str(client_id), "delivery")
            if resp.get('status') == 'success':
                r = resp.get('response', {})
                if isinstance(r, dict):
                    delivery_address_id = r.get('address_id') or r.get('id')
                else:
                    delivery_address_id = str(r)
                print(f"✓ Livraison créée: {delivery_address_id}")
                
                # Update main delivery address
                if delivery_address_id:
                    sellsy_api.update_client(str(client_id), {'maindelivaddressid': str(delivery_address_id)})
            else:
                print(f"✗ Erreur adresse livraison: {resp.get('error')}")
                delivery_address_id = default_address_id

        # 3. Adresse Facturation
        billing_address_id = None
        if same_billing_address:
            billing_address_id = delivery_address_id or default_address_id
        elif billing_address:
            print("→ Adresse facturation...")
            resp = sellsy_api.add_address_to_client(billing_address, str(client_id), "billing")
            if resp.get('status') == 'success':
                r = resp.get('response', {})
                billing_address_id = r.get('address_id') if isinstance(r, dict) else str(r)
                print(f"✓ Facturation créée: {billing_address_id}")
            else:
                billing_address_id = default_address_id

        # 4. Création Devis
        print("→ Création devis...")
        prod_names = [p.get('nom_commercial', '') for p in selected_products]
        subject = f"Devis - {', '.join(prod_names[:3])}"
        
        estimate_data = {
            'client_id': client_id,
            'billing_address_id': billing_address_id,
            'delivery_address_id': delivery_address_id,
            'name': subject,
            'products': selected_products,
            'product_notes': order_data.get('product_notes', ''),
            'notes': delivery_address.get('notes', '')
        }
        
        resp = sellsy_api.create_estimate(estimate_data)
        estimate_id = None
        if resp.get('status') == 'success':
            estimate_id = resp.get('response', {}).get('doc_id')
            print(f"✓ DEVIS CRÉÉ AVEC SUCCÈS: {estimate_id}")
        else:
            print(f"✗ Erreur devis: {resp.get('error')}")

        return {
            'success': True,
            'client_id': client_id,
            'estimate_id': estimate_id,
            'message': 'Devis créé' if estimate_id else 'Erreur devis'
        }

    except Exception as e:
        print(f"EXCEPTION: {e}")
        return {'success': False, 'error': str(e)}