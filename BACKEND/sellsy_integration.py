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
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=request_data, timeout=SELLSY_CONFIG['timeout'])
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, data=request_data, timeout=SELLSY_CONFIG['timeout'])
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            # Debug logs (décommenter si nécessaire)
            # print(f"URL: {url}")
            # print(f"Headers: {headers}")
            # print(f"Request Data: {request_data}")
            # print(f"Response Status: {response.status_code}")
            # print(f"Response Text: {response.text[:500]}")
            
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
        """
        Crée un nouveau client dans Sellsy

        Args:
            client_data: Dictionnaire contenant les informations du client
        """
        # Format selon la doc Sellsy - utiliser Client.create avec "third"
        # Déterminer le type: 'person' si pas d'entreprise, 'corporation' sinon
        third_type = 'corporation' if client_data.get('company_name') else 'person'

        third_params = {
            "name": client_data.get('company_name') or client_data.get('name', ''),
            "email": client_data.get('email', ''),
            "mobile": client_data.get('phone', ''),  # Utiliser mobile au lieu de phone
            "tel": client_data.get('phone', ''),     # Ajouter aussi tel
            "type": third_type
        }

        # Ajouter SIREN/SIRET si disponibles
        if client_data.get('siren'):
            third_params["siren"] = client_data.get('siren')
        if client_data.get('siret'):
            third_params["siret"] = client_data.get('siret')

        # Ajouter l'adresse si disponible
        # Dans l'API Sellsy, l'adresse doit être créée lors de la création du client
        # La structure attendue est un objet address avec les champs requis
        if client_data.get('address'):
            third_params["address"] = {
                "name": "Adresse principale",
                "part1": client_data.get('address', ''),
                "zip": client_data.get('postal_code', ''),
                "town": client_data.get('city', ''),
                "countrycode": "FR" if client_data.get('country') == 'France' else (client_data.get('country', 'FR')[:2].upper() if client_data.get('country') else 'FR')
            }
            # Pour une adresse de livraison, ajouter part2 si disponible
            if client_data.get('first_name') or client_data.get('last_name'):
                part2 = f"{client_data.get('first_name', '')} {client_data.get('last_name', '')}".strip()
                if client_data.get('company_name'):
                    part2 += f" - {client_data.get('company_name')}"
                if part2:
                    third_params["address"]["part2"] = part2

        # Ajouter les notes si disponibles
        if client_data.get('notes'):
            third_params["stickyNote"] = client_data.get('notes')

        # Si c'est une personne, ajouter prénom/nom
        if third_type == 'person':
            third_params["people_forename"] = client_data.get('first_name', '')
            third_params["people_name"] = client_data.get('last_name', '')

        sellsy_request = {
            "method": "Client.create",
            "params": {
                "third": third_params
            }
        }
        
        print(f"[DEBUG Client.create] Paramètres envoyés: {json.dumps(sellsy_request, indent=2, ensure_ascii=False)}")
        
        response = self._make_request('POST', '', sellsy_request)
        
        print(f"[DEBUG Client.create] Réponse reçue: {json.dumps(response, indent=2, ensure_ascii=False, default=str)}")
        
        return response

    def create_contact(self, contact_data: Dict, third_id: str) -> Dict:
        """
        Crée un contact (personne physique) et le lie à un client (société)

        Args:
            contact_data: Dictionnaire contenant les informations du contact
            third_id: ID du client (société) auquel lier le contact

        Returns:
            Réponse de l'API Sellsy
        """
        people_data = {
            "forename": contact_data.get('first_name', ''),
            "name": contact_data.get('last_name', ''),
            "email": contact_data.get('email', ''),
            "tel": contact_data.get('phone', ''),
            "mobile": contact_data.get('phone', ''),
            "thirdids": [third_id]  # Lier le contact à la société
        }

        # Ajouter la position si disponible
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
        """
        Ajoute une adresse à un client existant dans Sellsy
        
        Args:
            address_data: Dictionnaire contenant les informations de l'adresse
            third_id: ID du client auquel ajouter l'adresse
            address_type: Type d'adresse ("billing" pour facturation, "delivery" pour livraison)
            
        Returns:
            Réponse de l'API Sellsy
        """
        print(f"\n  [add_address_to_client] Début de la création d'adresse")
        print(f"  Type: {address_type}")
        print(f"  Client ID: {third_id}")
        print(f"  Données reçues: {json.dumps(address_data, indent=4, ensure_ascii=False)}")
        
        address_name = "Adresse de facturation" if address_type == "billing" else "Adresse de livraison"
        
        # Construire part1 avec toutes les informations de l'adresse
        # Format: "Numéro et nom de rue"
        part1 = address_data.get('address', '')
        
        # Construire part2 avec le nom/prénom si disponible (pour l'adresse de livraison)
        part2 = ""
        if address_type == "delivery":
            # Pour l'adresse de livraison, ajouter le nom du destinataire
            if address_data.get('first_name') or address_data.get('last_name'):
                part2 = f"{address_data.get('first_name', '')} {address_data.get('last_name', '')}".strip()
            if address_data.get('company_name'):
                if part2:
                    part2 += f" - {address_data.get('company_name')}"
                else:
                    part2 = address_data.get('company_name')
        
        # Construire les paramètres d'adresse selon la documentation Sellsy
        address_params = {
            "thirdid": third_id,
            "name": address_name,
            "part1": part1,
            "zip": address_data.get('postal_code', ''),
            "town": address_data.get('city', ''),
            "countrycode": "FR" if address_data.get('country') == 'France' else (address_data.get('country', 'FR')[:2].upper() if address_data.get('country') else 'FR')
        }
        
        # Ajouter part2 si disponible (nom du destinataire pour adresse de livraison)
        if part2:
            address_params["part2"] = part2
        
        # Pour une adresse de livraison, on peut aussi spécifier le type
        # Selon la documentation, on peut utiliser "type" pour différencier les adresses
        if address_type == "delivery":
            # Marquer comme adresse de livraison si supporté par l'API
            # Note: Vérifier dans la doc si ce champ existe
            pass
        
        print(f"  Paramètres d'adresse construits: {json.dumps(address_params, indent=4, ensure_ascii=False)}")
        
        # Selon la documentation Sellsy, utiliser Client.addAddress pour ajouter une adresse
        # Méthode: Client.addAddress
        # Paramètres: clientid (int) et address (array - même structure que dans Client.create)
        sellsy_request = {
            "method": "Client.addAddress",
            "params": {
                "clientid": int(third_id),
                "address": address_params
            }
        }
        
        print(f"  Requête Sellsy complète: {json.dumps(sellsy_request, indent=4, ensure_ascii=False)}")
        
        response = self._make_request('POST', '', sellsy_request)
        
        print(f"  Réponse brute de l'API: {json.dumps(response, indent=4, ensure_ascii=False, default=str)}")
        
        # Selon la documentation, la réponse est: {"response":{"address_id":{{address_id}}},"error":"","status":"success"}
        if response.get('status') == 'success':
            response_data = response.get('response', {})
            address_id = response_data.get('address_id') or response_data.get('addressid') or response_data.get('id')
            
            if address_id:
                print(f"  ✓ Adresse créée avec succès, ID: {address_id}")
                return {
                    "status": "success",
                    "response": {
                        "address_id": str(address_id),
                        "id": str(address_id),
                        "addressid": str(address_id)
                    }
                }
            else:
                print(f"  ⚠ Réponse de succès mais aucun ID d'adresse trouvé")
                print(f"  Structure de la réponse: {json.dumps(response_data, indent=2, ensure_ascii=False, default=str)}")
        
        return response

    def get_current_opportunity_ident(self) -> Optional[str]:
        """
        Obtient l'identifiant actuel pour une nouvelle opportunité
        
        Returns:
            Identifiant de l'opportunité ou None si erreur
        """
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
            print(f"Erreur lors de l'obtention de l'identifiant d'opportunité: {e}")
            return None
    
    def get_opportunities_list(self) -> Optional[Dict]:
        """
        Obtient la liste des opportunités pour comprendre la structure
        
        Returns:
            Liste des opportunités ou None si erreur
        """
        sellsy_request = {
            "method": "Opportunities.getList",
            "params": {
                "search": {
                    "limit": 1
                }
            }
        }
        
        try:
            response = self._make_request('GET', '', sellsy_request)
            print(f"Réponse getList opportunités: {response}")
            return response
        except Exception as e:
            print(f"Erreur lors de l'obtention de la liste d'opportunités: {e}")
            return None
    
    def create_estimate(self, estimate_data: Dict) -> Dict:
        """
        Crée un devis (estimate) dans Sellsy avec les produits du catalogue

        Args:
            estimate_data: Dictionnaire contenant les informations du devis
                - client_id: ID du client
                - contact_id: ID du contact (optionnel)
                - products: Liste des produits avec quantité et code_produit
                - notes: Notes du devis (optionnel)

        Returns:
            Réponse de l'API Sellsy
        """
        import time

        # Récupérer le catalogue une seule fois pour tous les produits
        print("\nRécupération du catalogue pour le matching des produits...")
        catalog = self.get_full_catalog()

        # Préparer les lignes de produits (rows)
        rows = []
        for idx, product in enumerate(estimate_data.get('products', [])):
            # Extraire le code produit (référence Sellsy)
            # Le code peut être dans 'code_produit' ou extrait de la référence Excel
            product_code = product.get('code_produit', '')

            # Si pas de code_produit, essayer d'extraire de la colonne SELLSY
            if not product_code and product.get('sellsy_reference'):
                # Format: "050612 - GAELLE 80" -> extraire "050612"
                sellsy_ref = product.get('sellsy_reference', '')
                if ' - ' in sellsy_ref:
                    product_code = sellsy_ref.split(' - ')[0].strip()
                else:
                    product_code = sellsy_ref.strip()

            # Chercher le produit dans le catalogue Sellsy
            sellsy_product = None
            if product_code:
                print(f"  Recherche du produit: {product_code}")
                sellsy_product = self.find_product_by_code(product_code, catalog)

                if sellsy_product:
                    print(f"    >> Trouvé: {sellsy_product['name']} (ID: {sellsy_product['id']}, Prix: {sellsy_product['unitAmount']} EUR)")
                else:
                    print(f"    >> Produit non trouvé dans le catalogue")

            # Créer la ligne de devis
            if sellsy_product:
                # Produit trouvé dans le catalogue - utiliser linkedid avec prix du catalogue
                row = {
                    "row_type": "item",
                    "row_linkedid": sellsy_product['id'],  # ID du produit catalogue
                    "row_qt": product.get('quantity', 1),
                    "row_unitAmount": sellsy_product['unitAmount'],  # Prix du catalogue
                    "row_tax": "20.00"  # TVA française standard (format string)
                }

                # Utiliser la Référence Atelier (colonne J) comme nom si disponible
                reference_atelier = product.get('reference_atelier', '')
                if reference_atelier:
                    row["row_name"] = reference_atelier
                
                # Utiliser la DESCRIPTION MAISON RAPHAEL (colonne AE) comme description
                description_maison = product.get('description_maison_raphael', '')
                if description_maison:
                    row["row_notes"] = description_maison
                else:
                    # Fallback sur les détails du produit si pas de description
                    product_details = []
                    if product.get('code_produit'):
                        product_details.append(f"Code: {product.get('code_produit')}")
                        # Si le code contient "DC", ajouter une note spéciale
                        if 'DC' in str(product.get('code_produit')):
                            product_details.append("Variante: DOS AVEC CHEVALET")
                    if product.get('frame_size'):
                        product_details.append(f"Taille: {product.get('frame_size')}")
                    if product.get('nom_commercial'):
                        product_details.append(f"Nom: {product.get('nom_commercial')}")

                    if product_details:
                        row["row_notes"] = " | ".join(product_details)
            else:
                # Produit non trouvé - créer en texte libre (sans linkedid)
                # Utiliser la Référence Atelier (colonne J) comme nom si disponible
                reference_atelier = product.get('reference_atelier', '')
                row_name = reference_atelier if reference_atelier else product.get('nom_commercial', product.get('product', 'Produit'))
                
                row = {
                    "row_type": "item",
                    "row_name": row_name,
                    "row_qt": product.get('quantity', 1),
                    "row_unitAmount": "0.01",  # Prix minimal
                    "row_unit": "unité",
                    "row_tax": "20.00"  # TVA française standard 20%
                    # Pas de row_linkedid car produit non trouvé dans le catalogue
                }

                # Utiliser la DESCRIPTION MAISON RAPHAEL (colonne AE) comme description
                description_maison = product.get('description_maison_raphael', '')
                if description_maison:
                    row["row_notes"] = description_maison
                else:
                    # Fallback sur les détails du produit si pas de description
                    product_details = []
                    if product.get('code_produit'):
                        product_details.append(f"Réf: {product.get('code_produit')}")
                    if product.get('frame_size'):
                        product_details.append(f"Taille: {product.get('frame_size')}")

                    if product_details:
                        row["row_notes"] = " | ".join(product_details)

            rows.append(row)

        # Ajouter les notes des produits si disponibles
        product_notes = estimate_data.get('product_notes', '')
        if product_notes:
            rows.append({
                "row_type": "comment",
                "row_comment": f"Notes du client:\n{product_notes}"
            })

        # Convertir rows en dictionnaire avec indices numériques
        # Sellsy attend {1: {...}, 2: {...}} au lieu de [{...}, {...}]
        rows_dict = {str(i+1): row for i, row in enumerate(rows)}

        # Créer le document de type "estimate" (devis)
        document_params = {
            "document": {
                "doctype": "estimate",
                "thirdid": estimate_data.get('client_id'),
                "subject": estimate_data.get('name', 'Demande de devis'),
                "displayedDate": int(time.time()),  # Date actuelle
                "notes": estimate_data.get('notes', '')
                # Pas besoin de currency, Sellsy utilisera la devise par défaut
            },
            "row": rows_dict
        }

        # Ajouter le contact si disponible
        if estimate_data.get('contact_id'):
            document_params["document"]["contactid"] = estimate_data.get('contact_id')
        
        # Ajouter l'adresse de facturation si disponible
        if estimate_data.get('billing_address_id'):
            document_params["document"]["thirdaddressid"] = estimate_data.get('billing_address_id')
            print(f"Utilisation de l'adresse de facturation ID: {estimate_data.get('billing_address_id')}")
        
        # Ajouter l'adresse de livraison si disponible
        if estimate_data.get('delivery_address_id'):
            document_params["document"]["shipaddressid"] = estimate_data.get('delivery_address_id')
            print(f"Utilisation de l'adresse de livraison ID: {estimate_data.get('delivery_address_id')}")

        sellsy_request = {
            "method": "Document.create",
            "params": document_params
        }

        return self._make_request('POST', '', sellsy_request)
    
    def search_client_by_email(self, email: str) -> Optional[Dict]:
        """
        Recherche un client par email

        Args:
            email: Email du client à rechercher

        Returns:
            Dictionnaire avec les informations du client ou None si non trouvé
        """
        # Format selon la doc Sellsy V1 - utiliser Client.getList avec POST
        sellsy_request = {
            "method": "Client.getList",
            "params": {
                "search": {
                    "contains": email
                },
                "pagination": {
                    "nbperpage": 10,
                    "pagenum": 1
                }
            }
        }

        try:
            response = self._make_request('POST', '', sellsy_request)
            if response.get('status') == 'success' and response.get('response'):
                result = response['response'].get('result', {})
                # Si result est une liste vide, aucun client trouvé
                if isinstance(result, list) and len(result) == 0:
                    return None
                # Si result est un dict, chercher le client
                if isinstance(result, dict):
                    # Retourne le premier client trouvé qui correspond exactement à l'email
                    for client_id, client_data in result.items():
                        if client_data.get('email', '').lower() == email.lower():
                            # Récupérer les informations complètes du client avec Client.getOne
                            full_client = self.get_client_by_id(client_id)
                            if full_client:
                                return full_client
                            return {'id': client_id, **client_data}
                return None
            return None
        except Exception as e:
            print(f"Erreur lors de la recherche du client: {e}")
            return None
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict]:
        """
        Récupère les informations complètes d'un client par son ID
        
        Args:
            client_id: ID du client
            
        Returns:
            Dictionnaire avec les informations complètes du client ou None
        """
        sellsy_request = {
            "method": "Client.getOne",
            "params": {
                "clientid": client_id
            }
        }
        
        try:
            print(f"\n[API CALL] Client.getOne - Requête: {json.dumps(sellsy_request, indent=2, ensure_ascii=False)}")
            response = self._make_request('POST', '', sellsy_request)
            print(f"[API CALL] Client.getOne - Réponse complète: {json.dumps(response, indent=2, ensure_ascii=False, default=str)}")
            
            if response.get('status') == 'success' and response.get('response'):
                client_data = response.get('response', {})
                print(f"[API CALL] Client.getOne - Données client extraites: {json.dumps(client_data, indent=2, ensure_ascii=False, default=str)}")
                return {'id': client_id, **client_data}
            else:
                print(f"[API CALL] Client.getOne - Erreur dans la réponse: {response.get('error')}")
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération du client {client_id}: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None
    
    def get_client_addresses(self, client_id: str) -> Optional[Dict]:
        """
        Récupère toutes les adresses d'un client via Address.getList
        
        Args:
            client_id: ID du client
            
        Returns:
            Dictionnaire avec toutes les adresses du client ou None
        """
        sellsy_request = {
            "method": "Address.getList",
            "params": {
                "search": {
                    "thirdid": client_id
                }
            }
        }
        
        try:
            response = self._make_request('POST', '', sellsy_request)
            if response.get('status') == 'success' and response.get('response'):
                addresses_data = response.get('response', {})
                return addresses_data
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération des adresses du client {client_id}: {e}")
            return None
    
    def update_client(self, client_id: str, client_data: Dict) -> Dict:
        """
        Met à jour les informations d'un client existant dans Sellsy
        
        Args:
            client_id: ID du client à mettre à jour
            client_data: Dictionnaire contenant les informations à mettre à jour
            
        Returns:
            Réponse de l'API Sellsy
        """
        third_params = {}
        
        # Ajouter les champs à mettre à jour
        if client_data.get('maindelivaddressid'):
            third_params["maindelivaddressid"] = client_data.get('maindelivaddressid')
        
        if client_data.get('name'):
            third_params["name"] = client_data.get('name')
        
        if client_data.get('email'):
            third_params["email"] = client_data.get('email')
        
        if client_data.get('mobile'):
            third_params["mobile"] = client_data.get('mobile')
        
        if client_data.get('tel'):
            third_params["tel"] = client_data.get('tel')
        
        sellsy_request = {
            "method": "Client.update",
            "params": {
                "clientid": client_id,
                "third": third_params
            }
        }
        
        return self._make_request('POST', '', sellsy_request)
    
    def get_full_catalog(self) -> Dict[str, Dict]:
        """
        Récupère TOUT le catalogue Sellsy (nécessaire pour le matching des produits)

        Returns:
            Dictionnaire de tous les produits {product_id: product_data}
        """
        all_products = {}
        page = 1
        total_pages = None

        print("Récupération du catalogue Sellsy...")

        while True:
            catalog_request = {
                "method": "Catalogue.getList",
                "params": {
                    "type": "item",
                    "pagination": {
                        "nbperpage": 100,
                        "pagenum": page
                    }
                }
            }

            response = self._make_request('POST', '', catalog_request)

            if response.get('status') == 'success':
                infos = response.get('response', {}).get('infos', {})
                result = response.get('response', {}).get('result', {})

                if total_pages is None:
                    total_pages = int(infos.get('nbpages', 0))
                    total_items = infos.get('nbtotal', 0)
                    print(f"  Catalogue: {total_items} produits sur {total_pages} pages")

                all_products.update(result)

                if page >= total_pages:
                    break

                page += 1
            else:
                print(f"Erreur lors de la récupération du catalogue: {response.get('error')}")
                break

        print(f"  Catalogue récupéré: {len(all_products)} produits")
        return all_products

    def find_product_by_code(self, product_code: str, catalog: Optional[Dict] = None) -> Optional[Dict]:
        """
        Trouve un produit dans le catalogue Sellsy par son code (référence)

        Args:
            product_code: Code du produit (ex: "050612" ou "050612DC")
            catalog: Catalogue déjà récupéré (optionnel, sera récupéré si None)

        Returns:
            Dictionnaire du produit trouvé ou None
        """
        # Récupérer le catalogue si pas fourni
        if catalog is None:
            catalog = self.get_full_catalog()

        # Convertir DC en 123 pour la recherche dans Sellsy
        # DC = Dos avec Chevalet = variante 123 dans Sellsy
        search_code = product_code
        if product_code.endswith('DC'):
            search_code = product_code[:-2] + '123'  # Remplacer DC par 123
            print(f"    >> Code avec DC converti: {product_code} -> {search_code}")

        # Chercher le produit par code dans le nom
        for product_id, product in catalog.items():
            product_name = product.get('name', '')

            # Le code est au début du nom (ex: "050612123 - GAELLE 80")
            if product_name.startswith(search_code):
                return {
                    'id': product.get('id'),
                    'name': product_name,
                    'unitAmount': product.get('unitAmount'),
                    'taxid': product.get('taxid')
                }

        return None

