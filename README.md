# RAPH PANEL - Application de Demande de Devis

Application web permettant aux clients de sélectionner des produits et de créer des demandes de devis, avec intégration automatique dans Sellsy CRM.

## 📁 Structure du Projet

```
Sellsy/
├── frontend/          # Interface utilisateur (déployé sur Netlify)
│   ├── index.html
│   ├── script.js
│   ├── styles.css
│   └── _redirects
│
├── backend/           # API Flask (déployé sur Railway/Render)
│   ├── app.py
│   ├── sellsy_integration.py
│   ├── config.py
│   ├── requirements.txt
│   ├── Procfile
│   └── runtime.txt
│
├── data/              # Fichiers Excel des produits
│   └── *.xlsx
│
├── netlify.toml       # Configuration Netlify
├── .gitignore
└── README.md
```

## 🚀 Démarrage Local

### Prérequis
- Python 3.7+
- pip

### Installation

1. **Installer les dépendances du backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Démarrer les serveurs**

   **Option 1 : Script automatique**
   ```bash
   # Double-cliquez sur test_complete.bat
   ```

   **Option 2 : Manuel**
   ```bash
   # Terminal 1 - Backend
   cd backend
   python app.py
   
   # Terminal 2 - Frontend
   cd frontend
   python -m http.server 8000
   ```

3. **Accéder à l'application**
   - Frontend : http://localhost:8000
   - Backend API : http://localhost:5000/api

## 🎯 Fonctionnalités

- ✅ Sélection de produits par catégorie
- ✅ Filtres par couleur, taille, caractéristiques
- ✅ Panier avec jauge de minimum (1000€)
- ✅ Formulaire d'adresse de livraison et facturation
- ✅ Intégration automatique Sellsy (création client, devis)
- ✅ Interface responsive

## 📦 Déploiement

### Backend (Railway/Render)
1. Connectez votre repository Git
2. Configurez le répertoire : `backend`
3. Configurez les variables d'environnement Sellsy
4. Déployez

### Frontend (Netlify)
1. Connectez votre repository Git
2. Configurez :
   - **Publish directory** : `frontend`
   - **Build command** : (vide)
3. Ajoutez la variable d'environnement :
   - `VITE_API_URL` = URL de votre backend
4. Déployez

Consultez `NETLIFY_DEPLOY.md` pour plus de détails.

## 🔧 Configuration

### Backend
Les tokens Sellsy sont configurés dans `backend/config.py`.

### Frontend
L'URL de l'API est détectée automatiquement :
- En local : `http://localhost:5000/api`
- En production : Utilise la variable d'environnement `VITE_API_URL`

## 📝 API Endpoints

- `GET /api/categories` - Liste des catégories
- `GET /api/products` - Tous les produits
- `GET /api/products/<category>` - Produits d'une catégorie
- `GET /api/sizes` - Toutes les tailles
- `GET /api/sizes/<category>` - Tailles d'une catégorie
- `POST /api/order` - Soumettre une commande

## 🛠️ Technologies

- **Frontend** : HTML, CSS, JavaScript (vanilla)
- **Backend** : Python, Flask, Flask-CORS
- **Intégration** : API Sellsy V1
- **Données** : Fichiers Excel (pandas, openpyxl)

## 📄 Licence

Développé pour RAPH PANEL. Tous droits réservés.
