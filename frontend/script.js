// Configuration
// Utiliser la variable d'environnement Netlify ou détecter automatiquement l'environnement
function getApiBaseUrl() {
    // 1. Vérifier la variable d'environnement Netlify (définie dans netlify.toml ou dans les paramètres)
    if (window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    
    // 2. En développement local
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:5000/api';
    }
    
    // 3. En production, utiliser l'URL du backend configurée
    // Cette valeur doit être définie dans les variables d'environnement Netlify
    // ou dans un fichier de configuration
    return 'https://votre-backend.railway.app/api'; // ⚠️ À REMPLACER par votre URL backend réelle
}

const API_BASE_URL = getApiBaseUrl();
console.log('API Base URL:', API_BASE_URL);

// État global de l'application
let appState = {
    categories: [],
    products: [],
    sizes: [],
    selectedProducts: [],
    currentStep: 1,
    deliveryAddress: null,
    // Pagination
    currentPage: 1,
    productsPerPage: 12,
    filteredProducts: [],
    colors: [] // Ajout de l'état pour les couleurs
};

// Éléments DOM
const elements = {
    // Steps
    steps: document.querySelectorAll('.step'),
    stepContents: document.querySelectorAll('.step-content'),
    
    // Product selection
    categorySelect: document.getElementById('categorySelect'),
    colorSelect: document.getElementById('colorSelect'),
    sizeSelect: document.getElementById('sizeSelect'),
    productsGrid: document.getElementById('productsGrid'),
    loadMoreContainer: document.getElementById('loadMoreContainer'),
    loadMoreBtn: document.getElementById('loadMoreBtn'),
    selectedProductsList: document.getElementById('selectedProductsList'),
    productNotes: document.getElementById('productNotes'),
    totalHT: document.getElementById('totalHT'),
    totalTTC: document.getElementById('totalTTC'),
    
    // Gauge elements
    currentCost: document.getElementById('currentCost'),
    maxCost: document.getElementById('maxCost'),
    gaugeFill: document.getElementById('gaugeFill'),
    gaugePercentage: document.getElementById('gaugePercentage'),
    selectedCount: document.getElementById('selectedCount'),
    totalCost: document.getElementById('totalCost'),
    
    // Navigation buttons
    nextStep1: document.getElementById('nextStep1'),
    prevStep2: document.getElementById('prevStep2'),
    nextStep2: document.getElementById('nextStep2'),
    prevStep3: document.getElementById('prevStep3'),
    submitOrder: document.getElementById('submitOrder'),
    
    // Delivery form
    deliveryForm: document.getElementById('deliveryForm'),
    
    // Confirmation
    orderProductsList: document.getElementById('orderProductsList'),
    orderAddress: document.getElementById('orderAddress'),
    orderTotalHT: document.getElementById('orderTotalHT'),
    orderTotalTTC: document.getElementById('orderTotalTTC'),
    
    // Modal
    loadingOverlay: document.getElementById('loadingOverlay'),
    successModal: document.getElementById('successModal'),
    orderNumber: document.getElementById('orderNumber'),
    newOrder: document.getElementById('newOrder'),
    
    // Sellsy integration
    sellsyInfo: document.getElementById('sellsyInfo'),
    sellsyError: document.getElementById('sellsyError'),
    sellsyClientId: document.getElementById('sellsyClientId'),
    sellsyOpportunityId: document.getElementById('sellsyOpportunityId'),
    sellsyErrorMessage: document.getElementById('sellsyErrorMessage')
};

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
});

// Initialisation
async function initializeApp() {
    showLoading(true);
    try {
        console.log('Démarrage de l\'initialisation...');
        console.log('API URL:', API_BASE_URL);
        
        await loadCategories();
        console.log('Catégories chargées avec succès');
        
        await loadAllProducts();
        console.log('Produits chargés avec succès');
        
        // Charger les couleurs APRÈS les produits
        loadAllColors();
        console.log('Couleurs chargées avec succès');
        
        await loadAllSizes();
        console.log('Tailles chargées avec succès');
        
        showLoading(false);
        console.log('Initialisation terminée avec succès');
    } catch (error) {
        console.error('Erreur lors de l\'initialisation:', error);
        showLoading(false);
        
        // Message d'erreur plus détaillé
        let errorMessage = 'Erreur lors du chargement des données.\n\n';
        errorMessage += 'Détails: ' + error.message + '\n\n';
        errorMessage += 'Vérifiez que:\n';
        errorMessage += '1. Le serveur Flask est démarré sur le port 5000\n';
        errorMessage += '2. L\'API est accessible\n';
        errorMessage += '3. Les fichiers Excel sont présents dans le dossier DATA\n\n';
        errorMessage += 'Veuillez rafraîchir la page après avoir vérifié ces points.';
        
        alert(errorMessage);
    }
}

// Gestion de la case à cocher pour l'adresse de facturation
function handleBillingAddressToggle() {
    const sameBillingAddressCheckbox = document.getElementById('sameBillingAddress');
    const billingAddressFields = document.getElementById('billingAddressFields');
    const billingInputs = billingAddressFields.querySelectorAll('input, select, textarea');
    
    if (sameBillingAddressCheckbox.checked) {
        billingAddressFields.style.display = 'none';
        billingInputs.forEach(input => {
            input.disabled = true;
            input.value = '';
        });
    } else {
        billingAddressFields.style.display = 'block';
        billingInputs.forEach(input => {
            input.disabled = false;
        });
    }
}