# Instance globale de l'API Sellsy
sellsy_api = SellsyAPI(SELLSY_CONFIG['consumer_token'], SELLSY_CONFIG['consumer_secret'])

def create_client_and_opportunity(order_data: Dict) -> Dict:
    """
    Crée un client et une opportunité dans Sellsy à partir des données de commande
    
    Args:
        order_data: Données de la commande contenant les produits et l'adresse
        
    Returns:
        Dictionnaire avec les résultats de la création
    """
    try:
        print("\n\n" + "="*80, flush=True)
        print("="*80, flush=True)
        print("=== DÉBUT create_client_and_opportunity - NOUVEAU CODE ===", flush=True)
        print("="*80, flush=True)
        print("="*80 + "\n", flush=True)
        sys.stdout.flush()
        
        delivery_address = order_data.get('delivery_address', {})
        selected_products = order_data.get('selected_products', [])
        
        # Préparation des données client avec TOUS les champs disponibles
        client_data = {
            'first_name': delivery_address.get('firstName', ''),
            'last_name': delivery_address.get('lastName', ''),
            'name': f"{delivery_address.get('firstName', '')} {delivery_address.get('lastName', '')}".strip(),
            'company_name': delivery_address.get('companyName', ''),  # Nom de l'entreprise
            'siren': delivery_address.get('siren', ''),               # SIREN
            'siret': delivery_address.get('siret', ''),               # SIRET
            'email': delivery_address.get('email', ''),
            'phone': delivery_address.get('phone', ''),
            'address': delivery_address.get('address', ''),
            'city': delivery_address.get('city', ''),
            'postal_code': delivery_address.get('postalCode', ''),
            'country': delivery_address.get('country', 'France'),
            'notes': delivery_address.get('notes', '')                # Notes de livraison
        }
        
        # Récupérer les informations de facturation si différentes
        billing_address = None
        same_billing_address = delivery_address.get('sameBillingAddress', 'on') == 'on'
        
        if not same_billing_address:
            # Adresse de facturation différente
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
        
        # Vérification si le client existe déjà
        print("\n" + "="*80, flush=True)
        print("ÉTAPE 1: Vérification/Création du client", flush=True)
        print("="*80, flush=True)
        print(f"Email recherché: {client_data['email']}", flush=True)
        print(f"Données client préparées: {json.dumps(client_data, indent=2, ensure_ascii=False)}", flush=True)
        sys.stdout.flush()
        
        existing_client = sellsy_api.search_client_by_email(client_data['email'])
        default_address_id = None
        
        if existing_client:
            client_id = existing_client.get('id') or existing_client.get('thirdid')
            print(f"\n✓ Client existant trouvé: {client_id}")
            print(f"Structure complète du client existant: {json.dumps(existing_client, indent=2, ensure_ascii=False, default=str)}")
            
            # Récupérer l'ID de l'adresse principale du client existant
            # Essayer plusieurs champs possibles selon la structure de la réponse Sellsy
            if existing_client.get('addressid'):
                default_address_id = existing_client.get('addressid')
            elif existing_client.get('address_id'):
                default_address_id = existing_client.get('address_id')
            elif existing_client.get('address'):
                # Si l'adresse est un objet, essayer de récupérer son ID
                if isinstance(existing_client.get('address'), dict):
                    default_address_id = existing_client.get('address', {}).get('id') or existing_client.get('address', {}).get('addressid')
                # Si l'adresse est une liste, prendre la première
                elif isinstance(existing_client.get('address'), list) and len(existing_client.get('address', [])) > 0:
                    first_address = existing_client.get('address')[0]
                    if isinstance(first_address, dict):
                        default_address_id = first_address.get('id') or first_address.get('addressid')
            
            if default_address_id:
                print(f"✓ Adresse principale du client existant trouvée: {default_address_id}")
            else:
                print("⚠ Aucune adresse principale trouvée pour le client existant")
        else:
            # Création du nouveau client
            print("\n→ Création d'un nouveau client...")
            print(f"Paramètres de création: {json.dumps(client_data, indent=2, ensure_ascii=False)}")
            
            client_response = sellsy_api.create_client(client_data)
            print(f"\nRéponse création client (complète): {json.dumps(client_response, indent=2, ensure_ascii=False, default=str)}")

            # Récupérer l'ID du client depuis la réponse
            client_id = None
            if isinstance(client_response, dict) and client_response.get('status') == 'success':
                response_data = client_response.get('response', {})
                # Client.create retourne {"response": {"client_id": "XXXXX"}}
                client_id = response_data.get('client_id') or response_data.get('id')
                print(f"\n✓ Nouveau client créé avec l'ID: {client_id}")
                
                # Récupérer l'ID de l'adresse principale créée avec le client
                if response_data.get('addressid'):
                    default_address_id = response_data.get('addressid')
                    print(f"✓ Adresse principale créée avec le client (addressid): {default_address_id}")
                elif response_data.get('address'):
                    if isinstance(response_data.get('address'), dict):
                        default_address_id = response_data.get('address', {}).get('id')
                        print(f"✓ Adresse principale créée avec le client (address.id): {default_address_id}")
                else:
                    print("⚠ Aucune adresse principale retournée dans la réponse de création du client")
            else:
                print(f"✗ ERREUR lors de la création du client: {client_response.get('error')}")

            # Si c'est une entreprise avec un nom et prénom, créer un contact associé
            if client_data.get('company_name') and (client_data.get('first_name') or client_data.get('last_name')):
                print(f"\n→ Création d'un contact pour la société {client_id}...")
                contact_response = sellsy_api.create_contact(client_data, str(client_id))
                print(f"Réponse création contact: {json.dumps(contact_response, indent=2, ensure_ascii=False, default=str)}")

                if contact_response.get('status') == 'success':
                    contact_id = contact_response.get('response', {}).get('id')
                    print(f"✓ Contact créé avec succès: {contact_id}")
                else:
                    print(f"✗ Erreur lors de la création du contact: {contact_response.get('error')}")
        
        # Créer l'adresse de livraison séparée
        print("\n" + "="*80, flush=True)
        print("ÉTAPE 2: Création de l'adresse de livraison", flush=True)
        print("="*80, flush=True)
        print(f"Client ID: {client_id}", flush=True)
        print(f"Adresse de livraison reçue: {json.dumps(delivery_address, indent=2, ensure_ascii=False)}", flush=True)
        sys.stdout.flush()
        
        delivery_address_id = None
        if delivery_address.get('address'):
            print(f"\n→ Création de l'adresse de livraison pour le client {client_id}...")
            delivery_address_data = {
                'address': delivery_address.get('address', ''),
                'city': delivery_address.get('city', ''),
                'postal_code': delivery_address.get('postalCode', ''),
                'country': delivery_address.get('country', 'France'),
                'first_name': delivery_address.get('firstName', ''),
                'last_name': delivery_address.get('lastName', ''),
                'company_name': delivery_address.get('companyName', '')
            }
            print(f"Données d'adresse préparées: {json.dumps(delivery_address_data, indent=2, ensure_ascii=False)}")
            
            delivery_address_response = sellsy_api.add_address_to_client(delivery_address_data, str(client_id), "delivery")
            print(f"\nRéponse création adresse de livraison (complète): {json.dumps(delivery_address_response, indent=2, ensure_ascii=False, default=str)}")
            
            if delivery_address_response.get('status') == 'success':
                response_data = delivery_address_response.get('response', {})
                print(f"\nStructure de la réponse (response): {json.dumps(response_data, indent=2, ensure_ascii=False, default=str)}")
                
                # L'API Sellsy peut retourner l'ID de différentes manières
                delivery_address_id = (
                    response_data.get('address_id') or 
                    response_data.get('id') or 
                    response_data.get('addressid') or
                    str(response_data) if isinstance(response_data, (int, str)) else None
                )
                
                print(f"\n✓ Adresse de livraison créée avec l'ID: {delivery_address_id}")
                print(f"Tentatives de récupération de l'ID:")
                print(f"  - address_id: {response_data.get('address_id')}")
                print(f"  - id: {response_data.get('id')}")
                print(f"  - addressid: {response_data.get('addressid')}")
                print(f"  - response direct: {response_data if isinstance(response_data, (int, str)) else 'N/A'}")
                
                # Mettre à jour le client pour définir cette adresse comme adresse de livraison principale
                if delivery_address_id:
                    print(f"\n→ Mise à jour du client {client_id} pour définir l'adresse de livraison principale...")
                    print(f"Paramètres de mise à jour: maindelivaddressid = {delivery_address_id}")
                    
                    update_response = sellsy_api.update_client(str(client_id), {
                        'maindelivaddressid': str(delivery_address_id)
                    })
                    print(f"Réponse mise à jour client (complète): {json.dumps(update_response, indent=2, ensure_ascii=False, default=str)}")
                    
                    if update_response.get('status') != 'success':
                        print(f"✗ ATTENTION: La mise à jour de l'adresse de livraison principale a échoué")
                        print(f"  Erreur: {update_response.get('error')}")
                    else:
                        print(f"✓ Adresse de livraison principale définie avec succès")
                else:
                    print(f"✗ ATTENTION: Impossible de récupérer l'ID de l'adresse de livraison créée")
                    print(f"  Structure de response_data: {type(response_data)} = {response_data}")
            else:
                error_msg = delivery_address_response.get('error') or delivery_address_response.get('message') or str(delivery_address_response)
                print(f"\n✗ ERREUR lors de la création de l'adresse de livraison")
                print(f"  Message d'erreur: {error_msg}")
                print(f"  Réponse complète: {json.dumps(delivery_address_response, indent=2, ensure_ascii=False, default=str)}")
                # En cas d'erreur, utiliser l'adresse principale par défaut
                delivery_address_id = default_address_id
                print(f"  → Utilisation de l'adresse principale par défaut: {default_address_id}")
        else:
            print(f"\n⚠ Pas d'adresse de livraison fournie (champ 'address' vide ou manquant)")
            print(f"  Contenu de delivery_address: {json.dumps(delivery_address, indent=2, ensure_ascii=False)}")
        
        # Déterminer l'ID de l'adresse de facturation à utiliser
        print("\n" + "="*80)
        print("ÉTAPE 3: Gestion de l'adresse de facturation")
        print("="*80)
        print(f"Même adresse de facturation que livraison: {same_billing_address}")
        
        billing_address_id = None
        if same_billing_address:
            # Si l'adresse de facturation est identique, utiliser l'adresse de livraison
            billing_address_id = delivery_address_id if delivery_address_id else default_address_id
            if billing_address_id:
                print(f"✓ Adresse de facturation identique à l'adresse de livraison")
                print(f"  Utilisation de l'adresse de livraison: {billing_address_id}")
            else:
                print(f"⚠ Aucune adresse disponible pour la facturation")
        elif billing_address and billing_address.get('address'):
            # Si l'adresse de facturation est différente, créer une nouvelle adresse
            print(f"\n→ Création d'une adresse de facturation différente pour le client {client_id}...")
            print(f"Données d'adresse de facturation: {json.dumps(billing_address, indent=2, ensure_ascii=False)}")
            
            billing_address_response = sellsy_api.add_address_to_client(billing_address, str(client_id), "billing")
            print(f"Réponse création adresse de facturation (complète): {json.dumps(billing_address_response, indent=2, ensure_ascii=False, default=str)}")
            
            if billing_address_response.get('status') == 'success':
                response_data = billing_address_response.get('response', {})
                billing_address_id = response_data.get('address_id') or response_data.get('id')
                print(f"✓ Adresse de facturation créée avec l'ID: {billing_address_id}")
            else:
                error_msg = billing_address_response.get('error') or billing_address_response.get('message') or str(billing_address_response)
                print(f"✗ Erreur lors de la création de l'adresse de facturation: {error_msg}")
                # En cas d'erreur, utiliser l'adresse principale par défaut
                billing_address_id = default_address_id
                print(f"  → Utilisation de l'adresse principale par défaut: {default_address_id}")
        else:
            print(f"⚠ Pas d'adresse de facturation fournie ou différente")
        
        # Mettre à jour les informations de facturation du client si nécessaire
        if billing_address and (billing_address.get('siren') or billing_address.get('siret')):
            # Si l'adresse de facturation a un SIREN/SIRET différent, on pourrait mettre à jour le client
            # Pour l'instant, on note juste cette information dans les notes
            if client_data.get('notes'):
                client_data['notes'] += f"\nSIREN facturation: {billing_address.get('siren', '')}"
                client_data['notes'] += f"\nSIRET facturation: {billing_address.get('siret', '')}"

        if not client_id:
            print(f"Impossible de récupérer l'ID du client. Réponse complète: {client_response if 'client_response' in locals() else 'N/A'}")
            raise Exception("Impossible de récupérer l'ID du client")

        # Préparation des données du devis
        product_names = [product.get('nom_commercial', product.get('product', '')) for product in selected_products]
        estimate_subject = f"Devis - {', '.join(product_names[:3])}"  # Limite à 3 produits pour le sujet

        # Récupérer les notes des produits depuis order_data
        product_notes = order_data.get('product_notes', '')

        # Construire les notes du devis avec toutes les informations
        estimate_notes_parts = []

        # Ajouter les notes de livraison de l'adresse
        if delivery_address.get('notes'):
            estimate_notes_parts.append(f"Notes de livraison: {delivery_address.get('notes')}")

        estimate_notes = "\n".join(estimate_notes_parts) if estimate_notes_parts else ''

        estimate_data = {
            'client_id': client_id,
            'contact_id': contact_id if 'contact_id' in locals() else None,
            'billing_address_id': billing_address_id,  # ID de l'adresse de facturation
            'delivery_address_id': delivery_address_id,  # ID de l'adresse de livraison
            'name': estimate_subject,
            'products': selected_products,
            'product_notes': product_notes,  # Notes spécifiques aux produits
            'notes': estimate_notes  # Notes générales du devis
        }

        # Création du devis
        print("\n" + "="*80)
        print("ÉTAPE 4: Création du devis")
        print("="*80)
        print(f"Création du devis pour le client {client_id}...")
        estimate_response = sellsy_api.create_estimate(estimate_data)
        print(f"Réponse création devis: {json.dumps(estimate_response, indent=2, ensure_ascii=False, default=str)}")

        estimate_id = None
        if estimate_response.get('status') == 'success':
            response_data = estimate_response.get('response', {})
            estimate_id = response_data.get('doc_id') or response_data.get('docid') or response_data.get('id')
            print(f"✓ Devis créé avec succès: {estimate_id}")
        else:
            print(f"✗ Erreur lors de la création du devis: {estimate_response.get('error')}")
        
        # Vérification des adresses du client après création du devis
        print("\n" + "="*80, flush=True)
        print("ÉTAPE 5: Vérification des adresses du client", flush=True)
        print("="*80, flush=True)
        print(f"Récupération des informations complètes du client {client_id}...", flush=True)
        sys.stdout.flush()
        
        # Récupérer le client complet avec Client.getOne
        print(f"\n[API CALL] Client.getOne pour client_id={client_id}", flush=True)
        full_client = sellsy_api.get_client_by_id(str(client_id))
        sys.stdout.flush()
        
        if full_client:
            print(f"\n✓ Client récupéré avec succès", flush=True)
            print(f"Structure complète du client: {json.dumps(full_client, indent=2, ensure_ascii=False, default=str)}", flush=True)
            
            # Extraire les informations d'adresse du client
            print(f"\n--- INFORMATIONS D'ADRESSES DU CLIENT ---", flush=True)
            print(f"Adresse principale (address): {full_client.get('address', 'N/A')}", flush=True)
            print(f"Adresse de livraison (shippingAddress): {full_client.get('shippingAddress', 'N/A')}", flush=True)
            print(f"ID adresse principale (mainaddressid): {full_client.get('mainaddressid', 'N/A')}", flush=True)
            print(f"ID adresse livraison principale (maindelivaddressid): {full_client.get('maindelivaddressid', 'N/A')}", flush=True)
            
            # Récupérer toutes les adresses via Address.getList
            print(f"\n[API CALL] Address.getList pour thirdid={client_id}", flush=True)
            addresses_list = sellsy_api.get_client_addresses(str(client_id))
            sys.stdout.flush()
            if addresses_list:
                print(f"✓ Adresses récupérées avec succès")
                print(f"Structure complète des adresses: {json.dumps(addresses_list, indent=2, ensure_ascii=False, default=str)}")
                
                # Extraire les adresses individuelles
                result = addresses_list.get('result', {})
                if isinstance(result, dict):
                    print(f"\n--- LISTE DES ADRESSES DU CLIENT ---")
                    for addr_id, addr_data in result.items():
                        print(f"\nAdresse ID: {addr_id}")
                        print(f"  Nom: {addr_data.get('name', 'N/A')}")
                        print(f"  Part1: {addr_data.get('part1', 'N/A')}")
                        print(f"  Part2: {addr_data.get('part2', 'N/A')}")
                        print(f"  Code postal: {addr_data.get('zip', 'N/A')}")
                        print(f"  Ville: {addr_data.get('town', 'N/A')}")
                        print(f"  Pays: {addr_data.get('countrycode', 'N/A')}")
                        print(f"  Type: {addr_data.get('type', 'N/A')}")
                elif isinstance(result, list):
                    print(f"\n--- LISTE DES ADRESSES DU CLIENT ({len(result)} adresse(s)) ---")
                    for idx, addr_data in enumerate(result):
                        print(f"\nAdresse #{idx + 1}")
                        print(f"  {json.dumps(addr_data, indent=2, ensure_ascii=False, default=str)}")
                else:
                    print(f"⚠ Format de réponse inattendu pour les adresses: {type(result)}")
            else:
                print(f"✗ Aucune adresse trouvée ou erreur lors de la récupération")
        else:
            print(f"✗ Impossible de récupérer les informations du client")

        return {
            'success': True,
            'client_id': client_id,
            'contact_id': contact_id if 'contact_id' in locals() else None,
            'estimate_id': estimate_id,
            'client_created': existing_client is None,
            'message': 'Client, contact et devis créés avec succès dans Sellsy' if estimate_id else 'Client créé mais erreur lors de la création du devis'
        }
        
    except Exception as e:
        print(f"Erreur lors de la création client/opportunité: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Erreur lors de la création dans Sellsy'
        } 