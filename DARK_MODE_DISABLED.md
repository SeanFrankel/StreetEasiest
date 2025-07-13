# Dark Mode Temporarily Disabled

## Overview
The dark mode functionality has been temporarily disabled across the website. All code has been preserved with explanatory comments for future reactivation.

## Changes Made

### 1. Template Changes
**File: `templates/navigation/header.html`**
- Commented out theme toggle includes in both desktop and mobile navigation
- Added explanatory comments about the disabled functionality

### 2. JavaScript Changes
**File: `static_src/javascript/main.js`**
- Commented out ThemeToggle import
- Commented out ThemeToggle initialization calls
- Added explanatory comments

**File: `static_compiled/js/main.js`**
- Manually removed ThemeToggle class from compiled JavaScript
- Removed ThemeToggle initialization calls
- Added explanatory comments

**File: `static_src/javascript/components/theme-toggle.js`**
- Added explanatory comment at the top of the file
- Component remains functional but not initialized

### 3. Template Component
**File: `templates/components/theme-toggle.html`**
- Added explanatory comment at the top of the file
- Template remains functional but not included in headers

### 4. Tailwind Configuration
**File: `tailwind.config.js`**
- Commented out `darkMode: 'class'` configuration
- Added explanatory comments

### 5. SCSS Styles
**File: `static_src/sass/main.scss`**
- Commented out dark mode styles in body selector
- Commented out dark mode styles in button-menu-toggle
- Added explanatory comments

## Reactivation Instructions
To reactivate dark mode functionality:

1. Uncomment the theme toggle includes in `templates/navigation/header.html`
2. Uncomment the ThemeToggle import and initialization in `static_src/javascript/main.js`
3. Uncomment `darkMode: 'class'` in `tailwind.config.js`
4. Uncomment dark mode styles in `static_src/sass/main.scss`
5. Rebuild static files using `npm run build` or equivalent
6. Run `python manage.py collectstatic --noinput`

## Notes
- All dark mode code has been preserved with clear comments
- The functionality can be easily reactivated when needed
- No code has been permanently removed
- Users will no longer see the dark mode toggle button
- The website will only display in light mode 