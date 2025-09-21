/**
 * SaveMyLinks - Enhanced Search and UI Functionality
 * This file contains advanced search, filtering, and UI enhancement features
 */

// Global state management
const AppState = {
    currentPage: 1,
    currentSearch: '',
    currentCategory: '',
    sortBy: 'created_at',
    sortOrder: 'desc',
    viewMode: 'grid', // 'grid' or 'list'
    selectedResources: new Set(),
    isLoading: false
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Load saved view mode from localStorage or default to grid
    const savedViewMode = localStorage.getItem('viewMode') || 'grid';
    setViewMode(savedViewMode);
    
    loadCategories();
    loadResources();
    setupEventListeners();
    setupKeyboardShortcuts();
    setupThemeToggle();
}

/**
 * Setup event listeners for enhanced functionality
 */
function setupEventListeners() {
    // Search input with debouncing
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchResources();
            }, 300); // 300ms debounce
        });
        
        // Enter key support
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                clearTimeout(searchTimeout);
                searchResources();
            }
        });
    }

    // Advanced search toggle
    const advancedSearchToggle = document.getElementById('advancedSearchToggle');
    if (advancedSearchToggle) {
        advancedSearchToggle.addEventListener('click', toggleAdvancedSearch);
    }

    // Sort controls
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', handleSortChange);
    }

    // View mode toggle
    const viewModeButtons = document.querySelectorAll('.view-mode-btn');
    viewModeButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const mode = e.target.dataset.mode;
            setViewMode(mode);
        });
    });

    // Bulk actions
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', handleSelectAll);
    }

    const bulkDeleteBtn = document.getElementById('bulkDelete');
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', handleBulkDelete);
    }
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            clearSearch();
        }
        
        // Arrow keys for pagination
        if (e.key === 'ArrowLeft' && e.ctrlKey) {
            e.preventDefault();
            navigatePage('prev');
        }
        if (e.key === 'ArrowRight' && e.ctrlKey) {
            e.preventDefault();
            navigatePage('next');
        }
    });
}

/**
 * Setup theme toggle functionality
 */
function setupThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        setTheme(savedTheme);
        
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }
}

/**
 * Set application theme
 */
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');
        if (icon) {
            icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        }
    }
}

/**
 * Enhanced search with multiple filters
 */
function searchResources() {
    AppState.currentSearch = document.getElementById('searchInput').value;
    AppState.currentPage = 1;
    loadResources();
}

/**
 * Clear search and filters
 */
function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.getElementById('categoryFilter').value = '';
    AppState.currentSearch = '';
    AppState.currentCategory = '';
    AppState.currentPage = 1;
    loadResources();
}

/**
 * Toggle advanced search panel
 */
function toggleAdvancedSearch() {
    const panel = document.getElementById('advancedSearchPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
}

/**
 * Handle sort change
 */
function handleSortChange() {
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        const [sortBy, sortOrder] = sortSelect.value.split('_');
        AppState.sortBy = sortBy;
        AppState.sortOrder = sortOrder;
        AppState.currentPage = 1;
        loadResources();
    }
}

/**
 * Set view mode (grid or list)
 */
function setViewMode(mode) {
    AppState.viewMode = mode;
    localStorage.setItem('viewMode', mode);
    
    // Update UI
    const resourcesList = document.getElementById('resourcesList');
    if (resourcesList) {
        resourcesList.className = `resources-${mode}`;
    }
    
    // Update button states
    document.querySelectorAll('.view-mode-btn').forEach(btn => {
        btn.classList.toggle('is-active', btn.dataset.mode === mode);
    });
    
    // Re-render resources with new view mode
    loadResources();
}

/**
 * Handle select all checkbox
 */
function handleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const resourceCheckboxes = document.querySelectorAll('.resource-checkbox');
    
    if (selectAllCheckbox.checked) {
        resourceCheckboxes.forEach(checkbox => {
            checkbox.checked = true;
            AppState.selectedResources.add(checkbox.value);
        });
    } else {
        resourceCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        AppState.selectedResources.clear();
    }
    
    updateBulkActionsUI();
}

/**
 * Handle bulk delete
 */
async function handleBulkDelete() {
    if (AppState.selectedResources.size === 0) return;
    
    const count = AppState.selectedResources.size;
    if (!confirm(`Are you sure you want to delete ${count} resource${count > 1 ? 's' : ''}?`)) {
        return;
    }
    
    try {
        const deletePromises = Array.from(AppState.selectedResources).map(id => 
            fetch(`/api/resources/${id}`, { method: 'DELETE' })
        );
        
        await Promise.all(deletePromises);
        
        showNotification(`Successfully deleted ${count} resource${count > 1 ? 's' : ''}`, 'is-success');
        AppState.selectedResources.clear();
        loadResources();
    } catch (error) {
        console.error('Error deleting resources:', error);
        showNotification('Error deleting resources', 'is-danger');
    }
}

/**
 * Update bulk actions UI
 */