// Configuration des événements
function setupEventListeners() {
    // Navigation des étapes
    elements.nextStep1.addEventListener('click', () => goToStep(2));
    elements.prevStep2.addEventListener('click', () => goToStep(1));
    elements.nextStep2.addEventListener('click', () => goToStep(3));
    elements.prevStep3.addEventListener('click', () => goToStep(2));
    
    // Sélection de catégorie
    elements.categorySelect.addEventListener('change', handleCategoryChange);
    
    // Sélection de taille
    elements.sizeSelect.addEventListener('change', handleSizeChange);
    
    // Sélection de couleur
    elements.colorSelect.addEventListener('change', handleColorChange);
    
    // Filtres binaires
    const vitreFilter = document.getElementById('vitreFilter');
    const rehausseFilter = document.getElementById('rehausseFilter');
    const chevaletFilter = document.getElementById('chevaletFilter');
    const possibiliteChevaletFilter = document.getElementById('possibiliteChevaletFilter');
    
    if (vitreFilter) vitreFilter.addEventListener('change', handleBinaryFiltersChange);
    if (rehausseFilter) rehausseFilter.addEventListener('change', handleBinaryFiltersChange);
    if (chevaletFilter) chevaletFilter.addEventListener('change', handleBinaryFiltersChange);
    if (possibiliteChevaletFilter) possibiliteChevaletFilter.addEventListener('change', handleBinaryFiltersChange);
    
    // Bouton "Voir plus"
    elements.loadMoreBtn.addEventListener('click', loadMoreProducts);
    
    // Soumission de commande
    elements.submitOrder.addEventListener('click', submitOrder);
    elements.newOrder.addEventListener('click', resetApp);
    
    // Gestion de la case à cocher pour l'adresse de facturation
    const sameBillingAddressCheckbox = document.getElementById('sameBillingAddress');
    if (sameBillingAddressCheckbox) {
        sameBillingAddressCheckbox.addEventListener('change', handleBillingAddressToggle);
        // Initialiser l'état de la case à cocher
        handleBillingAddressToggle();
    }
}

// Chargement des catégories
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE_URL}/categories`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            appState.categories = data.categories;
            populateCategorySelect();
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des catégories:', error);
        throw error;
    }
}

// Chargement de tous les produits
async function loadAllProducts() {
    try {
        const response = await fetch(`${API_BASE_URL}/products`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            appState.products = data.products;
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des produits:', error);
        throw error;
    }
}

// Chargement de toutes les tailles
async function loadAllSizes() {
    try {
        const response = await fetch(`${API_BASE_URL}/sizes`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            appState.sizes = data.sizes;
            populateSizeSelect();
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des tailles:', error);
        throw error;
    }
}

// Chargement de toutes les couleurs disponibles
function loadAllColors() {
    try {
        // Extraire les couleurs uniques depuis les produits
        const colors = new Set();
        appState.products.forEach(product => {
            if (product.type_cadre) {
                // Extraire la couleur du type de cadre (ex: "ENTRE-2-VERRES BLANC" -> "BLANC")
                const colorMatch = product.type_cadre.match(/\b(BLANC|NOIR|ROUGE|BLEU|VERT|JAUNE|ORANGE|VIOLET|ROSE|GRIS|MARRON|BEIGE)\b/i);
                if (colorMatch) {
                    colors.add(colorMatch[1].toUpperCase());
                }
            }
        });
        
        appState.colors = Array.from(colors).sort();
        populateColorSelect();
    } catch (error) {
        console.error('Erreur lors du chargement des couleurs:', error);
    }
}

// Chargement des couleurs pour une catégorie spécifique
function loadColorsForCategory(category) {
    try {
        // Filtrer les produits de la catégorie
        const categoryProducts = appState.products.filter(
            product => product.product_category === category
        );
        
        // Extraire les couleurs uniques
        const colors = new Set();
        categoryProducts.forEach(product => {
            if (product.type_cadre) {
                const colorMatch = product.type_cadre.match(/\b(BLANC|NOIR|ROUGE|BLEU|VERT|JAUNE|ORANGE|VIOLET|ROSE|GRIS|MARRON|BEIGE)\b/i);
                if (colorMatch) {
                    colors.add(colorMatch[1].toUpperCase());
                }
            }
        });
        
        // Mettre à jour le sélecteur de couleurs
        populateColorSelectForCategory(Array.from(colors).sort());
    } catch (error) {
        console.error('Erreur lors du chargement des couleurs pour la catégorie:', error);
    }
}

// Remplissage du sélecteur de couleurs pour une catégorie
function populateColorSelectForCategory(colors) {
    elements.colorSelect.innerHTML = '<option value="">Toutes les couleurs</option>';
    
    colors.forEach(color => {
        const option = document.createElement('option');
        option.value = color;
        option.textContent = color;
        elements.colorSelect.appendChild(option);
    });
}

// Remplissage du sélecteur de couleurs (toutes les couleurs)
function populateColorSelect() {
    elements.colorSelect.innerHTML = '<option value="">Toutes les couleurs</option>';
    
    if (appState.colors && appState.colors.length > 0) {
        appState.colors.forEach(color => {
            const option = document.createElement('option');
            option.value = color;
            option.textContent = color;
            elements.colorSelect.appendChild(option);
        });
    }
}

// Remplissage du sélecteur de catégories
function populateCategorySelect() {
    elements.categorySelect.innerHTML = '<option value="">Choisissez une catégorie...</option>';
    
    appState.categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        
        // Nettoyer le nom de la catégorie pour l'affichage (enlever BBD/BDD)
        let displayName = category.replace(/^(BBD|BDD)\s+/i, '').trim();
        option.textContent = displayName;
        
        elements.categorySelect.appendChild(option);
    });
}

// Remplissage du sélecteur de tailles
function populateSizeSelect() {
    elements.sizeSelect.innerHTML = '<option value="">Toutes les tailles</option>';
    
    appState.sizes.forEach(size => {
        const option = document.createElement('option');
        option.value = size;
        option.textContent = size;
        elements.sizeSelect.appendChild(option);
    });
}

// Gestion du changement de catégorie
function handleCategoryChange() {
    const selectedCategory = elements.categorySelect.value;
    
    // Réinitialiser les filtres quand on change de catégorie
    elements.colorSelect.value = '';
    elements.sizeSelect.value = '';
    
    // Réinitialiser les filtres binaires
    resetBinaryFilters();
    
    // Réinitialiser la pagination
    appState.currentPage = 1;
    
    if (selectedCategory) {
        // Vérifier et afficher les filtres binaires IMMÉDIATEMENT
        checkAndShowBinaryFilters(selectedCategory);
        
        // Charger les couleurs disponibles pour cette catégorie
        loadColorsForCategory(selectedCategory);
        
        // Filtrer les produits de la catégorie
        appState.filteredProducts = appState.products.filter(
            product => product.product_category === selectedCategory
        );
        
        // Afficher les produits avec pagination
        displayProductsWithPagination();
    } else {
        elements.productsGrid.innerHTML = '';
        elements.colorSelect.innerHTML = '<option value="">Toutes les couleurs</option>';
        elements.sizeSelect.innerHTML = '<option value="">Toutes les tailles</option>';
        elements.loadMoreContainer.style.display = 'none';
        appState.filteredProducts = [];
        
        // Masquer les filtres binaires
        hideBinaryFilters();
    }
}

// Chargement des tailles pour une catégorie spécifique
async function loadSizesForCategory(category) {
    try {
        const response = await fetch(`${API_BASE_URL}/sizes/${category}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            populateSizeSelectForCategory(data.sizes);
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des tailles pour la catégorie:', error);
        // En cas d'erreur, utiliser toutes les tailles
        populateSizeSelectForCategory(appState.sizes);
    }
}

