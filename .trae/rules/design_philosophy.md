**Purpose:** Outlines the UI/UX principles for the frontend, even if it's simple.

# SaveMyLinks - Design Philosophy

## Core Principle: Functional Minimalism
The UI must be clean, fast, accessible, and purely functional. The focus is on the content (the links), not on flashy design.

## Bulma CSS Framework
- Use Bulma's utility classes and components extensively. Prefer Bulma's built-in classes over custom CSS.
- Use a responsive layout based on Bulma's grid system (columns, column).
- Use Bulma's color palette for consistency. Primary color is is-link.
- Each resource should be displayed in a Bulma card component.

## Jinja2 Templating
- Use template inheritance. base.html should contain the core HTML structure, Bulma CSS CDN link, and a navigation bar.
- Child templates (e.g., index.html) should extend base.html and override the content block.
- Use Jinja2's for loops to iterate over lists of resources.
- Forms should use method="post" and have the necessary CSRF protection (if implemented) or use HTMX for enhanced functionality.

## User Experience
- The homepage (/) must immediately show the list of curated resources.
- The form to add a new resource should be on a separate page (/add).
- Provide clear visual feedback for actions (e.g., use Bulma's is-success notification on successful form submission).
- Ensure all interactive elements are accessible via keyboard and screen readers.
