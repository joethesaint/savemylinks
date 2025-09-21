import { test, expect } from '@playwright/test';

test.describe('SaveMyLinks Resources', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('http://localhost:8000');
  });

  test('should load the application without errors', async ({ page }) => {
    // Check that the page loads
    await expect(page).toHaveTitle(/SaveMyLinks/);
    
    // Check that main elements are present
    await expect(page.locator('#resourcesList')).toBeVisible();
    await expect(page.locator('#searchInput')).toBeVisible();
    await expect(page.locator('#categorySelect')).toBeVisible();
  });

  test('should preserve CSS classes when loading resources', async ({ page }) => {
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
    
    // Get the resources list element
    const resourcesList = page.locator('#resourcesList');
    
    // Check that the resources list has the correct CSS classes
    await expect(resourcesList).toHaveClass(/resources-grid/);
    
    // Trigger a resource reload by searching
    await page.fill('#searchInput', 'test');
    await page.waitForTimeout(500); // Wait for debounce
    
    // Check that CSS classes are still preserved after reload
    await expect(resourcesList).toHaveClass(/resources-grid/);
  });

  test('should switch between grid and list view modes', async ({ page }) => {
    const resourcesList = page.locator('#resourcesList');
    
    // Should start in grid mode
    await expect(resourcesList).toHaveClass(/resources-grid/);
    
    // Switch to list mode
    await page.click('[data-view-mode="list"]');
    await expect(resourcesList).toHaveClass(/resources-list/);
    
    // Switch back to grid mode
    await page.click('[data-view-mode="grid"]');
    await expect(resourcesList).toHaveClass(/resources-grid/);
  });

  test('should handle search functionality', async ({ page }) => {
    // Wait for initial load
    await page.waitForLoadState('networkidle');
    
    // Perform a search
    await page.fill('#searchInput', 'example');
    
    // Wait for search debounce and API call
    await page.waitForTimeout(500);
    
    // Check that search was performed (URL should contain search parameter)
    await page.waitForFunction(() => {
      return window.AppState && window.AppState.currentSearch === 'example';
    });
  });

  test('should handle category filtering', async ({ page }) => {
    // Wait for categories to load
    await page.waitForLoadState('networkidle');
    
    // Check if category select has options
    const categorySelect = page.locator('#categorySelect');
    const options = await categorySelect.locator('option').count();
    
    if (options > 1) {
      // Select a category (skip the first "All Categories" option)
      await categorySelect.selectOption({ index: 1 });
      
      // Wait for filter to apply
      await page.waitForTimeout(500);
      
      // Check that category filter was applied
      await page.waitForFunction(() => {
        return window.AppState && window.AppState.currentCategory !== '';
      });
    }
  });

  test('should handle empty state correctly', async ({ page }) => {
    // Search for something that likely won't exist
    await page.fill('#searchInput', 'nonexistentresource12345');
    await page.waitForTimeout(500);
    
    // Check if empty state is shown or resources are displayed
    const emptyState = page.locator('#emptyState');
    const resourcesList = page.locator('#resourcesList');
    
    // Either empty state should be visible or resources list should have content
    const emptyStateVisible = await emptyState.isVisible();
    const resourcesListHasContent = await resourcesList.locator('.resource-card').count() > 0;
    
    // At least one should be true (either showing empty state or showing resources)
    expect(emptyStateVisible || resourcesListHasContent).toBeTruthy();
  });

  test('should handle loading states', async ({ page }) => {
    // Check that loading state appears during resource loading
    const loadingState = page.locator('#loadingState');
    
    // Trigger a new search to see loading state
    await page.fill('#searchInput', 'test');
    
    // Loading state might be very brief, so we check if it exists in DOM
    await expect(loadingState).toBeAttached();
  });

  test('should maintain app state correctly', async ({ page }) => {
    // Wait for app to initialize
    await page.waitForLoadState('networkidle');
    
    // Check that AppState is available globally
    const appState = await page.evaluate(() => window.AppState);
    
    expect(appState).toBeDefined();
    expect(appState.currentPage).toBe(1);
    expect(appState.viewMode).toBe('grid');
    expect(appState.sortBy).toBe('created_at');
    expect(appState.sortOrder).toBe('desc');
  });

  test('should handle keyboard shortcuts', async ({ page }) => {
    // Test Ctrl+K for search focus
    await page.keyboard.press('Control+k');
    
    // Check that search input is focused
    await expect(page.locator('#searchInput')).toBeFocused();
    
    // Test Escape to clear search
    await page.fill('#searchInput', 'test search');
    await page.keyboard.press('Escape');
    
    // Check that search input is cleared
    await expect(page.locator('#searchInput')).toHaveValue('');
  });

  test('should handle theme toggle', async ({ page }) => {
    const themeToggle = page.locator('#themeToggle');
    
    if (await themeToggle.isVisible()) {
      // Get initial theme
      const initialTheme = await page.getAttribute('html', 'data-theme');
      
      // Toggle theme
      await themeToggle.click();
      
      // Check that theme changed
      const newTheme = await page.getAttribute('html', 'data-theme');
      expect(newTheme).not.toBe(initialTheme);
    }
  });

  test('should handle resource interactions', async ({ page }) => {
    // Wait for resources to load
    await page.waitForLoadState('networkidle');
    
    // Check if there are any resource cards
    const resourceCards = page.locator('.resource-card');
    const cardCount = await resourceCards.count();
    
    if (cardCount > 0) {
      // Test checkbox selection
      const firstCheckbox = resourceCards.first().locator('.resource-checkbox');
      if (await firstCheckbox.isVisible()) {
        await firstCheckbox.check();
        
        // Check that bulk actions become visible
        const bulkActions = page.locator('#bulkActions');
        await expect(bulkActions).toBeVisible();
      }
    }
  });
});