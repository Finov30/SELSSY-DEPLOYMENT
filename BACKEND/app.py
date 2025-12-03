from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
import re
from pathlib import Path
from sellsy_integration import create_client_and_opportunity

app = Flask(__name__)
# Configurer CORS pour accepter les requêtes depuis Netlify
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # En production, spécifiez votre domaine Netlify
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration
# En production, utiliser le chemin absolu ou une variable d'environnement
DATA_DIR = Path(os.environ.get('DATA_DIR', str(Path(__file__).parent.parent / "data")))
# Si DATA_DIR n'existe pas, essayer le chemin relatif depuis BACKEND
if not DATA_DIR.exists():
    DATA_DIR = Path(__file__).parent.parent / "DATA"

def clean_value(value):
    """Nettoie une valeur pour la rendre JSON-sérialisable"""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value) or value != value:  # NaN check
            return 0
        return value
    return str(value) if value is not None else ""



def load_products():
    """Charge tous les produits depuis les fichiers Excel"""
    all_products = []
    
    print(f"Recherche des fichiers Excel dans: {DATA_DIR}")
    print(f"Chemin absolu: {DATA_DIR.absolute()}")
    
    for excel_file in DATA_DIR.glob("*.xlsx"):
        try:
            print(f"Lecture du fichier: {excel_file}")
            
            # Lire le fichier Excel en ignorant les 3 premières lignes d'en-tête
            df = pd.read_excel(excel_file, header=None, skiprows=3)
            
            product_name = excel_file.stem  # Nom du fichier sans extension
            print(f"Catégorie: {product_name}")
            print(f"Colonnes disponibles: {df.columns.tolist()}")
            print(f"Nombre de lignes: {len(df)}")
            
            # Mapping des colonnes selon la structure réelle des fichiers
            # Colonne 0: Code produit, Colonne 1: Type cadre, Colonne 2: Format, 
            # Colonne 14: Nom du cadre (ex: ANDREA), Colonne 32: Coût achat HT 2025
            
            # Filtrer les lignes avec des données valides (code produit non-null)
            df = df.dropna(subset=[0])  # Supprimer les lignes sans code produit
            print(f"Nombre de lignes après filtrage: {len(df)}")
            
            for _, row in df.iterrows():
                try:
                    # Récupérer les valeurs des colonnes selon la structure réelle
                    code_produit_sellsy = clean_value(row[9])  # Colonne SELLSY (ex: "050612 - GAELLE 80")
                    # Extraire juste le code (avant le tiret)
                    code_produit = code_produit_sellsy.split(' - ')[0].strip() if code_produit_sellsy and ' - ' in str(code_produit_sellsy) else code_produit_sellsy

                    type_cadre = clean_value(row[1])
                    format_cadre = clean_value(row[2])
                    nom_cadre = clean_value(row[14])  # Nom du cadre (ex: ANDREA)
                    cout_achat = clean_value(row[32])  # COUT ACHAT HT 2025 (colonne 32)
                    
                    # Colonne J (index 9) : Référence Atelier
                    reference_atelier = clean_value(row[9])  # Colonne J
                    # Colonne AE (index 30) : DESCRIPTION MAISON RAPHAEL
                    description_maison_raphael = clean_value(row[30])  # Colonne AE
                    
                    # Récupérer les valeurs binaires
                    vitre_binaire = clean_value(row[17])  # VITRE BINAIRE (1/0)
                    rehausse_binaire = clean_value(row[18])  # REHAUSSE BINAIRE (1/0)
                    chevalet_binaire = clean_value(row[19])  # CHEVALET BINAIRE (1/0)
                    possibilite_chevalet_binaire = clean_value(row[20])  # POSSIBILITE CHEVALET BINAIRE (1/0)
                    
                    # Vérifier que nous avons les données essentielles
                    if code_produit and format_cadre:
                        # Construire le nom commercial
                        nom_commercial = f"{nom_cadre} {format_cadre}"
                        
                        # Si le nom du cadre est vide, utiliser le type de cadre
                        if not nom_cadre or nom_cadre == '' or nom_cadre == 'nan':
                            nom_commercial = f"{type_cadre} {format_cadre}"
                        
                        # Vérifier que nous avons au moins un nom de produit
                        if nom_commercial and nom_commercial != '' and nom_commercial != 'nan':
                            product_data = {
                                'product_category': product_name,
                                'nom_commercial': nom_commercial,
                                'frame_size': format_cadre,
                                'cout_achat_ht_2025': cout_achat,
                                'code_produit': code_produit,
                                'type_cadre': type_cadre,
                                'nom_cadre': nom_cadre,
                                'vitre_binaire': vitre_binaire,
                                'rehausse_binaire': rehausse_binaire,
                                'chevalet_binaire': chevalet_binaire,
                                'possibilite_chevalet_binaire': possibilite_chevalet_binaire,
                                'reference_atelier': reference_atelier,  # Colonne J
                                'description_maison_raphael': description_maison_raphael  # Colonne AE
                            }
                            all_products.append(product_data)
                        
                except Exception as row_error:
                    print(f"Erreur lors du traitement de la ligne {_}: {row_error}")
                    continue
            
            print(f"Produits ajoutés pour {product_name}: {len([p for p in all_products if p['product_category'] == product_name])}")
                
        except Exception as e:
            print(f"Erreur lors de la lecture de {excel_file}: {e}")
    
    print(f"Total des produits chargés: {len(all_products)}")
    return all_products

