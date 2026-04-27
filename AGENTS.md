# AGENTS.md - Agentic Coding Guidelines

## Project Overview
SnapStore is an AI-powered landing page generator for merchants. It uses pre-built templates to create landing pages with hero sections, benefits, pricing, and order forms. The AI (Gemini API) generates persuasive CTAs and content to boost conversions.

## Build/Lint/Test Commands

```bash
# Django Commands
python manage.py runserver              # Start development server
python manage.py makemigrations         # Generate migrations
python manage.py migrate                # Apply migrations
python manage.py createsuperuser        # Create admin user

# Run Tests
python manage.py test                   # Run all tests
python manage.py test <app_name>        # Run tests for specific app
python manage.py test <app>.tests.<ClassName>  # Run specific test class
python manage.py test <app>.tests.<ClassName>.<method>  # Run single test

# Linting
pip install djlint                      # Install djlint if needed
djlint .                                 # Lint all templates
djlint . --reformat                     # Reformat templates

# Python Code Quality
python -m py_compile <file>.py         # Syntax check
python -m compileall .                  # Compile all .py files
```

## Code Style Guidelines

### Python / Django

**Imports (PEP 8)**
```python
# Standard library imports first
import os
import json
from datetime import datetime

# Third-party imports second
from django.db import models
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse

# Local app imports third
from services.gemini import generate_cta
```

**Formatting**
- Use 4 spaces for indentation
- Max line length: 88 characters (Black-style)
- Use double quotes for strings
- Trailing commas in multi-line structures

**Naming Conventions**
- Functions: `snake_case` (e.g., `generate_cta`, `create_order`)
- Classes: `PascalCase` (e.g., `OrderForm`, `LandingPageBuilder`)
- Variables: `snake_case` (e.g., `page_context`, `order_data`)
- Constants: `UPPER_SNAKE_CASE`
- URL names: `snake_case` in templates

**Views**
- Use function-based views
- Return `JsonResponse` for AJAX endpoints
- Separate views by feature

**Models**
- Always define `__str__` method
- Use `related_name` for ForeignKeys
- Use `transaction.atomic()` for complex operations

```python
class Order(models.Model):
    product_name = models.CharField(max_length=200)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order: {self.product_name} - {self.customer_name}"
```

**Error Handling**
- Use try/except for API calls (especially Gemini)
- Return JsonResponse with success flag for AJAX
- Validate all user inputs before database operations

### Templates / HTML

**Template Structure**
- Use Django template inheritance
- Use `{% load static %}` for static files
- Pass version strings for cache busting: `?v={% now "U" %}`
- Use Bootstrap classes for styling

**Arabic Text**
- Project uses Arabic (RTL) - ensure proper text direction
- Use Arabic labels and UI text

### JavaScript

- Use vanilla JavaScript (no frameworks)
- Wrap in `document.addEventListener("DOMContentLoaded", ...)`
- Use `const` and `let`, avoid `var`

### Environment Configuration

- Use `python-decouple` for environment variables
- Never commit `.env` file (see `.gitignore`)

## Architecture

**App Structure**
```
core/               # Project settings
frontend/           # Landing page templates and views
services/           # Gemini API integration and page builder
```

**Key Patterns**
- Service layer for AI integration
- Template-based page generation
- Local storage of orders using Django models

## Dependencies

See `requirements.txt`:
- Django
- python-decouple
- djlint
- Google Gemini API integration

## Testing Guidelines

- Place tests in `<app>/tests.py`
- Test model methods and view responses
- Test API integration
- Run single test: `python manage.py test app.tests.TestClass.test_method`

## Development Guidelines 

you need to strictly apply those rules and guidelines:
- always use the components in `dashboard/templates/components/custom_select.html` instead of generic select tags 
- always use `dashboard/templates/components/pagination.html` with list views
- always add the `.form` class to forms unless i said the opposite
- always use the `partials/errorList.html` to deal with `form.form` errors
- always use the `{% block <block-name> %}` and `{% endblock <block-name> %}` to define blocks 
- always send me a system level notification when you finish a task
- always keep the brand consistency based on `frontend/static/css/index.css`
- no need to include the same color pallete each time, you must use `frontend/static/css/index.css` only
- always be creative with your design 
- always separate the js and css from the template files
- always form bootstrap's form controls
- its a multi-language website so always use the internalization framework in temmplates and views
- while writing CSS codes, always write it for `[dir="ltr"]` and `[dir="rtl"]`
- always write the helper functions in `<app-name>/utils.py`
- all imports must be at the top of the python file 
- use `textChoice` class when writing choices fields 
- you must always use sweetalert for confirmation when deleting/updating an object
- always use AJAX instead of standard form redirects for object actions (delete, update, approve, etc.) to provide dynamic and translatable SweetAlert responses
