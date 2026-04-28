# LOFT Design - Premium Interior Solutions Platform

LOFT Design is a sophisticated, high-end platform built on Django 5.2, designed for architectural firms and interior design studios to showcase their portfolios and manage premium product collections. The platform combines a **Neo-Brutalist** aesthetic with high-performance backend architecture, offering a "Single Point of Truth" configuration and full multi-language support.

## 🏛 Architecture & Key Features

### 1. Centralized Identity Management
Manage global site metadata, including brand names, multi-language taglines, contact information, and working hours, from a single configuration point in `core/context_processors.py`.

### 2. Variable-Driven Dynamic Branding
The entire UI is powered by backend-injected CSS variables. Adjusting the primary or secondary colors in the configuration instantly propagates changes across both the public landing page and the administrative dashboard.

### 3. Neo-Brutalist Public Interface
- **Portfolio Showcase**: High-impact project gallery with detailed case studies, 360° virtual tour integration, and technical specifications.
- **Product Catalog**: A curated collection management system with external affiliate links, direct contact leads, and premium display cards.
- **Modern Interactions**: Smooth AOS-powered animations, bold high-contrast hover effects, and tactile UI feedback.

### 4. Enterprise-Grade Globalization
- **Full i18n**: Native support for Arabic (AR), English (EN), and French (FR).
- **Automated RTL/LTR**: Dynamic layout switching that intelligently re-aligns borders, shadows, and navigation based on the active locale.

### 5. Advanced Component Library
- **Generic UI Blocks**: Specialized pagination, custom select wrappers, and interactive file inputs.
- **AJAX-First Pattern**: Standardized form handling with integrated loading states and translatable SweetAlert2 feedback.

## 🛠 Tech Stack

- **Framework**: Django 5.2+
- **Database**: PostgreSQL (Docker-ready)
- **Styling**: Bootstrap 5.3 + Custom Neo-Brutalist CSS Framework
- **Environment**: python-decouple for secure secret management
- **Containerization**: Optimized Multi-stage Docker Build

## 🚀 Getting Started

### 1. Installation
```bash
git clone https://github.com/amraoui-mo7amed/loftdesign
cd loftdesign
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file from the provided example:
```bash
cp .env.example .env
```
Generate a secure `APP_SECRET`:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 3. System Initialization
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Internationalization Workflow
To update translation strings:
```bash
python manage.py makemessages -l ar
python manage.py compilemessages
```

## 🐳 Docker Deployment
The project includes a production-ready `Dockerfile` with all necessary dependencies, including `gettext` for runtime translations.

```bash
docker-compose up --build
```

## 📖 Development Standards

### AJAX Form Implementation
To maintain the platform's seamless user experience, views should return standardized `JsonResponse` objects:

```python
return JsonResponse({
    "success": True,
    "message": _("Record updated successfully."),
    "redirect_url": "/path/to/redirect/"
})
```

### CSS Conventions
When adding styles, always account for text directionality:
```css
[dir="rtl"] .brutalist-card:hover {
    transform: translate(8px, -8px);
    box-shadow: -8px 8px 0px var(--brand-dark);
}
```

## 📄 License
Custom developed for LOFT Design. All rights reserved.
