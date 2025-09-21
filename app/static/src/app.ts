/**
 * SaveMyLinks - Enhanced Search and UI Functionality (TypeScript)
 * This file contains advanced search, filtering, and UI enhancement features
 */

import type {
  Resource,
  ResourcesResponse,
  CategoriesResponse,
  AppState,
  NotificationType,
  Theme,
  DOMElements,
  EventHandler,
  AsyncEventHandler,
  APIError
} from './types.js';

// Global state management with proper typing
const AppState: AppState = {
  currentPage: 1,
  currentSearch: '',
  currentCategory: '',
  sortBy: 'created_at',
  sortOrder: 'desc',
  viewMode: 'grid',
  selectedResources: new Set<number>(),
  isLoading: false
};

// DOM elements cache
let domElements: DOMElements;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', (): void => {
  initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp(): void {
  // Cache DOM elements
  domElements = {
    resourcesList: document.getElementById('resourcesList'),
    searchInput: document.getElementById('searchInput') as HTMLInputElement | null,
    categorySelect: document.getElementById('categorySelect') as HTMLSelectElement | null,
    sortSelect: document.getElementById('sortSelect') as HTMLSelectElement | null,
    viewModeButtons: document.querySelectorAll('[data-view-mode]') as NodeListOf<HTMLButtonElement>,
    loadingState: document.getElementById('loadingState'),
    emptyState: document.getElementById('emptyState'),
    pagination: document.getElementById('pagination'),
    bulkActions: document.getElementById('bulkActions'),
    selectAllCheckbox: document.getElementById('selectAll') as HTMLInputElement | null
  };

  // Load saved view mode from localStorage or default to grid
  const savedViewMode = (localStorage.getItem('viewMode') as 'grid' | 'list') || 'grid';
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
function setupEventListeners(): void {
  // Search input with debouncing
  if (domElements.searchInput) {
    let searchTimeout: number;
    domElements.searchInput.addEventListener('input', (): void => {
      clearTimeout(searchTimeout);
      searchTimeout = window.setTimeout(() => {
        searchResources();
      }, 300); // 300ms debounce
    });
  }

  // Category filter
  if (domElements.categorySelect) {
    domElements.categorySelect.addEventListener('change', filterByCategory);
  }

  // Sort functionality
  if (domElements.sortSelect) {
    domElements.sortSelect.addEventListener('change', handleSortChange);
  }

  // View mode buttons
  domElements.viewModeButtons.forEach(button => {
    button.addEventListener('click', (e: Event): void => {
      const target = e.target as HTMLButtonElement;
      const mode = target.dataset.viewMode as 'grid' | 'list';
      if (mode) {
        setViewMode(mode);
      }
    });
  });

  // Bulk actions
  if (domElements.selectAllCheckbox) {
    domElements.selectAllCheckbox.addEventListener('change', handleSelectAll);
  }

  const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', handleBulkDelete);
  }

  // Export functionality
  const exportBtn = document.getElementById('exportBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', exportResources);
  }
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts(): void {
  document.addEventListener('keydown', (e: KeyboardEvent): void => {
    // Ctrl/Cmd + K for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      domElements.searchInput?.focus();
    }
    
    // Escape to clear search
    if (e.key === 'Escape' && domElements.searchInput === document.activeElement) {
      clearSearch();
    }
    
    // Ctrl/Cmd + A for select all (when not in input)
    if ((e.ctrlKey || e.metaKey) && e.key === 'a' && 
        document.activeElement?.tagName !== 'INPUT' && 
        document.activeElement?.tagName !== 'TEXTAREA') {
      e.preventDefault();
      handleSelectAll();
    }
  });
}

/**
 * Setup theme toggle functionality
 */
function setupThemeToggle(): void {
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    const savedTheme = (localStorage.getItem('theme') as Theme) || 'light';
    setTheme(savedTheme);
    
    themeToggle.addEventListener('click', (): void => {
      const currentTheme = document.documentElement.getAttribute('data-theme') as Theme;
      const newTheme: Theme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
    });
  }
}

/**
 * Set application theme
 */
function setTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
}

/**
 * Search resources with current query
 */
function searchResources(): void {
  AppState.currentSearch = domElements.searchInput?.value || '';
  AppState.currentPage = 1;
  loadResources();
}

/**
 * Clear search input and results
 */
function clearSearch(): void {
  if (domElements.searchInput) {
    domElements.searchInput.value = '';
  }
  AppState.currentSearch = '';
  AppState.currentPage = 1;
  loadResources();
}

/**
 * Toggle advanced search panel
 */