function updateBulkActionsUI() {
    const bulkActions = document.getElementById('bulkActions');
    const selectedCount = document.getElementById('selectedCount');
    
    if (bulkActions && selectedCount) {
        if (AppState.selectedResources.size > 0) {
            bulkActions.style.display = 'block';
            selectedCount.textContent = AppState.selectedResources.size;
        } else {
            bulkActions.style.display = 'none';
        }
    }
}

/**
 * Navigate pages with keyboard
 */
function navigatePage(direction) {
    if (direction === 'prev' && AppState.currentPage > 1) {
        AppState.currentPage--;
        loadResources();
    } else if (direction === 'next') {
        AppState.currentPage++;
        loadResources();
    }
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'is-info', duration = 3000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type} is-light`;
    notification.innerHTML = `
        <button class="delete" onclick="this.parentElement.remove()"></button>
        ${message}
    `;
    
    // Add to page
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(notification, container.firstChild);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, duration);
}

/**
 * Enhanced resource card rendering with animations
 */
function renderResourceCard(resource) {
    const template = document.getElementById('resourceCardTemplate');
    if (!template) return null;
    
    const card = template.content.cloneNode(true);
    
    // Populate card data
    const titleElement = card.querySelector('.resource-title');
    const urlElement = card.querySelector('.resource-url');
    const descriptionElement = card.querySelector('.resource-description');
    const categoryElement = card.querySelector('.resource-category');
    const dateElement = card.querySelector('.resource-date');
    
    // Set title in the subtitle paragraph
    if (titleElement) titleElement.textContent = resource.title || 'Untitled';
    
    // Set URL in the link element - both text and href
    if (urlElement) {
        urlElement.textContent = resource.url || '';
        urlElement.href = resource.url || '#';
    }
    
    // Set description
    if (descriptionElement) descriptionElement.textContent = resource.description || 'No description';
    
    // Set category
    if (categoryElement) categoryElement.textContent = resource.category || 'Uncategorized';
    
    // Set date
    if (dateElement) {
        const date = resource.created_at ? new Date(resource.created_at).toLocaleDateString() : 'Unknown';
        dateElement.textContent = date;
    }
    
    // Handle preview image display
    const previewImageColumn = card.querySelector('.preview-image-column');
    const previewImage = card.querySelector('.preview-image');
    const metadataInfo = card.querySelector('.metadata-info');
    const metadataSite = card.querySelector('.metadata-site');
    const metadataStatus = card.querySelector('.metadata-status');
    
    if (resource.link_metadata && resource.link_metadata.image && previewImage && previewImageColumn) {
        // Show preview image
        previewImage.src = resource.link_metadata.image;
        previewImage.alt = resource.link_metadata.title || resource.title || 'Preview';
        previewImageColumn.style.display = 'block';
        
        // Handle image load errors
        previewImage.onerror = function() {
            console.log('Failed to load preview image:', resource.link_metadata.image);
            previewImageColumn.style.display = 'none';
        };
    } else if (previewImageColumn) {
        // Hide preview image column if no image available
        previewImageColumn.style.display = 'none';
    }
    
    // Display metadata information
    if (resource.link_metadata && metadataInfo) {
        if (resource.link_metadata.site_name && metadataSite) {
            metadataSite.textContent = `Source: ${resource.link_metadata.site_name}`;
            metadataInfo.style.display = 'block';
        }
        
        if (resource.link_metadata.status === 'success' && metadataStatus) {
            metadataStatus.style.display = 'inline-flex';
        }
    }
    
    // Set up action buttons with resource ID
    const editBtn = card.querySelector('.edit-btn');
    const deleteBtn = card.querySelector('.delete-btn');
    const refreshBtn = card.querySelector('.refresh-metadata-btn');
    
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            // For now, just show a notification - edit functionality can be added later
            showNotification('Edit functionality coming soon!', 'is-info');
        });
    }
    
    if (deleteBtn) {
        deleteBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to delete this resource?')) {
                try {
                    const response = await fetch(`/api/resources/${resource.id}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        showNotification('Resource deleted successfully!', 'is-success');
                        loadResources(); // Reload the resources
                    } else {
                        throw new Error('Failed to delete resource');
                    }
                } catch (error) {
                    console.error('Error deleting resource:', error);
                    showNotification('Failed to delete resource', 'is-danger');
                }
            }
        });
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            try {
                showNotification('Refreshing metadata...', 'is-info');
                const response = await fetch(`/api/resources/${resource.id}/refresh-metadata`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showNotification('Metadata refreshed successfully!', 'is-success');
                    loadResources(); // Reload the resources
                } else {
                    throw new Error('Failed to refresh metadata');
                }
            } catch (error) {
                console.error('Error refreshing metadata:', error);
                showNotification('Failed to refresh metadata', 'is-danger');
            }
        });
    }
    
    // Add checkbox for bulk operations
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'resource-checkbox';
    checkbox.value = resource.id;
    checkbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            AppState.selectedResources.add(resource.id.toString());
        } else {
            AppState.selectedResources.delete(resource.id.toString());
        }
        updateBulkActionsUI();
    });
    
    const cardElement = card.querySelector('.resource-card');
    if (cardElement) {
        cardElement.insertBefore(checkbox, cardElement.firstChild);
        // Add animation class
        cardElement.classList.add('fade-in');
    }
    
    return card;
}

