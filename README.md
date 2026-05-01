# LOFT Design - Premium Interior Solutions Platform

LOFT Design is a sophisticated, high-end architectural and interior design platform built on **Django 5.2**. It is engineered to bridge the gap between creative project showcasing and lead-driven commerce. Featuring a **Neo-Brutalist** aesthetic, the platform offers a robust administrative ecosystem for managing portfolios, product catalogs, and real-time customer interactions.

---

## Core Features & Modules

### 1. Advanced Portfolio Management
A high-impact showcase for architectural projects.
- **Dynamic Galleries**: Multi-image project layouts with automated thumbnail generation.
- **Project Metadata**: Categorized project details including tags, external documentation links, and technical specifications.
- **Immersive UX**: Integrated support for 360° virtual tours and interactive project case studies.

### 2. Curated Product Catalog & Lead Generation
A specialized commerce layer for interior design components.
- **Affiliate Integration**: Direct external linking for high-end furniture and decor.
- **Lead Capture System**: Integrated order tracking for direct product inquiries.
- **Inventory Control**: Status-driven catalog management (Active/Inactive) with categorized navigation.

### 3. Real-time Notification Engine
Powered by **django-eventstream** and Server-Sent Events (SSE).
- **Asynchronous Updates**: Real-time delivery of system alerts, order notifications, and approval status updates.
- **Interaction Management**: User-specific notification streams with read/unread tracking and standardized interaction types (Info, Success, Warning, Error).

### 4. Administrative Ecosystem (Dashboard)
A comprehensive backend for studio operations.
- **User Governance**: Full lifecycle management for staff profiles including approval workflows and role-based access.
- **Order Pipeline**: Centralized management of product leads with status tracking (Pending → Processing → Completed).
- **Content Operations**: CRUD interfaces for portfolios, categories, and inventory.

### 5. Globalization & Localization (i18n/L10n)
- **Native RTL/LTR Architecture**: Dynamic layout switching specifically optimized for Arabic, English, and French.
- **Locale-Aware UI**: Intelligently re-aligning shadows, borders, and navigation based on the active language.

---

## Technical Stack

- **Backend**: Django 5.2 (Python 3.11+)
- **Database**: PostgreSQL 15 (Optimized with health checks)
- **Real-time**: SSE via `django-eventstream`
- **Frontend**: Bootstrap 5.3 + Custom CSS variable-driven branding
- **Deployment**: 
  - **Docker & Docker Compose**: Multi-environment orchestration (Dev/Prod)
  - **Reverse Proxy**: Nginx with automated SSL via Certbot

---

## Environment Orchestration

The project uses a separated Docker strategy to ensure environment parity while optimizing local development.

### Local Development
The development environment is configured for **hot-reloading** and direct debugging.
```bash
# Starts the dev stack using docker-compose.dev.yml (set as default via COMPOSE_FILE)
docker compose up --build
```

### Production Stack
The production stack includes Nginx, SSL termination, and optimized Gunicorn/Daphne workers.
```bash
# Forces the production configuration
docker compose -f docker-compose.yml up -d
```

---

## Setup & Installation

### 1. Initialization
```bash
git clone https://github.com/amraoui-mo7amed/loftdesign
cp .env.example .env
```

### 2. Dependency Management
```bash
# Using Virtualenv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Database & Admin
```bash
python manage.py migrate
python manage.py init_admin  # Custom command to initialize studio administration
```

---

## Developer Standards

### AJAX-First Interaction Pattern
All destructive or state-changing actions (Delete, Status Update, Approve) must utilize AJAX to provide seamless feedback via SweetAlert2.

**Standardized Response Format:**
```python
return JsonResponse({
    "success": True,
    "message": _("Notification marked as read"),
    "data": {} # Optional
})
```

### CSS Variables & Branding
Global branding is managed via CSS variables injected through the backend. Avoid hardcoding hex values; use the established design tokens.

---

## License
Internal Studio License. Proprietary to LOFT Design.