function toggleAdvancedSearch(): void {
  const advancedSearch = document.getElementById('advancedSearch');
  if (advancedSearch) {
    advancedSearch.classList.toggle('is-hidden');
  }
}

/**
 * Handle sort change
 */
function handleSortChange(): void {
  if (!domElements.sortSelect) return;
  
  const [sortBy, sortOrder] = domElements.sortSelect.value.split('_');
  if (sortBy) {
    AppState.sortBy = sortBy;
  }
  AppState.sortOrder = (sortOrder as 'asc' | 'desc') || 'desc';
  AppState.currentPage = 1;
  loadResources();
}

/**
 * Set view mode (grid or list)
 */
function setViewMode(mode: 'grid' | 'list'): void {
  AppState.viewMode = mode;
  localStorage.setItem('viewMode', mode);
  
  // Update resources list class - FIXED: Preserve existing classes
  if (domElements.resourcesList) {
    // Remove old view mode classes and add new one
    domElements.resourcesList.classList.remove('resources-grid', 'resources-list');
    domElements.resourcesList.classList.add(`resources-${mode}`);
  }
  
  // Update button states
  domElements.viewModeButtons.forEach(button => {
    const buttonMode = button.dataset.viewMode;
    button.classList.toggle('is-active', buttonMode === mode);
  });
  
  // Reload resources to apply new view
  loadResources();
}

/**
 * Handle select all checkbox
 */
function handleSelectAll(): void {
  const isChecked = domElements.selectAllCheckbox?.checked || false;
  const checkboxes = document.querySelectorAll('.resource-checkbox') as NodeListOf<HTMLInputElement>;
  
  checkboxes.forEach(checkbox => {
    checkbox.checked = isChecked;
    const resourceId = parseInt(checkbox.dataset.resourceId || '0');
    if (isChecked) {
      AppState.selectedResources.add(resourceId);
    } else {
      AppState.selectedResources.delete(resourceId);
    }
  });
  
  updateBulkActionsUI();
}

/**
 * Handle bulk delete operation
 */
async function handleBulkDelete(): Promise<void> {
  if (AppState.selectedResources.size === 0) return;
  
  const confirmed = confirm(`Are you sure you want to delete ${AppState.selectedResources.size} resources?`);
  if (!confirmed) return;
  
  try {
    const deletePromises = Array.from(AppState.selectedResources).map(id =>
      fetch(`/api/resources/${id}`, { method: 'DELETE' })
    );
    
    await Promise.all(deletePromises);
    
    AppState.selectedResources.clear();
    updateBulkActionsUI();
    loadResources();
    showNotification('Resources deleted successfully', 'is-success');
  } catch (error) {
    console.error('Error deleting resources:', error);
    showNotification('Error deleting resources', 'is-danger');
  }
}

/**
 * Update bulk actions UI based on selection
 */
function updateBulkActionsUI(): void {
  const selectedCount = AppState.selectedResources.size;
  const bulkActionsCount = document.getElementById('bulkActionsCount');
  
  if (domElements.bulkActions) {
    domElements.bulkActions.style.display = selectedCount > 0 ? 'block' : 'none';
  }
  
  if (bulkActionsCount) {
    bulkActionsCount.textContent = selectedCount.toString();
  }
}

/**
 * Navigate to different page
 */
function navigatePage(direction: 'prev' | 'next' | number): void {
  if (typeof direction === 'number') {
    AppState.currentPage = direction;
  } else if (direction === 'prev' && AppState.currentPage > 1) {
    AppState.currentPage--;
  } else if (direction === 'next') {
    AppState.currentPage++;
  }
  loadResources();
}

/**
 * Show notification to user
 */
function showNotification(message: string, type: NotificationType = 'is-info', duration: number = 3000): void {
  const notification = document.createElement('div');
  notification.className = `notification ${type} is-light`;
  notification.innerHTML = `
    <button class="delete"></button>
    ${message}
  `;
  
  const container = document.querySelector('.container') || document.body;
  container.insertBefore(notification, container.firstChild);
  
  // Auto dismiss
  setTimeout(() => {
    notification.remove();
  }, duration);
  
  // Manual dismiss
  const deleteBtn = notification.querySelector('.delete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => notification.remove());
  }
}

/**
 * Render a single resource card
 */
