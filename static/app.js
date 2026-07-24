// Standalone app.js for Workflow Planner Tasks

function toggleViewTab(view) {
    var taskListContainer = document.getElementById('task-list');
    var productCardsContainer = document.getElementById('product-cards-container');
    var filterBar = document.getElementById('filter-bar');
    var allBtn = document.getElementById('view-all-tasks');
    var prodBtn = document.getElementById('view-products');

    if (view === 'all') {
        allBtn.classList.add('bg-white', 'text-black');
        allBtn.classList.remove('bg-gray-700', 'text-gray-300');
        prodBtn.classList.remove('bg-white', 'text-black');
        prodBtn.classList.add('bg-gray-700', 'text-gray-300');
        
        if (taskListContainer) taskListContainer.style.display = 'block';
        if (productCardsContainer) productCardsContainer.style.display = 'none';
        if (filterBar) filterBar.style.display = 'flex';
        showAllTasks();

    } else { // view === 'products'
        prodBtn.classList.add('bg-white', 'text-black');
        prodBtn.classList.remove('bg-gray-700', 'text-gray-300');
        allBtn.classList.remove('bg-white', 'text-black');
        allBtn.classList.add('bg-gray-700', 'text-gray-300');
        
        if (taskListContainer) taskListContainer.style.display = 'none';
        if (filterBar) filterBar.style.display = 'none';
        
        if (productCardsContainer) {
            productCardsContainer.style.display = 'grid';
            productCardsContainer.innerHTML = '<div class="text-gray-400 col-span-full text-center py-8">Memuat...</div>';
            fetchProductsAndRender(productCardsContainer);
        }
    }
}

function fetchProductsAndRender(container) {
    fetch('/api/products-with-tasks')
        .then(r => r.json())
        .then(products => {
            container.innerHTML = '';
            if (products.length === 0) {
                container.innerHTML = '<div class="text-gray-400 col-span-full text-center py-8">Belum ada produk dengan task</div>';
                return;
            }
            products.forEach(p => {
                var img = p.image_path 
                    ? '<img src="/' + p.image_path + '" class="w-full h-full object-cover">' 
                    : '<div class="w-full h-full flex items-center justify-center text-gray-500"><i class="fas fa-image"></i></div>';
                var card = '<div class="bg-gray-800 rounded-2xl p-3 border border-gray-700 cursor-pointer hover:border-yellow-500 transition-all" onclick="filterTasksByProduct(' + p.id + ')">';
                card += '<div class="w-full aspect-square rounded-lg bg-gray-700 mb-3 overflow-hidden">' + img + '</div>';
                card += '<p class="text-white font-bold text-sm truncate">' + p.model_name + '</p>';
                card += '<p class="text-xs text-gray-400 uppercase">' + (p.status || 'DRAFT') + '</p></div>';
                container.innerHTML += card;
            });
        })
        .catch(err => {
            container.innerHTML = '<div class="text-red-400 col-span-full text-center py-8">Gagal memuat produk</div>';
            console.error(err);
        });
}

function showAllTasks() {
    var cards = document.querySelectorAll('.task-card');
    cards.forEach(function(card) { card.style.display = 'block'; });
}

function filterTasksByProduct(productId) {
    var cards = document.querySelectorAll('.task-card');
    var count = 0;
    cards.forEach(function(card) {
        var pid = card.getAttribute('data-product-id');
        if (pid == productId) {
            card.style.display = 'block';
            count++;
        } else {
            card.style.display = 'none';
        }
    });
    console.log('Filtered tasks for product ' + productId + ': ' + count + ' found');
}