// Chargement des tailles pour une catégorie spécifique et une couleur
async function loadSizesForColor(category, color) {
    try {
        const response = await fetch(`${API_BASE_URL}/sizes/${category}/${color}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            populateSizeSelectForCategory(data.sizes);
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des tailles pour la catégorie et la couleur:', error);
        // En cas d'erreur, utiliser toutes les tailles de la catégorie
        loadSizesForCategory(category);
    }
}

// Gestion des filtres binaires
function checkAndShowBinaryFilters(category) {
    const binaryFiltersContainer = document.getElementById('binaryFilters');
    if (!binaryFiltersContainer) return;
    
    // Vérifier si la catégorie a des produits avec des caractéristiques binaires
    const categoryProducts = appState.products.filter(
        product => product.product_category === category
    );
    
    // Analyser les valeurs binaires pour chaque caractéristique
    let vitreValues = new Set();
    let rehausseValues = new Set();
    let possibiliteChevaletValues = new Set();
    
    categoryProducts.forEach(product => {
        if (product.vitre_binaire !== undefined) vitreValues.add(product.vitre_binaire);
        if (product.rehausse_binaire !== undefined) rehausseValues.add(product.rehausse_binaire);
        if (product.possibilite_chevalet_binaire !== undefined) possibiliteChevaletValues.add(product.possibilite_chevalet_binaire);
    });
    
    // Un filtre ne s'affiche que s'il y a des valeurs mixtes (0 ET 1)
    const hasVitreMixed = vitreValues.size > 1; // Plus d'une valeur = mixte
    const hasRehausseMixed = rehausseValues.size > 1;
    
    // Vérifier si la colonne "Chevalet" est présente
    // Elle est présente si au moins un produit a cette valeur définie
    const hasPossibiliteChevaletColumn = possibiliteChevaletValues.size > 0;
    const hasPossibiliteChevaletMixed = hasPossibiliteChevaletColumn && possibiliteChevaletValues.size > 1;
    
    // Afficher seulement les filtres avec des valeurs mixtes
    const vitreFilter = document.getElementById('vitreFilter');
    const rehausseFilter = document.getElementById('rehausseFilter');
    const possibiliteChevaletFilterContainer = document.getElementById('possibiliteChevaletFilterContainer');
    
    if (vitreFilter) {
        vitreFilter.style.display = hasVitreMixed ? 'block' : 'none';
        vitreFilter.parentElement.style.display = hasVitreMixed ? 'flex' : 'none';
    }
    
    if (rehausseFilter) {
        rehausseFilter.style.display = hasRehausseMixed ? 'block' : 'none';
        rehausseFilter.parentElement.style.display = hasRehausseMixed ? 'flex' : 'none';
    }
    
    // Afficher le filtre "Chevalet" seulement si la colonne est présente
    if (possibiliteChevaletFilterContainer) {
        possibiliteChevaletFilterContainer.style.display = hasPossibiliteChevaletColumn ? 'flex' : 'none';
    }
    
    // Afficher le conteneur seulement s'il y a au moins un filtre à afficher
    const hasAnyFilter = hasVitreMixed || hasRehausseMixed || hasPossibiliteChevaletColumn;
    binaryFiltersContainer.style.display = hasAnyFilter ? 'block' : 'none';
}

function hideBinaryFilters() {
    const binaryFiltersContainer = document.getElementById('binaryFilters');
    const possibiliteChevaletFilterContainer = document.getElementById('possibiliteChevaletFilterContainer');
    
    if (binaryFiltersContainer) {
        binaryFiltersContainer.style.display = 'none';
    }
    
    if (possibiliteChevaletFilterContainer) {
        possibiliteChevaletFilterContainer.style.display = 'none';
    }
}

function resetBinaryFilters() {
    const vitreFilter = document.getElementById('vitreFilter');
    const rehausseFilter = document.getElementById('rehausseFilter');
    const possibiliteChevaletFilter = document.getElementById('possibiliteChevaletFilter');
    
    if (vitreFilter) vitreFilter.checked = false;
    if (rehausseFilter) rehausseFilter.checked = false;
    if (possibiliteChevaletFilter) possibiliteChevaletFilter.checked = false;
}

function handleBinaryFiltersChange() {
    // Réinitialiser la pagination
    appState.currentPage = 1;
    
    // Appliquer tous les filtres
    applyAllFilters();
}

function applyAllFilters() {
    const selectedCategory = elements.categorySelect.value;
    const selectedColor = elements.colorSelect.value;
    const selectedSize = elements.sizeSelect.value;
    
    // Récupérer les valeurs des filtres binaires
    const vitreFilter = document.getElementById('vitreFilter');
    const rehausseFilter = document.getElementById('rehausseFilter');
    const possibiliteChevaletFilter = document.getElementById('possibiliteChevaletFilter');
    
    const vitreChecked = vitreFilter ? vitreFilter.checked : false;
    const rehausseChecked = rehausseFilter ? rehausseFilter.checked : false;
    const possibiliteChevaletChecked = possibiliteChevaletFilter ? possibiliteChevaletFilter.checked : false;
    
    // Filtrer les produits par catégorie
    let filteredProducts = appState.products.filter(
        product => product.product_category === selectedCategory
    );
    
    // Filtrer par couleur si une couleur est sélectionnée
    if (selectedColor) {
        filteredProducts = filteredProducts.filter(product => {
            if (product.type_cadre) {
                const colorMatch = product.type_cadre.match(/\b(BLANC|NOIR|ROUGE|BLEU|VERT|JAUNE|ORANGE|VIOLET|ROSE|GRIS|MARRON|BEIGE)\b/i);
                return colorMatch && colorMatch[1].toUpperCase() === selectedColor;
            }
            return false;
        });
    }
    
    // Filtrer par taille si une taille est sélectionnée
    if (selectedSize) {
        filteredProducts = filteredProducts.filter(
            product => product.frame_size === selectedSize
        );
    }
    
    // Appliquer les filtres binaires en utilisant les valeurs 1/0
    if (vitreChecked || rehausseChecked || possibiliteChevaletChecked) {
        filteredProducts = filteredProducts.filter(product => {
            let matches = true;
            
            if (vitreChecked) {
                matches = matches && product.vitre_binaire === 1;
            }
            if (rehausseChecked) {
                matches = matches && product.rehausse_binaire === 1;
            }
            if (possibiliteChevaletChecked) {
                matches = matches && product.possibilite_chevalet_binaire === 1;
            }
            
            return matches;
        });
    }
    
    // Mettre à jour les produits filtrés
    appState.filteredProducts = filteredProducts;
    
    // Afficher les produits avec pagination
    displayProductsWithPagination();
}

// Remplissage du sélecteur de tailles pour une catégorie
function populateSizeSelectForCategory(sizes) {
    elements.sizeSelect.innerHTML = '<option value="">Toutes les tailles</option>';
    
    sizes.forEach(size => {
        const option = document.createElement('option');
        option.value = size;
        option.textContent = size;
        elements.sizeSelect.appendChild(option);
    });
}

// Gestion du changement de taille
function handleSizeChange() {
    const selectedCategory = elements.categorySelect.value;
    
    if (!selectedCategory) {
        return; // Pas de catégorie sélectionnée
    }
    
    // Réinitialiser la pagination
    appState.currentPage = 1;
    
    // Appliquer tous les filtres
    applyAllFilters();
}

// Gestion du changement de couleur
function handleColorChange() {
    const selectedCategory = elements.categorySelect.value;
    const selectedColor = elements.colorSelect.value;
    
    if (!selectedCategory) {
        return; // Pas de catégorie sélectionnée
    }
    
    // Réinitialiser le filtre de taille
    elements.sizeSelect.value = '';
    
    // Réinitialiser la pagination
    appState.currentPage = 1;
    
    // Charger les tailles selon la couleur sélectionnée
    if (selectedColor) {
        loadSizesForColor(selectedCategory, selectedColor);
    } else {
        loadSizesForCategory(selectedCategory);
    }
    
    // Appliquer tous les filtres
    applyAllFilters();
}

// Affichage des produits avec pagination
function displayProductsWithPagination() {
    const startIndex = 0;
    const endIndex = appState.currentPage * appState.productsPerPage;
    const productsToShow = appState.filteredProducts.slice(startIndex, endIndex);
    
    // Vider la grille si c'est la première page
    if (appState.currentPage === 1) {
        elements.productsGrid.innerHTML = '';
    }
    
    // Ajouter les nouveaux produits
    productsToShow.forEach(product => {
        const productCard = createProductCard(product);
        elements.productsGrid.appendChild(productCard);
    });
    
    // Gérer l'affichage du bouton "Voir plus"
    const hasMoreProducts = endIndex < appState.filteredProducts.length;
    elements.loadMoreContainer.style.display = hasMoreProducts ? 'block' : 'none';
    
    // Désactiver le bouton s'il n'y a plus de produits
    elements.loadMoreBtn.disabled = !hasMoreProducts;
    
    // Mettre à jour le texte du bouton
    if (hasMoreProducts) {
        const remainingProducts = appState.filteredProducts.length - endIndex;
        const productsToLoad = Math.min(remainingProducts, appState.productsPerPage);
        elements.loadMoreBtn.innerHTML = `<i class="fas fa-plus"></i> Voir ${productsToLoad} produit${productsToLoad > 1 ? 's' : ''} de plus`;
    }
}

// Charger plus de produits
function loadMoreProducts() {
    appState.currentPage++;
    displayProductsWithPagination();
}

// Affichage des produits (fonction legacy - à supprimer plus tard)
function displayProducts(products) {
    elements.productsGrid.innerHTML = '';
    
    products.forEach(product => {
        const productCard = createProductCard(product);
        elements.productsGrid.appendChild(productCard);
    });
}

// Création d'une carte produit
function createProductCard(product) {
    const card = document.createElement('div');
    card.className = 'product-card';
    // Utiliser le code_produit unique au lieu de la combinaison category + nom
    card.dataset.productId = product.code_produit || `${product.product_category}-${product.nom_commercial}`;
    
    // Rechercher le produit uniquement par code_produit pour éviter les conflits entre variantes (avec/sans DC)
    const existingProduct = appState.selectedProducts.find(p => {
        if (product.code_produit && p.code_produit) {
            // Si les deux ont un code_produit, comparer uniquement par code_produit
            return p.code_produit === product.code_produit;
        }
        // Fallback uniquement si aucun des deux n'a de code_produit
        return !product.code_produit && !p.code_produit &&
               p.product_category === product.product_category && 
               p.nom_commercial === product.nom_commercial;
    });
    
    const isSelected = !!existingProduct;
    const currentQuantity = existingProduct ? existingProduct.quantity : 1;
    
    if (isSelected) {
        card.classList.add('selected');
    }
    
    // Analyser les caractéristiques du produit basées sur les valeurs binaires
    const hasVitre = product.vitre_binaire === 1;
    const hasRehausse = product.rehausse_binaire === 1;
    const hasPossibiliteChevalet = product.possibilite_chevalet_binaire === 1;
    
    // Fonction pour extraire la couleur du type_cadre (même logique que le filtre Coloris)
    const extractColor = (typeCadre) => {
        if (typeCadre) {
            const colorMatch = typeCadre.match(/\b(BLANC|NOIR|ROUGE|BLEU|VERT|JAUNE|ORANGE|VIOLET|ROSE|GRIS|MARRON|BEIGE)\b/i);
            return colorMatch ? colorMatch[1].toUpperCase() : typeCadre;
        }
        return 'N/A';
    };
    
    const productColor = extractColor(product.type_cadre);
    
    card.innerHTML = `
        <h3>${product.nom_commercial}</h3>
        <div class="product-info">
            <p><strong>Nom commercial:</strong> ${product.nom_commercial}</p>
            <p><strong>ID produit:</strong> ${product.code_produit || 'N/A'}</p>
            <p><strong>Couleur:</strong> ${productColor}</p>
        </div>
        
        <!-- Caractéristiques du produit -->
        <div class="product-characteristics">
            <span class="char-badge ${hasVitre ? 'vitre' : 'sans-vitre'}">
                ${hasVitre ? 'Vitre' : 'Sans vitre'}
            </span>
            <span class="char-badge ${hasRehausse ? 'rehausse' : 'sans-rehausse'}">
                ${hasRehausse ? 'Rehausse' : 'Sans rehausse'}
            </span>
            <span class="char-badge ${hasPossibiliteChevalet ? 'chevalet' : 'sans-chevalet'}">
                ${hasPossibiliteChevalet ? 'Chevalet' : 'Sans chevalet'}
            </span>
        </div>
        
        <div class="product-actions">
            <input type="number" class="quantity-input" value="${currentQuantity}" min="1" max="99">
            <button class="add-to-cart-btn">
                ${isSelected ? 'Mettre à jour' : 'Ajouter au panier'}
            </button>
        </div>
    `;
    
    // Gestion des événements
    const addButton = card.querySelector('.add-to-cart-btn');
    const quantityInput = card.querySelector('.quantity-input');
    
    addButton.addEventListener('click', () => {
        const quantity = parseInt(quantityInput.value);
        if (quantity > 0) {
            addToCart(product, quantity);
        }
    });
    
    // Mise à jour en temps réel de la quantité
    quantityInput.addEventListener('input', () => {
        const quantity = parseInt(quantityInput.value);
        if (quantity > 0 && isSelected) {
            updateProductQuantity(product, quantity);
        }
    });
    
    // Mise à jour en temps réel de la quantité (pour tous les produits, même non sélectionnés)
    quantityInput.addEventListener('change', () => {
        const quantity = parseInt(quantityInput.value);
        if (quantity > 0) {
            // Rechercher le produit uniquement par code_produit pour éviter les conflits entre variantes (avec/sans DC)
            const existingProduct = appState.selectedProducts.find(p => {
                if (product.code_produit && p.code_produit) {
                    return p.code_produit === product.code_produit;
                }
                return !product.code_produit && !p.code_produit &&
                       p.product_category === product.product_category && 
                       p.nom_commercial === product.nom_commercial;
            });
            if (existingProduct) {
                updateProductQuantity(product, quantity);
            }
        }
    });
    
    return card;
}

// Ajout au panier
function addToCart(product, quantity) {
    // Rechercher le produit uniquement par code_produit pour éviter les conflits entre variantes (avec/sans DC)
    const existingProduct = appState.selectedProducts.find(p => {
        if (product.code_produit && p.code_produit) {
            // Si les deux ont un code_produit, comparer uniquement par code_produit
            return p.code_produit === product.code_produit;
        }
        // Fallback uniquement si aucun des deux n'a de code_produit
        return !product.code_produit && !p.code_produit &&
               p.product_category === product.product_category && 
               p.nom_commercial === product.nom_commercial;
    });
    
    if (existingProduct) {
        existingProduct.quantity = quantity; // Remplace la quantité au lieu d'ajouter
    } else {
        appState.selectedProducts.push({
            ...product,
            quantity: quantity
        });
    }
    
    updateSelectedProductsDisplay();
    updateProductCards();
    updateTotals();
    updateNavigationButtons();
}

// Mise à jour de la quantité d'un produit
function updateProductQuantity(product, quantity) {
    // Rechercher le produit uniquement par code_produit pour éviter les conflits entre variantes (avec/sans DC)
    const existingProduct = appState.selectedProducts.find(p => {
        if (product.code_produit && p.code_produit) {
            // Si les deux ont un code_produit, comparer uniquement par code_produit
            return p.code_produit === product.code_produit;
        }
        // Fallback uniquement si aucun des deux n'a de code_produit
        return !product.code_produit && !p.code_produit &&
               p.product_category === product.product_category && 
               p.nom_commercial === product.nom_commercial;
    });
    
    if (existingProduct) {
        existingProduct.quantity = quantity;
        updateSelectedProductsDisplay(); // Mettre à jour l'affichage des produits sélectionnés
        updateProductCards(); // Mettre à jour les cartes produits
        updateTotals();
        updateNavigationButtons();
    }
}

// Suppression du panier
function removeFromCart(productId) {
    appState.selectedProducts = appState.selectedProducts.filter(
        p => p.code_produit != productId && 
             `${p.product_category}-${p.nom_commercial}` !== productId
    );
    
    updateSelectedProductsDisplay();
    updateProductCards();
    updateTotals();
    updateNavigationButtons();
}

// Mise à jour de l'affichage des produits sélectionnés
function updateSelectedProductsDisplay() {
    elements.selectedProductsList.innerHTML = '';
    
    appState.selectedProducts.forEach(product => {
        const item = document.createElement('div');
        item.className = 'selected-item';
        // Utiliser le code_produit unique s'il existe, sinon fallback sur l'ancienne méthode
        const productId = product.code_produit || `${product.product_category}-${product.nom_commercial}`;
        item.dataset.productId = productId;
        
        const price = parseFloat(product.tarif_vente_2025) || 0;
        const totalCost = price * product.quantity;
        
        item.innerHTML = `
            <div class="selected-item-info">
                <div class="selected-item-name">${product.nom_commercial}</div>
                <div class="selected-item-details">
                    Valeur unitaire: ${formatPrice(price)} | Total: ${formatPrice(totalCost)}
                </div>
            </div>
            <div class="selected-item-actions">
                <div class="quantity-control">
                    <label for="quantity-${productId}">Qté:</label>
                    <input type="number" 
                           id="quantity-${productId}" 
                           class="quantity-input-selected" 
                           value="${product.quantity}" 
                           min="1" 
                           max="99"
                           data-product-category="${product.product_category}"
                           data-product-name="${product.nom_commercial}"
                           data-product-code="${product.code_produit || ''}">
                </div>
                <button class="remove-btn" onclick="removeFromCart('${productId}')">
                    Supprimer
                </button>
            </div>
        `;
        
        elements.selectedProductsList.appendChild(item);
        
        // Ajouter l'événement pour la modification de quantité
        const quantityInput = item.querySelector('.quantity-input-selected');
        quantityInput.addEventListener('change', (e) => {
            const newQuantity = parseInt(e.target.value);
            if (newQuantity > 0) {
                updateProductQuantity(product, newQuantity);
            } else {
                // Remettre la valeur précédente si la quantité n'est pas valide
                e.target.value = product.quantity;
            }
        });
        
        // Ajouter l'événement pour la modification en temps réel
        quantityInput.addEventListener('input', (e) => {
            const newQuantity = parseInt(e.target.value);
            if (newQuantity > 0) {
                updateProductQuantity(product, newQuantity);
            }
        });
    });
}

// Mise à jour des cartes produits
function updateProductCards() {
    const cards = elements.productsGrid.querySelectorAll('.product-card');
    
    cards.forEach(card => {
        const productId = card.dataset.productId;
        // Rechercher par code_produit en priorité, puis par productId
        const existingProduct = appState.selectedProducts.find(p => {
            if (p.code_produit) {
                return p.code_produit == productId;
            }
            return `${p.product_category}-${p.nom_commercial}` === productId;
        });
        
        const isSelected = !!existingProduct;
        const addButton = card.querySelector('.add-to-cart-btn');
        const quantityInput = card.querySelector('.quantity-input');
        
        if (isSelected) {
            card.classList.add('selected');
            addButton.textContent = 'Mettre à jour';
            addButton.disabled = false;
            
            // Mettre à jour la quantité affichée si elle a changé
            if (quantityInput.value != existingProduct.quantity) {
                quantityInput.value = existingProduct.quantity;
            }
        } else {
            card.classList.remove('selected');
            addButton.textContent = 'Ajouter au panier';
            addButton.disabled = false;
            
            // Remettre la quantité à 1 si le produit n'est plus sélectionné
            quantityInput.value = 1;
        }
    });
}

// Mise à jour des totaux (désactivé pour devis)
function updateTotals() {
    elements.totalHT.textContent = "Devis à établir";
    elements.totalTTC.textContent = "Devis à établir";
    updateCostGauge();
}

// Mise à jour de la jauge de coût d'achat HT 2025
function updateCostGauge() {
    console.log('updateCostGauge() appelée');
    console.log('Produits sélectionnés:', appState.selectedProducts);
    
    const MIN_COST = 1000; // Minimum de 1000€
    let totalCost = 0;
    let productCount = 0;
    
    // Calculer le coût total des produits sélectionnés
    appState.selectedProducts.forEach(product => {
        const price = parseFloat(product.tarif_vente_2025) || 0;
        const quantity = product.quantity || 1;
        totalCost += price * quantity;
        productCount += quantity;
        console.log(`Produit: ${product.nom_commercial}, Prix: ${price}, Qté: ${quantity}, Total: ${price * quantity}`);
    });
    
    // Calculer le pourcentage (100% = 1000€ minimum)
    const percentage = Math.min((totalCost / MIN_COST) * 100, 100);
    
    console.log('Calculs jauge:', { totalCost, productCount, percentage, MIN_COST });
    
    // Vérifier que les éléments DOM existent
    if (!elements.currentCost || !elements.selectedCount || !elements.totalCost || !elements.gaugePercentage || !elements.gaugeFill) {
        console.error('Éléments DOM de la jauge manquants:', {
            currentCost: !!elements.currentCost,
            selectedCount: !!elements.selectedCount,
            totalCost: !!elements.totalCost,
            gaugePercentage: !!elements.gaugePercentage,
            gaugeFill: !!elements.gaugeFill
        });
        return;
    }
    
    // Mettre à jour l'affichage
    elements.currentCost.textContent = Math.round(totalCost);
    elements.selectedCount.textContent = productCount;
    elements.totalCost.textContent = `${Math.round(totalCost)}€`;
    elements.gaugePercentage.textContent = `${Math.round(percentage)}%`;
    
    // Mettre à jour la jauge
    elements.gaugeFill.style.width = `${percentage}%`;
    console.log('Largeur de la jauge mise à jour:', `${percentage}%`);
    
    // Gérer l'état critique (proche de 1000€ minimum)
    if (percentage >= 90 && percentage < 100) {
        elements.gaugeFill.classList.add('critical');
    } else {
        elements.gaugeFill.classList.remove('critical');
    }
    
    // Animation pour les changements de valeur
    animateValueChange('selectedCount', productCount);
    animateValueChange('totalCost', `${Math.round(totalCost)}€`);
    
    // Mise à jour des boutons de navigation
    updateNavigationButtons();
}

// Animation pour les changements de valeur
function animateValueChange(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('updated');
        element.textContent = newValue;
        
        setTimeout(() => {
            element.classList.remove('updated');
        }, 600);
    }
}

// Mise à jour des boutons de navigation
function updateNavigationButtons() {
    // Calculer la valeur totale du panier
    let totalCost = 0;
    appState.selectedProducts.forEach(product => {
        const price = parseFloat(product.tarif_vente_2025) || 0;
        const quantity = product.quantity || 1;
        totalCost += price * quantity;
    });
    
    // Le bouton est activé seulement si on a des produits ET que le panier atteint 1000€ minimum
    const hasProducts = appState.selectedProducts.length > 0;
    const meetsMinimum = totalCost >= 1000;
    
    elements.nextStep1.disabled = !hasProducts || !meetsMinimum;
    
    // Ajouter un message d'aide si le minimum n'est pas atteint
    if (hasProducts && !meetsMinimum) {
        const remaining = Math.ceil(1000 - totalCost);
        elements.nextStep1.title = `Panier minimum non atteint. Il manque ${remaining}€ pour continuer.`;
    } else {
        elements.nextStep1.title = '';
    }
}

// Navigation entre les étapes
function goToStep(step) {
    if (step === 2) {
        // Vérifier qu'on a des produits ET que le panier atteint 1000€ minimum
        if (appState.selectedProducts.length === 0) {
            alert('Veuillez sélectionner au moins un produit avant de continuer.');
            return;
        }
        
        // Calculer la valeur totale du panier
        let totalCost = 0;
        appState.selectedProducts.forEach(product => {
            const price = parseFloat(product.tarif_vente_2025) || 0;
            const quantity = product.quantity || 1;
            totalCost += price * quantity;
        });
        
        if (totalCost < 1000) {
            const remaining = Math.ceil(1000 - totalCost);
            alert(`Panier minimum non atteint. Il manque ${remaining}€ pour continuer. Veuillez ajouter plus de produits.`);
            return;
        }
    }
    
    if (step === 3) {
        // Validation du formulaire de livraison
        if (!elements.deliveryForm.checkValidity()) {
            elements.deliveryForm.reportValidity();
            return;
        }
        
        // Validation spécifique pour l'adresse de facturation si elle n'est pas identique
        const sameBillingAddressCheckbox = document.getElementById('sameBillingAddress');
        if (!sameBillingAddressCheckbox.checked) {
            const billingAddressFields = document.getElementById('billingAddressFields');
            const requiredBillingFields = billingAddressFields.querySelectorAll('[required]');
            let billingValid = true;
            
            requiredBillingFields.forEach(field => {
                if (!field.value.trim()) {
                    billingValid = false;
                    field.focus();
                    field.reportValidity();
                }
            });
            
            if (!billingValid) {
                alert('Veuillez remplir tous les champs obligatoires de l\'adresse de facturation.');
                return;
            }
        }
        
        // Sauvegarde de l'adresse
        const formData = new FormData(elements.deliveryForm);
        appState.deliveryAddress = Object.fromEntries(formData);
        
        // Mise à jour de l'affichage de confirmation
        updateConfirmationDisplay();
    }
    
    // Mise à jour des étapes
    elements.steps.forEach((stepEl, index) => {
        if (index + 1 < step) {
            stepEl.classList.add('completed');
            stepEl.classList.remove('active');
        } else if (index + 1 === step) {
            stepEl.classList.add('active');
            stepEl.classList.remove('completed');
        } else {
            stepEl.classList.remove('active', 'completed');
        }
    });
    
    // Mise à jour du contenu
    elements.stepContents.forEach((content, index) => {
        if (index + 1 === step) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
    
    appState.currentStep = step;
}

// Mise à jour de l'affichage de confirmation
function updateConfirmationDisplay() {
    // Produits commandés
    elements.orderProductsList.innerHTML = '';
    appState.selectedProducts.forEach(product => {
        const price = parseFloat(product.tarif_vente_2025) || 0;
        const totalCost = price * product.quantity;
        
        const item = document.createElement('div');
        item.className = 'order-product-item';
        item.innerHTML = `
            <div>
                <strong>${product.nom_commercial}</strong><br>
                <small>Qté: ${product.quantity} | Valeur unitaire: ${formatPrice(price)} | Total: ${formatPrice(totalCost)}</small>
            </div>
        `;
        elements.orderProductsList.appendChild(item);
    });
    
    // Notes des produits
    const productNotes = elements.productNotes ? elements.productNotes.value.trim() : '';
    if (productNotes) {
        const notesItem = document.createElement('div');
        notesItem.className = 'order-product-item';
        notesItem.style.marginTop = '15px';
        notesItem.style.padding = '15px';
        notesItem.style.backgroundColor = '#f8f9fa';
        notesItem.style.borderRadius = '6px';
        notesItem.style.border = '1px solid #e9ecef';
        notesItem.innerHTML = `
            <div>
                <strong><i class="fas fa-sticky-note"></i> Notes pour des demandes spécifiques:</strong><br>
                <small>${productNotes.replace(/\n/g, '<br>')}</small>
            </div>
        `;
        elements.orderProductsList.appendChild(notesItem);
    }
    
    // Adresse de livraison
    const address = appState.deliveryAddress;
    let addressHtml = `
        <strong>${address.firstName} ${address.lastName}</strong><br>
        ${address.companyName ? `Entreprise: ${address.companyName}<br>` : ''}
        ${address.siren ? `SIREN: ${address.siren}<br>` : ''}
        ${address.siret ? `SIRET: ${address.siret}<br>` : ''}
        ${address.email}<br>
        ${address.phone}<br>
        ${address.address}<br>
        ${address.postalCode} ${address.city}<br>
        ${address.country}
        ${address.notes ? `<br><br><strong>Notes:</strong><br>${address.notes}` : ''}
    `;
    
    // Adresse de facturation si différente
    if (address.sameBillingAddress === 'off') {
        addressHtml += `<br><br><strong>Adresse de facturation:</strong><br>`;
        addressHtml += `<strong>${address.billingFirstName || ''} ${address.billingLastName || ''}</strong><br>`;
        if (address.billingCompanyName) addressHtml += `Entreprise: ${address.billingCompanyName}<br>`;
        if (address.billingSiren) addressHtml += `SIREN: ${address.billingSiren}<br>`;
        if (address.billingSiret) addressHtml += `SIRET: ${address.billingSiret}<br>`;
        if (address.billingAddress) addressHtml += `${address.billingAddress}<br>`;
        if (address.billingPostalCode && address.billingCity) addressHtml += `${address.billingPostalCode} ${address.billingCity}<br>`;
        if (address.billingCountry) addressHtml += `${address.billingCountry}`;
    } else {
        addressHtml += `<br><br><strong>Adresse de facturation:</strong> Identique à l'adresse de livraison`;
    }
    
    elements.orderAddress.innerHTML = addressHtml;
    
    // Pas de totaux pour un devis
    elements.orderTotalHT.textContent = "Devis à établir";
    elements.orderTotalTTC.textContent = "Devis à établir";
}

// Soumission de la commande
async function submitOrder() {
    showLoading(true);
    
    try {
        // Récupérer les notes des produits
        const productNotes = elements.productNotes ? elements.productNotes.value.trim() : '';
        
        const orderData = {
            selected_products: appState.selectedProducts,
            product_notes: productNotes,
            delivery_address: appState.deliveryAddress
        };
        
        const response = await fetch(`${API_BASE_URL}/order`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            elements.orderNumber.textContent = data.order.order_id;
            
            // Gestion de l'intégration Sellsy
            if (data.sellsy_client_id && data.sellsy_opportunity_id) {
                // Succès de l'intégration Sellsy
                elements.sellsyInfo.style.display = 'block';
                elements.sellsyError.style.display = 'none';
                elements.sellsyClientId.textContent = data.sellsy_client_id;
                elements.sellsyOpportunityId.textContent = data.sellsy_opportunity_id;
            } else if (data.sellsy_error) {
                // Erreur d'intégration Sellsy
                elements.sellsyInfo.style.display = 'none';
                elements.sellsyError.style.display = 'block';
                elements.sellsyErrorMessage.textContent = data.sellsy_error;
            } else {
                // Pas d'intégration Sellsy
                elements.sellsyInfo.style.display = 'none';
                elements.sellsyError.style.display = 'none';
            }
            
            showSuccessModal();
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        console.error('Erreur lors de la soumission de la commande:', error);
        alert('Erreur lors de la soumission de la commande. Veuillez réessayer.');
    } finally {
        showLoading(false);
    }
}

// Affichage du modal de succès
function showSuccessModal() {
    elements.successModal.classList.add('active');
}

// Réinitialisation de l'application
function resetApp() {
    elements.successModal.classList.remove('active');
    
    // Réinitialisation de l'état
    appState.selectedProducts = [];
    appState.deliveryAddress = null;
    appState.currentStep = 1;
    appState.currentPage = 1;
    appState.filteredProducts = [];
    
    // Réinitialisation de l'affichage
    elements.categorySelect.value = '';
    elements.sizeSelect.innerHTML = '<option value="">Toutes les tailles</option>';
    elements.productsGrid.innerHTML = '';
    elements.loadMoreContainer.style.display = 'none';
    elements.selectedProductsList.innerHTML = '';
    elements.deliveryForm.reset();
    
    // Réinitialisation des filtres binaires
    resetBinaryFilters();
    hideBinaryFilters();
    
    // Réinitialisation des notes des produits
    if (elements.productNotes) {
        elements.productNotes.value = '';
    }
    
    // Masquer les informations Sellsy
    elements.sellsyInfo.style.display = 'none';
    elements.sellsyError.style.display = 'none';
    
    // Retour à l'étape 1
    goToStep(1);
    
    // Mise à jour des totaux et de la jauge
    updateTotals();
    updateNavigationButtons();
}

// Affichage/masquage du loading
function showLoading(show) {
    if (show) {
        elements.loadingOverlay.classList.add('active');
    } else {
        elements.loadingOverlay.classList.remove('active');
    }
}

// Formatage des prix
function formatPrice(price) {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR'
    }).format(price || 0);
}


// Gestion des erreurs globales
window.addEventListener('error', function(e) {
    console.error('Erreur JavaScript:', e.error);
    showLoading(false);
});

// Gestion des erreurs de réseau
window.addEventListener('unhandledrejection', function(e) {
    console.error('Erreur de promesse non gérée:', e.reason);
    showLoading(false);
    alert('Une erreur est survenue. Veuillez rafraîchir la page.');
}); 