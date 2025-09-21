**Purpose:** Comprehensive guide for UI/UX implementation, focusing on maintainable, accessible, and user-friendly design.

# SaveMyLinks - Design Philosophy

## Core Principle: Functional Minimalism
The UI must embody simplicity while maintaining full functionality:
- Clean, uncluttered layouts with consistent spacing and alignment
- Fast loading times (<2s target) through optimized assets
- WCAG 2.1 AA compliance for accessibility
- Content-first approach prioritizing link readability and usability
- Minimal animations, used only for functional feedback

## Bulma CSS Framework Implementation
### Core Usage
- Leverage Bulma's utility classes as primary styling method
- Minimize custom CSS; when needed, follow Bulma's naming conventions
- Maintain mobile-first responsive design using Bulma breakpoints

### Layout Structure
- Implement 12-column grid system consistently
- Use container > columns > column hierarchy
- Apply appropriate spacing classes (m-*, p-*) for consistent gutters
- Ensure responsive behavior at standard breakpoints (mobile, tablet, desktop)

### Components & Styling
- Resource Cards:
  - Use card component with card-header, card-content structure
  - Implement hover states for interactive feedback
  - Maintain consistent padding (p-4) and margins (m-2)
- Color System:
  - Primary: is-link (#485fc7)
  - Success: is-success (#48c78e)
  - Warning: is-warning (#ffe08a)
  - Error: is-danger (#f14668)
- Typography:
  - Use Bulma's built-in size classes (is-size-*)
  - Maintain readable line lengths (max-width on containers)

## Jinja2 Templating Architecture
### Base Template (base.html)
- DOCTYPE and meta tags for proper rendering
- Responsive viewport meta tag
- Bulma CSS CDN integration
- Common header with navigation
- Footer with essential links
- Defined content blocks:
  - {% block head %}
  - {% block content %}
  - {% block scripts %}

### Component Templates
- Create reusable components for:
  - Resource cards
  - Forms
  - Navigation elements
  - Notification messages

### Forms & Security
- Implement POST method consistently
- CSRF protection on all forms
- HTMX Integration:
  - Use for dynamic content loading
  - Implement proper swap strategies
  - Include loading indicators

## User Experience Guidelines
### Navigation & Information Architecture
- Homepage (/):
  - Immediate resource visibility
  - Clear categorization
  - Efficient search/filter capabilities
- Add Resource Page (/add):
  - Clear form layout
  - Input validation feedback
  - Success/error states

### Interaction Design
- Visual Feedback:
  - Loading states using is-loading class
  - Success notifications (is-success)
  - Error states (is-danger)
  - Hover effects on interactive elements
- Form Interactions:
  - Real-time validation where appropriate
  - Clear error messages
  - Autocomplete where beneficial

### Accessibility Requirements
- ARIA labels on interactive elements
- Proper heading hierarchy (h1-h6)
- Keyboard navigation support
- Color contrast ratios meeting WCAG 2.1 AA
- Screen reader compatibility
- Focus indicators on interactive elements

### Performance Considerations
- Lazy loading for images
- Minimal initial payload
- Efficient caching strategies
- Progressive enhancement approach
