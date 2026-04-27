# Django Starter Kit

A robust, centralized, and highly customizable Django boilerplate designed for rapid project scaffolding. This kit focuses on a "Single Point of Truth" configuration, multi-language support (AR/EN/FR), and modern UI components.

## Key Features

- **Centralized Configuration**: Manage site name, logo, contact details, and SEO metadata from a single Python file (`core/context_processors.py`).
- **Dynamic Branding**: UI colors are driven by CSS variables injected from the backend. Change your brand colors in one place, and the entire site (Dashboard & Frontend) updates instantly.
- **Full i18n & RTL Support**: Built-in support for Arabic (RTL), English (LTR), and French (LTR) with automatic layout switching.
- **Modern Component Library**: Ready-to-use generic components: Select tags, File Inputs, and specialized Pagination.
- **AJAX-First Pattern**: Standardized form handling with loading states and translatable SweetAlert2/error list feedback.

## Tech Stack

- **Backend**: Django 5.2+
- **Environment**: python-decouple
- **Styling**: Bootstrap 5.3 + Variable-driven CSS
- **Real-time**: Django EventStream + SSE

## Getting Started

### 1. Clone & Install
```bash
git clone https://github.com/amraoui-mo7amed/dj-starter-kit
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and set your variables.
```bash
cp .env.example .env
```

**Generate a Safe Secret Key:**
Run this command to generate a secure key for `APP_SECRET`:
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

| Variable | Description |
|----------|-------------|
| `APP_SECRET` | Your Django secret key (generate a unique one for production). |
| `APP_ENV` | Set to `development` for local work or `production` to disable debug mode. |
| `APP_ALLOWED_HOSTS` | Comma-separated list of domains (e.g., `localhost,127.0.0.1,yourdomain.com`). |
| `EMAIL_*` | SMTP settings for account activation and notification emails. |

### 3. Database Setup
```bash
python manage.py migrate
```

### 4. Create Superuser (Admin)
To access the dashboard management features and Django admin:
```bash
python manage.py createsuperuser
```

### 5. Seed Database (Optional)
Generate randomized generic user profiles for development:
```bash
python manage.py seed_users 10
```

## Development Guide

### Creating an AJAX-Compatible View
The project uses a centralized JavaScript handler for forms with the `.form` class. To make a view compatible with the `errorList.html` partial and SweetAlert feedback, return a `JsonResponse` as follows:

```python
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

def your_view(request):
    if request.method == "POST":
        # 1. Validation Logic
        errors = []
        if not request.POST.get("name"):
            errors.append(_("Name is required."))
        
        if errors:
            return JsonResponse({"success": False, "errors": errors})

        # 2. Processing Logic
        # ... your code ...

        # 3. Success Response
        return JsonResponse({
            "success": True,
            "message": _("Action completed successfully!"),
            "redirect_url": "/dashboard/success/" # Optional redirect
        })
```

**Template Usage:**
```html
{% include "partials/errorList.html" with form_id="yourFormId" %}
<form id="yourFormId" class="form" method="post">
    ...
</form>
```

## Customization

### 1. Project Identity
Edit the `site_config` dictionary in `core/context_processors.py` to change branding, SEO, and contact details globally.

### 2. Dashboard Navigation & RBAC
Manage menu items in `dashboard/context_processors.py`. Use the `admin_only: True` flag to restrict specific links to superusers.

## License
This is a generic boilerplate for future projects. Customize and extend as needed.