function renderResourceCard(resource: Resource): HTMLElement | null {
  if (!resource) return null;

  const card = document.createElement('div');
  card.className = 'resource-card';
  card.dataset.resourceId = resource.id.toString();

  const previewImage = resource.preview_image || resource.metadata?.image;
  const title = resource.title || resource.metadata?.title || 'Untitled';
  const description = resource.description || resource.metadata?.description || '';
  const domain = new URL(resource.url).hostname;

  card.innerHTML = `
    <div class="resource-card-content">
      ${previewImage ? `
        <div class="resource-preview">
          <img src="${previewImage}" alt="${title}" loading="lazy" onerror="this.style.display='none'">
        </div>
      ` : ''}
      
      <div class="resource-content">
        <div class="resource-header">
          <input type="checkbox" class="resource-checkbox" data-resource-id="${resource.id}">
          <h3 class="resource-title">
            <a href="${resource.url}" target="_blank" rel="noopener noreferrer">${title}</a>
          </h3>
        </div>
        
        ${description ? `<p class="resource-description">${description}</p>` : ''}
        
        <div class="resource-meta">
          <span class="resource-domain">${domain}</span>
          ${resource.category ? `<span class="resource-category tag is-small">${resource.category}</span>` : ''}
          <span class="resource-date">${new Date(resource.created_at).toLocaleDateString()}</span>
        </div>
        
        ${resource.tags && resource.tags.length > 0 ? `
          <div class="resource-tags">
            ${resource.tags.map(tag => `<span class="tag is-small">${tag}</span>`).join('')}
          </div>
        ` : ''}
      </div>
      
      <div class="resource-actions">
        <button class="button is-small is-danger" onclick="deleteResource(${resource.id})">
          <span class="icon"><i class="fas fa-trash"></i></span>
        </button>
        <button class="button is-small" onclick="editResource(${resource.id})">
          <span class="icon"><i class="fas fa-edit"></i></span>
        </button>
      </div>
    </div>
  `;

  // Add event listener for checkbox
  const checkbox = card.querySelector('.resource-checkbox') as HTMLInputElement;
  if (checkbox) {
    checkbox.addEventListener('change', (e: Event): void => {
      const target = e.target as HTMLInputElement;
      const resourceId = parseInt(target.dataset.resourceId || '0');
      
      if (target.checked) {
        AppState.selectedResources.add(resourceId);
      } else {
        AppState.selectedResources.delete(resourceId);
      }
      
      updateBulkActionsUI();
    });
  }

  return card;
}

/**
 * Export resources in various formats
 */
async function exportResources(): Promise<void> {
  try {
    const response = await fetch('/api/resources/export');
    const blob = await response.blob();
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `savemylinks-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showNotification('Resources exported successfully', 'is-success');
  } catch (error) {
    console.error('Error exporting resources:', error);
    showNotification('Error exporting resources', 'is-danger');
  }
}

/**
 * Load resources from API
 */
async function loadResources(): Promise<void> {
  if (!domElements.resourcesList) return;

  // Show loading state
  if (domElements.loadingState) domElements.loadingState.style.display = 'block';
  if (domElements.emptyState) domElements.emptyState.style.display = 'none';
  if (domElements.pagination) domElements.pagination.style.display = 'none';
  
  // FIXED: Preserve classes when clearing content
  const currentClasses = domElements.resourcesList.className;
  domElements.resourcesList.innerHTML = '';
  domElements.resourcesList.className = currentClasses;
  
  AppState.isLoading = true;

  try {
    const params = new URLSearchParams({
      page: AppState.currentPage.toString(),
      per_page: '10'
    });

    if (AppState.currentSearch) params.append('search', AppState.currentSearch);
    if (AppState.currentCategory) params.append('category', AppState.currentCategory);
    if (AppState.sortBy) params.append('sort_by', AppState.sortBy);
    if (AppState.sortOrder) params.append('sort_order', AppState.sortOrder);

    const response = await fetch(`/api/resources/?${params}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data: ResourcesResponse = await response.json();

    // Hide loading state
    if (domElements.loadingState) domElements.loadingState.style.display = 'none';
    AppState.isLoading = false;

    if (!data.resources || data.resources.length === 0) {
      if (domElements.emptyState) domElements.emptyState.style.display = 'block';
    } else {
      renderResources(data.resources);
      renderPagination(data);
    }

    updateResourceCount(data.total || 0);

  } catch (error) {
    console.error('Error loading resources:', error);
    if (domElements.loadingState) domElements.loadingState.style.display = 'none';
    AppState.isLoading = false;
    showNotification('Error loading resources', 'is-danger');
  }
}

/**
 * Filter resources by category
 */
function filterByCategory(): void {
  AppState.currentCategory = domElements.categorySelect?.value || '';
  AppState.currentPage = 1;
  loadResources();
}

/**
 * Load categories from API
 */