/**
 * Export selected resources
 */
async function exportResources() {
    try {
        const response = await fetch('/api/resources/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                resource_ids: Array.from(AppState.selectedResources)
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'resources.json';
            a.click();
            window.URL.revokeObjectURL(url);
            
            showNotification('Resources exported successfully', 'is-success');
        } else {
            showNotification('Error exporting resources', 'is-danger');
        }
    } catch (error) {
        console.error('Error exporting resources:', error);
        showNotification('Error exporting resources', 'is-danger');
    }
}

// Export functions for use in HTML
window.AppState = AppState;
window.searchResources = searchResources;
window.clearSearch = clearSearch;
window.filterByCategory = filterByCategory;
window.setViewMode = setViewMode;
window.exportResources = exportResources;
window.showNotification = showNotification;

/**
 * Load resources from the API
 */
async function loadResources() {
    const loadingState = document.getElementById('loadingState');
    const resourcesList = document.getElementById('resourcesList');
    const emptyState = document.getElementById('emptyState');
    const pagination = document.getElementById('pagination');
    
    if (loadingState) loadingState.style.display = 'block';
    if (resourcesList) resourcesList.innerHTML = '';
    if (emptyState) emptyState.style.display = 'none';
    if (pagination) pagination.style.display = 'none';
    
    AppState.isLoading = true;
    
    try {
        const params = new URLSearchParams({
            page: AppState.currentPage,
            per_page: 10
        });
        
        if (AppState.currentSearch) params.append('search', AppState.currentSearch);
        if (AppState.currentCategory) params.append('category', AppState.currentCategory);
        if (AppState.sortBy) params.append('sort_by', AppState.sortBy);
        if (AppState.sortOrder) params.append('sort_order', AppState.sortOrder);
        
        const response = await fetch(`/api/resources/?${params}`);
        const data = await response.json();
        
        if (loadingState) loadingState.style.display = 'none';
        AppState.isLoading = false;
        
        if (data.resources && data.resources.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
        } else {
            renderResources(data.resources || []);
            renderPagination(data);
        }
        
        updateResourceCount(data.total || 0);
        
    } catch (error) {
        console.error('Error loading resources:', error);
        if (loadingState) loadingState.style.display = 'none';
        AppState.isLoading = false;
        showNotification('Error loading resources', 'is-danger');
    }
}

/**
 * Filter resources by category
 */
function filterByCategory() {
    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter) {
        AppState.currentCategory = categoryFilter.value;
        AppState.currentPage = 1;
        loadResources();
    }
}

/**
 * Load categories for the filter dropdown
 */
async function loadCategories() {
    try {
        const response = await fetch('/api/resources/categories');
        const categories = await response.json();
        
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            // Clear existing options except "All Categories"
            categoryFilter.innerHTML = '<option value="">All Categories</option>';
            
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categoryFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

/**
 * Render resources in the UI
 */
function renderResources(resources) {
    const resourcesList = document.getElementById('resourcesList');
    if (!resourcesList) return;
    
    // Clear content but preserve CSS classes
    const currentClasses = resourcesList.className;
    resourcesList.innerHTML = '';
    resourcesList.className = currentClasses;
    
    resources.forEach(resource => {
        const resourceCard = renderResourceCard(resource);
        if (resourceCard) {
            resourcesList.appendChild(resourceCard);
        }
    });
}

/**
 * Render pagination controls
 */
function renderPagination(data) {
    const pagination = document.getElementById('pagination');
    
    // Calculate total pages from total and per_page
    const totalPages = Math.ceil((data.total || 0) / (data.per_page || 10));
    
    if (!pagination || !data.total || totalPages <= 1) return;
    
    pagination.style.display = 'flex';
    
    const prevPage = document.getElementById('prevPage');
    const nextPage = document.getElementById('nextPage');
    const pageNumbers = document.getElementById('pageNumbers');
    
    if (prevPage) {
        prevPage.disabled = data.page <= 1;
        prevPage.onclick = () => {
            if (data.page > 1) {
                AppState.currentPage = data.page - 1;
                loadResources();
            }
        };
    }
    
    if (nextPage) {
        nextPage.disabled = data.page >= totalPages;
        nextPage.onclick = () => {
            if (data.page < totalPages) {
                AppState.currentPage = data.page + 1;
                loadResources();
            }
        };
    }
    
    if (pageNumbers) {
        pageNumbers.innerHTML = '';
        for (let i = 1; i <= totalPages; i++) {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.className = `pagination-link ${i === data.page ? 'is-current' : ''}`;
            a.textContent = i;
            a.onclick = () => {
                AppState.currentPage = i;
                loadResources();
            };
            li.appendChild(a);
            pageNumbers.appendChild(li);
        }
    }
}

/**
 * Update resource count display
 */
function updateResourceCount(total) {
    const resourceCount = document.getElementById('resourceCount');
    if (resourceCount) {
        resourceCount.textContent = `${total} resource${total !== 1 ? 's' : ''}`;
    }
}