# StreetEasiest - Wagtail CMS Project

A modern Wagtail CMS project with a clean, organized structure following best practices.

## Project Structure

```
StreetEasiest/
├── static_src/              # Source files for frontend assets
│   ├── sass/               # SCSS files
│   ├── javascript/         # JavaScript files and components
│   ├── images/             # Source images
│   └── fonts/              # Font files (if needed)
├── static_compiled/        # Compiled frontend assets (generated)
├── staticfiles/            # Collected static files (generated)
├── templates/              # Django/Wagtail templates
├── myproject/              # Django project settings and apps
├── media/                  # User-uploaded media files
└── fixtures/               # Database fixtures
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd StreetEasiest
   ```

2. **Set up Python environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up Node.js dependencies**
   ```bash
   npm install
   ```

4. **Build frontend assets**
   ```bash
   npm run build
   ```

5. **Initialize the project**
   ```bash
   make init
   ```

### Development

- **Start development server**: `make start`
- **Watch frontend assets**: `npm run start`
- **Build production assets**: `npm run build:prod`

### Available Commands

- `make init` - Initialize the project (build assets, load data, start server)
- `make start` - Start the Django development server
- `make build-assets` - Build frontend assets
- `make build-assets:watch` - Watch and rebuild frontend assets
- `make load-data` - Load initial data and collect static files
- `make reset-db` - Reset the database

## Features

- **Wagtail CMS** - Modern content management system
- **Tailwind CSS** - Utility-first CSS framework
- **Webpack** - Modern frontend build system
- **Sass** - CSS preprocessor
- **Responsive Design** - Mobile-first approach
- **Accessibility** - WCAG compliant components

## Static Files Management

The project uses a modern static files setup:

1. **Source files** are in `static_src/`
2. **Webpack** compiles them to `static_compiled/`
3. **Django** collects them to `staticfiles/` for production

This ensures clean separation between source and compiled assets while maintaining optimal performance.

## Contributing

1. Follow the existing code style
2. Ensure all tests pass
3. Build assets before committing
4. Update documentation as needed

## License

[Add your license information here]


