/**
 * Type definitions for SaveMyLinks application
 */

// Resource interface
export interface Resource {
  id: number;
  url: string;
  title: string;
  description?: string;
  category?: string;
  tags?: string[];
  preview_image?: string;
  created_at: string;
  updated_at: string;
  metadata?: ResourceMetadata;
}

// Resource metadata interface
export interface ResourceMetadata {
  title?: string;
  description?: string;
  image?: string;
  site_name?: string;
  type?: string;
}

// API response interfaces
export interface ResourcesResponse {
  resources: Resource[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface Category {
  name: string;
  count: number;
}

export interface CategoriesResponse {
  categories: Category[];
}

// Application state interface
export interface AppState {
  currentPage: number;
  currentSearch: string;
  currentCategory: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  viewMode: 'grid' | 'list';
  selectedResources: Set<number>;
  isLoading: boolean;
}

// UI notification types
export type NotificationType = 'is-info' | 'is-success' | 'is-warning' | 'is-danger';

// Theme types
export type Theme = 'light' | 'dark';

// Sort options
export type SortBy = 'created_at' | 'updated_at' | 'title' | 'url';

// Export format types
export type ExportFormat = 'json' | 'csv' | 'html';

// DOM element selectors
export interface DOMElements {
  resourcesList: HTMLElement | null;
  searchInput: HTMLInputElement | null;
  categorySelect: HTMLSelectElement | null;
  sortSelect: HTMLSelectElement | null;
  viewModeButtons: NodeListOf<HTMLButtonElement>;
  loadingState: HTMLElement | null;
  emptyState: HTMLElement | null;
  pagination: HTMLElement | null;
  bulkActions: HTMLElement | null;
  selectAllCheckbox: HTMLInputElement | null;
}

// Event handler types
export type EventHandler<T = Event> = (event: T) => void;
export type AsyncEventHandler<T = Event> = (event: T) => Promise<void>;

// API error interface
export interface APIError {
  message: string;
  status: number;
  details?: unknown;
}