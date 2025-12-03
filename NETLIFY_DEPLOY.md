# Guide de Déploiement sur Netlify

## ⚠️ Important : Architecture du Projet

Ce projet est composé de **deux parties** :
1. **Frontend** (UI/) : Peut être déployé sur Netlify
2. **Backend** (BACKEND/) : Doit être hébergé séparément (Railway, Render, Heroku, etc.)

Netlify ne peut **pas** héberger directement un serveur Flask Python.

## 📋 Prérequis

1. Compte Netlify (gratuit)
2. Backend hébergé ailleurs avec une URL publique
3. Git repository (GitHub, GitLab, Bitbucket)

## 🚀 Déploiement du Frontend sur Netlify

### Option 1 : Déploiement via Git (Recommandé)

1. **Pousser le code sur GitHub/GitLab**
   ```bash
   git add .
   git commit -m "Préparation pour Netlify"
   git push origin main
   ```

2. **Connecter Netlify à votre repository**
   - Allez sur [app.netlify.com](https://app.netlify.com)
   - Cliquez sur "Add new site" > "Import an existing project"
   - Connectez votre repository Git
   - Configurez les paramètres de build :
     - **Base directory** : (laisser vide)
     - **Build command** : (laisser vide, site statique)
     - **Publish directory** : `UI`

3. **Configurer les variables d'environnement**
   - Dans Netlify : Site settings > Environment variables
   - Ajoutez : `VITE_API_URL` = `https://votre-backend.herokuapp.com/api`
   - (Remplacez par l'URL réelle de votre backend)

4. **Déployer**
   - Netlify déploiera automatiquement à chaque push

### Option 2 : Déploiement via Netlify CLI

1. **Installer Netlify CLI**
   ```bash
   npm install -g netlify-cli
   ```

2. **Se connecter**
   ```bash
   netlify login
   ```

3. **Initialiser le site**
   ```bash
   netlify init
   ```
   - Choisissez "Create & configure a new site"
   - Publish directory : `UI`
   - Build command : (laisser vide)

4. **Déployer**
   ```bash
   netlify deploy --prod
   ```

## 🔧 Configuration du Backend

Le backend Flask doit être hébergé séparément. Options recommandées :

### Option 1 : Railway (Recommandé - Gratuit)
1. Créez un compte sur [railway.app](https://railway.app)
2. Créez un nouveau projet
3. Connectez votre repository Git
4. Railway détectera automatiquement Python
5. Configurez les variables d'environnement nécessaires
6. Railway fournira une URL publique (ex: `https://votre-app.railway.app`)

### Option 2 : Render
1. Créez un compte sur [render.com](https://render.com)
2. Créez un nouveau "Web Service"
3. Connectez votre repository
4. Configurez :
   - Build Command : `cd BACKEND && pip install -r requirements.txt`
   - Start Command : `cd BACKEND && python app.py`
5. Render fournira une URL publique

### Option 3 : Heroku
1. Créez un compte sur [heroku.com](https://heroku.com)
2. Installez Heroku CLI
3. Créez une application :
   ```bash
   heroku create votre-app-name
   ```
4. Déployez :
   ```bash
   git subtree push --prefix BACKEND heroku main
   ```

## 📝 Fichiers de Configuration (Déjà créés à la racine)

Les fichiers nécessaires pour le déploiement Railway sont déjà placés à la racine du projet :
- `Procfile` : Indique à Railway comment lancer l'application (`web: gunicorn --chdir BACKEND app:app`)
- `requirements.txt` : Liste les dépendances Python
- `runtime.txt` : Spécifie la version de Python

### Modifier `BACKEND/app.py` (Déjà fait)
L'application est déjà configurée pour utiliser le port fourni par l'environnement :
```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

## 🔐 Variables d'Environnement à Configurer

### Sur Netlify (Frontend)
- `VITE_API_URL` : URL de votre backend (ex: `https://votre-backend.railway.app/api`)

### Sur le Backend (Railway/Render/Heroku)
- Variables Sellsy (déjà dans `BACKEND/config.py`)
- `PORT` : Port du serveur (généralement géré automatiquement)
- `DATA_DIR` : Chemin vers les fichiers Excel (à adapter selon l'hébergement)

## 📁 Gestion des Fichiers Excel

Les fichiers Excel dans `DATA/` doivent être accessibles au backend. Options :

1. **Inclure dans le déploiement** : Ajoutez `DATA/` au repository Git
2. **Stockage cloud** : Utilisez S3, Google Cloud Storage, etc.
3. **Base de données** : Migrez les données vers une base de données

## ✅ Checklist de Déploiement

- [ ] Backend déployé et accessible publiquement
- [ ] URL du backend configurée dans Netlify (variable `VITE_API_URL`)
- [ ] Fichiers Excel accessibles au backend
- [ ] Variables d'environnement Sellsy configurées sur le backend
- [ ] CORS configuré sur le backend pour accepter les requêtes depuis Netlify
- [ ] Test de l'application complète

## 🧪 Test après Déploiement

1. Vérifiez que le frontend se charge correctement
2. Testez la connexion API (ouvrez la console du navigateur)
3. Testez la sélection de produits
4. Testez la soumission d'une commande
5. Vérifiez les logs du backend pour les erreurs

## 🐛 Résolution de Problèmes

### Erreur CORS
- Vérifiez que `Flask-CORS` est configuré dans `BACKEND/app.py`
- Vérifiez que l'URL du frontend est autorisée

### Erreur 404 sur les API
- Vérifiez que `VITE_API_URL` est correctement configurée
- Vérifiez que le backend est accessible publiquement

### Fichiers Excel non trouvés
- Vérifiez le chemin `DATA_DIR` dans `BACKEND/app.py`
- Assurez-vous que les fichiers sont inclus dans le déploiement

## 📞 Support

En cas de problème, vérifiez :
1. Les logs Netlify (Deploys > [votre déploiement] > Deploy log)
2. Les logs du backend
3. La console du navigateur (F12)