async function loadCategories(): Promise<void> {
  try {
    const response = await fetch('/api/categories/');
    const data: CategoriesResponse = await response.json();
    
    if (domElements.categorySelect && data.categories) {
      // Clear existing options except the first one
      const firstOption = domElements.categorySelect.firstElementChild;
      domElements.categorySelect.innerHTML = '';
      if (firstOption) {
        domElements.categorySelect.appendChild(firstOption);
      }
      
      // Add category options
      data.categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category.name;
        option.textContent = `${category.name} (${category.count})`;
        domElements.categorySelect!.appendChild(option);
      });
    }
  } catch (error) {
    console.error('Error loading categories:', error);
  }
}

/**
 * Render resources in the DOM
 */
function renderResources(resources: Resource[]): void {
  if (!domElements.resourcesList) return;

  // FIXED: Don't clear classes, they're already preserved in loadResources
  resources.forEach(resource => {
    const resourceCard = renderResourceCard(resource);
    if (resourceCard) {
      domElements.resourcesList!.appendChild(resourceCard);
    }
  });
}

/**
 * Render pagination controls
 */
function renderPagination(data: ResourcesResponse): void {
  if (!domElements.pagination || !data.pages || data.pages <= 1) return;

  let paginationHTML = '<nav class="pagination is-centered" role="navigation">';
  
  // Previous button
  if (data.page > 1) {
    paginationHTML += `<button class="pagination-previous" onclick="navigatePage('prev')">Previous</button>`;
  } else {
    paginationHTML += `<button class="pagination-previous" disabled>Previous</button>`;
  }
  
  // Next button
  if (data.page < data.pages) {
    paginationHTML += `<button class="pagination-next" onclick="navigatePage('next')">Next</button>`;
  } else {
    paginationHTML += `<button class="pagination-next" disabled>Next</button>`;
  }
  
  // Page numbers
  paginationHTML += '<ul class="pagination-list">';
  
  const startPage = Math.max(1, data.page - 2);
  const endPage = Math.min(data.pages, data.page + 2);
  
  if (startPage > 1) {
    paginationHTML += `<li><button class="pagination-link" onclick="navigatePage(1)">1</button></li>`;
    if (startPage > 2) {
      paginationHTML += `<li><span class="pagination-ellipsis">&hellip;</span></li>`;
    }
  }
  
  for (let i = startPage; i <= endPage; i++) {
    const isActive = i === data.page ? 'is-current' : '';
    paginationHTML += `<li><button class="pagination-link ${isActive}" onclick="navigatePage(${i})">${i}</button></li>`;
  }
  
  if (endPage < data.pages) {
    if (endPage < data.pages - 1) {
      paginationHTML += `<li><span class="pagination-ellipsis">&hellip;</span></li>`;
    }
    paginationHTML += `<li><button class="pagination-link" onclick="navigatePage(${data.pages})">${data.pages}</button></li>`;
  }
  
  paginationHTML += '</ul></nav>';
  
  domElements.pagination.innerHTML = paginationHTML;
  domElements.pagination.style.display = 'block';
}

/**
 * Update resource count display
 */
function updateResourceCount(total: number): void {
  const countElement = document.getElementById('resourceCount');
  if (countElement) {
    countElement.textContent = `${total} resource${total !== 1 ? 's' : ''}`;
  }
}

// Global function exports for HTML onclick handlers
declare global {
  interface Window {
    AppState: AppState;
    searchResources: () => void;
    clearSearch: () => void;
    filterByCategory: () => void;
    setViewMode: (mode: 'grid' | 'list') => void;
    exportResources: () => Promise<void>;
    showNotification: (message: string, type?: NotificationType, duration?: number) => void;
    navigatePage: (direction: 'prev' | 'next' | number) => void;
    deleteResource: (id: number) => Promise<void>;
    editResource: (id: number) => void;
  }
}

// Export functions to global scope for HTML compatibility
window.AppState = AppState;
window.searchResources = searchResources;
window.clearSearch = clearSearch;
window.filterByCategory = filterByCategory;
window.setViewMode = setViewMode;
window.exportResources = exportResources;
window.showNotification = showNotification;
window.navigatePage = navigatePage;

// Placeholder functions for HTML onclick handlers
window.deleteResource = async (id: number): Promise<void> => {
  const confirmed = confirm('Are you sure you want to delete this resource?');
  if (!confirmed) return;
  
  try {
    const response = await fetch(`/api/resources/${id}`, { method: 'DELETE' });
    if (response.ok) {
      loadResources();
      showNotification('Resource deleted successfully', 'is-success');
    } else {
      throw new Error('Failed to delete resource');
    }
  } catch (error) {
    console.error('Error deleting resource:', error);
    showNotification('Error deleting resource', 'is-danger');
  }
};

window.editResource = (id: number): void => {
  // Placeholder for edit functionality
  console.log('Edit resource:', id);
  showNotification('Edit functionality not implemented yet', 'is-warning');
};