def get_available_sizes(products):
    """Récupère toutes les tailles disponibles depuis les produits"""
    sizes = set()
    for product in products:
        if product.get('frame_size') and product['frame_size']:
            sizes.add(product['frame_size'])
    
    # Trier les tailles par ordre croissant (largeur*hauteur)
    def sort_key(size):
        try:
            if '*' in size:
                width, height = size.split('*')
                return (int(width), int(height))
            return (0, 0)
        except:
            return (0, 0)
    
    return sorted(list(sizes), key=sort_key)

@app.route('/api/products', methods=['GET'])
def get_products():
    """Récupère tous les produits"""
    try:
        products = load_products()
        return jsonify({
            'success': True,
            'products': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Récupère toutes les catégories de produits"""
    try:
        categories = []
        for excel_file in DATA_DIR.glob("*.xlsx"):
            categories.append(excel_file.stem)
        
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/<category>', methods=['GET'])
def get_products_by_category(category):
    """Récupère les produits d'une catégorie spécifique"""
    try:
        excel_file = DATA_DIR / f"{category}.xlsx"
        if not excel_file.exists():
            return jsonify({
                'success': False,
                'error': 'Catégorie non trouvée'
            }), 404
        
        # Lire le fichier Excel en ignorant les 3 premières lignes d'en-tête
        df = pd.read_excel(excel_file, header=None, skiprows=3)
        df = df.dropna(subset=[0])  # Supprimer les lignes sans code produit
        
        products = []
        for _, row in df.iterrows():
            try:
                # Récupérer les valeurs des colonnes selon la structure réelle
                code_produit_sellsy = clean_value(row[9])  # Colonne SELLSY (ex: "050612 - GAELLE 80")
                # Extraire juste le code (avant le tiret)
                code_produit = code_produit_sellsy.split(' - ')[0].strip() if code_produit_sellsy and ' - ' in str(code_produit_sellsy) else code_produit_sellsy

                type_cadre = clean_value(row[1])
                format_cadre = clean_value(row[2])
                nom_cadre = clean_value(row[14])  # Nom du cadre (ex: ANDREA)
                cout_achat = clean_value(row[32])  # COUT ACHAT HT 2025 (colonne 32)
                
                # Récupérer les valeurs binaires
                vitre_binaire = clean_value(row[17])  # VITRE BINAIRE (1/0)
                rehausse_binaire = clean_value(row[18])  # REHAUSSE BINAIRE (1/0)
                chevalet_binaire = clean_value(row[19])  # CHEVALET BINAIRE (1/0)
                possibilite_chevalet_binaire = clean_value(row[20])  # POSSIBILITE CHEVALET BINAIRE (1/0)
                
                # Colonne J (index 9) : Référence Atelier
                reference_atelier = clean_value(row[9])  # Colonne J
                # Colonne AE (index 30) : DESCRIPTION MAISON RAPHAEL
                description_maison_raphael = clean_value(row[30])  # Colonne AE
                
                # Vérifier que nous avons les données essentielles
                if code_produit and format_cadre:
                    # Construire le nom commercial
                    nom_commercial = f"{nom_cadre} {format_cadre}"
                    
                    # Si le nom du cadre est vide, utiliser le type de cadre
                    if not nom_cadre or nom_cadre == '' or nom_cadre == 'nan':
                        nom_commercial = f"{type_cadre} {format_cadre}"
                    
                    # Vérifier que nous avons au moins un nom de produit
                    if nom_commercial and nom_commercial != '' and nom_commercial != 'nan':
                        product_data = {
                            'product_category': category,
                            'nom_commercial': nom_commercial,
                            'frame_size': format_cadre,
                            'cout_achat_ht_2025': cout_achat,
                            'code_produit': code_produit,
                            'type_cadre': type_cadre,
                            'nom_cadre': nom_cadre,
                            'vitre_binaire': vitre_binaire,
                            'rehausse_binaire': rehausse_binaire,
                            'chevalet_binaire': chevalet_binaire,
                            'possibilite_chevalet_binaire': possibilite_chevalet_binaire,
                            'reference_atelier': reference_atelier,  # Colonne J
                            'description_maison_raphael': description_maison_raphael  # Colonne AE
                        }
                        products.append(product_data)
                    
            except Exception as row_error:
                print(f"Erreur lors du traitement de la ligne {_}: {row_error}")
                continue
        
        return jsonify({
            'success': True,
            'products': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sizes', methods=['GET'])
def get_sizes():
    """Récupère toutes les tailles de cadres disponibles"""
    try:
        products = load_products()
        sizes = get_available_sizes(products)
        
        return jsonify({
            'success': True,
            'sizes': sizes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sizes/<category>', methods=['GET'])
def get_sizes_by_category(category):
    """Récupère les tailles disponibles pour une catégorie spécifique"""
    try:
        products = load_products()
        category_products = [p for p in products if p['product_category'] == category]
        sizes = get_available_sizes(category_products)
        
        return jsonify({
            'success': True,
            'sizes': sizes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/order', methods=['POST'])
def submit_order():
    """Soumet une commande avec les produits sélectionnés et l'adresse de livraison"""
    try:
        data = request.get_json()
        
        # Validation des données
        if not data.get('selected_products') or not data.get('delivery_address'):
            return jsonify({
                'success': False,
                'error': 'Données manquantes'
            }), 400
        
        # Génération de l'ID de commande
        order_id = f"DEVIS-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        
        # Création du client et de l'opportunité dans Sellsy
        sellsy_result = create_client_and_opportunity(data)
        
        order_summary = {
            'order_id': order_id,
            'products': data['selected_products'],
            'delivery_address': data['delivery_address'],
            'timestamp': pd.Timestamp.now().isoformat(),
            'sellsy_integration': sellsy_result
        }
        
        if sellsy_result['success']:
            return jsonify({
                'success': True,
                'message': 'Demande de devis soumise avec succès et intégrée dans Sellsy',
                'order': order_summary,
                'sellsy_client_id': sellsy_result.get('client_id'),
                'sellsy_opportunity_id': sellsy_result.get('opportunity_id')
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Demande de devis soumise avec succès (erreur d\'intégration Sellsy)',
                'order': order_summary,
                'sellsy_error': sellsy_result.get('error')
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    import os
    # En production, utiliser le PORT fourni par l'environnement (Railway, Render, Heroku)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port) 