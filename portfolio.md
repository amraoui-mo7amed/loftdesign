# Portfolio Feature — Recreation Spec

## 1. Models (`dashboard/models.py`)

### Portfolio

```python
class Portfolio(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    thumbnail = models.ImageField(upload_to="portfolio/thumbnails/", verbose_name=_("Thumbnail"))
    description = models.TextField(verbose_name=_("Description"))
    tags = models.CharField(max_length=10000, verbose_name=_("Tags"), help_text=_("Comma separated tags"))
    external_link = models.URLField(verbose_name=_("External Link"), blank=True, null=True)
    is_featured = models.BooleanField(default=False, verbose_name=_("Is Featured"))
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = _("Portfolio")
        verbose_name_plural = _("Portfolios")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
```

### PortfolioGallery

```python
class PortfolioGallery(models.Model):
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="gallery_images",
        verbose_name=_("Portfolio")
    )
    image = models.ImageField(upload_to="portfolio/gallery/", verbose_name=_("Image"))

    class Meta:
        verbose_name = _("Portfolio Image")
        verbose_name_plural = _("Portfolio Images")

    def __str__(self):
        return f"Image for {self.portfolio.title}"
```

After creating, run: `python manage.py makemigrations && python manage.py migrate`

---

## 2. Dashboard Views (`dashboard/views/portfolio.py`)

All views protected by `@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])`.

### `portfolio_list(request)`
- Fetch all `Portfolio.objects.all().order_by("-created_at")`
- Support `?q=` search (title__icontains)
- Paginate at 10 per page
- Render `portfolio/list.html` with `page_obj`, `query`, `title`

### `portfolio_create(request)`
- GET: Render `portfolio/create.html`
- POST (AJAX): 
  - Read: `title`, `description`, `tags`, `thumbnail` (file), `external_link`, `is_featured`
  - Read gallery from `request.FILES.getlist("gallery_images")`
  - `transaction.atomic()` → save Portfolio → create PortfolioGallery for each image
  - Return JSON `{success, message, redirect_url}`

### `portfolio_update(request, pk)`
- GET: Render `portfolio/edit.html` with portfolio instance
- POST (AJAX): Update fields, handle thumbnail replacement, delete images from `delete_images[]` POST param, add new gallery images

### `portfolio_delete(request, pk)`
- POST only (AJAX)
- `portfolio.delete()` → return JSON `{success, message}`

---

## 3. Dashboard URLs (`dashboard/urls.py`)

```python
path("portfolio/", portfolio.portfolio_list, name="portfolio_list"),
path("portfolio/create/", portfolio.portfolio_create, name="portfolio_create"),
path("portfolio/<int:pk>/update/", portfolio.portfolio_update, name="portfolio_update"),
path("portfolio/<int:pk>/delete/", portfolio.portfolio_delete, name="portfolio_delete"),
```

---

## 4. Dashboard Templates (`dashboard/templates/portfolio/`)

All extend `dash/dash_index.html`. Use AOS animations. CSS: `portfolio.css`. JS: `portfolio.js` + SweetAlert2.

### `list.html`
- Header: "Portfolios" + "New Masterpiece" button
- Search input `?q=` with clear
- Card grid: thumbnail, title, description (trunc 120), tags, date, photo count, edit/delete buttons
- Delete uses `data-delete-url` + `data-swal-*` attrs + SweetAlert
- Empty state, pagination component

### `create.html`
- Two-column: Left (col-8) = General Info (title, desc, tags) + Gallery (file drop zone); Right (col-4) = Thumbnail drop zone + External link + Featured toggle + Actions
- Form: `enctype="multipart/form-data" class="form" id="portfolioForm"`

### `edit.html`
- Same layout as create
- Shows existing gallery images with `delete_images[]` checkboxes
- Shows current thumbnail with replace option
- Shows "Last updated"

---

## 5. Frontend Views (`frontend/views/portfolio.py`)

### `portfolio_list(request)`
- `Portfolio.objects.all()` → render `portfolio/portfolio_list.html`

### `portfolio_detail(request, pk)`
- `get_object_or_404(Portfolio, pk=pk)` → render `portfolio/portfolio_detail.html`

---

## 6. Frontend URLs (`frontend/urls.py`)

```python
path("portfolio/", portfolio.portfolio_list, name="portfolio_list"),
path("portfolio/<int:pk>/", portfolio.portfolio_detail, name="portfolio_detail"),
```

---

## 7. Frontend Templates

### `frontend/templates/portfolio/portfolio_list.html`
- Extends `index.html`
- Grid of portfolio cards via `partials/portfolio_card.html`
- CSS: `home.css`, `portfolio_list.css`. JS: `portfolio_list.js`

### `frontend/templates/portfolio/portfolio_detail.html`
- Extends `index.html`
- Fullscreen viewer (hero image + prev/next), thumb strip, action buttons (back, details modal, 360)
- Details modal with title, description, tags, date, contact
- CSS: `home.css`, `portfolio_list.css`, `portfolio_detail.css`. JS: `portfolio_detail.js`

### `frontend/templates/partials/portfolio_card.html`
- Reusable card: thumbnail (or default fallback), "View Projects" button → `frontend:portfolio_detail`

---

## 8. Static Files

### Dashboard CSS (`dashboard/static/css/portfolio.css`) — ~242 lines
- `.editorial-item` / `.editorial-img-container` / `.editorial-content` / `.editorial-meta` / `.editorial-tags` / `.editorial-actions`
- `.editorial-btn` / `.editorial-btn-delete` — action buttons
- `.vr-badge-icon` — 360 overlay
- `.file-drop-zone` — drag-and-drop upload
- `.preview-grid` / `.preview-item` — gallery previews
- `.existing-image-wrapper` / `.delete-checkbox-overlay` — update view gallery mgmt
- Full RTL via `[dir="rtl"]`

### Dashboard JS (`dashboard/static/js/portfolio.js`) — ~263 lines
- `compressImage(file, maxW, maxH, quality, callback)` — canvas compression (1920×1080, JPEG 0.7)
- Thumbnail preview + auto-compress >1MB
- Multi-file gallery preview with per-image compression
- Drop zone: click-to-browse + drag-and-drop
- AJAX delete via SweetAlert2 (`data-delete-url`, `data-delete-name`, `data-swal-*`)
- Quantity/Active toggle (qty ≤ 0 → deactivate)

### Frontend CSS (`frontend/static/css/portfolio_list.css`) — ~300 lines
- Neo-brutalist cards (`.brutalist-card`, `.brutalist-img`)
- Fullscreen viewer (`.viewer-container`, `.viewer-main-img`, `.viewer-nav`, `.nav-btn`)
- Floating buttons (`.fixed-360-btn`, `.details-trigger-btn`)
- Detail card (`.product-details-card`, `.product-spec-box`)
- Scroll reveal (`.scroll-reveal`)
- RTL support

### Frontend CSS (`frontend/static/css/portfolio_detail.css`) — ~207 lines
- Full-viewport dark viewer (`.viewer-container`, `.viewer-main-img`)
- Action buttons with backdrop-filter (`.viewer-actions`)
- Thumb strip (`.thumb-strip`, `.thumb-item`)
- Responsive (991.98px, 575.98px)
- RTL support

### Frontend JS (`frontend/static/js/portfolio_list.js`) — ~63 lines
- Image viewer: prev/next nav, fade transition (300ms), active thumb scroll
- Scroll reveal: add `.active` to `.scroll-reveal` on viewport entry

### Frontend JS (`frontend/static/js/portfolio_detail.js`) — ~63 lines
- Image viewer (same as list)
- Modal: clone `#project-details` into `#detailsModalBody` on show

---

## 9. Navigation

### Dashboard Sidebar (`dashboard/context_processors.py`)
Inside `if is_admin:` block:
```python
{"title": _("Portfolio"), "icon": "fas fa-briefcase", "url_name": "dash:portfolio_list"}
```

### Landing Nav (`frontend/templates/partials/landing-nav.html`)
```html
<li class="nav-item">
    <a class="nav-link fw-bold" href="{% url 'frontend:home' %}#portfolio">{% trans "Portfolio" %}</a>
</li>
```

### Homepage Inline Nav (`frontend/templates/home.html`)
```html
<li class="nav-item">
    <a class="nav-link fw-bold" href="{% url 'frontend:portfolio_list' %}">{% trans "Portfolio" %}</a>
</li>
```

---

## 10. Homepage Integration

In `frontend/views/main.py:home_view`:
```python
from dashboard.models import Portfolio
latest_portfolios = Portfolio.objects.filter(is_featured=True)[:6]
if not latest_portfolios.exists():
    latest_portfolios = Portfolio.objects.all()[:6]
```

In `frontend/templates/home.html`, `<section id="portfolio">`:
- Show up to 6 `latest_portfolios` as `.category-card` with thumbnail + "View Projects"
- "View All Projects" button → `frontend:portfolio_list`

---

## 11. Dashboard Stats Tag (`dashboard/templatetags/tags.py`)

For providers:
```python
{"title": _("Portfolios"), "value": Portfolio.objects.count(), ...}
```

---

## 12. Implementation Notes

- No Django ModelForms — all manual HTML with AJAX
- No admin.py registration
- No REST API — all AJAX through standard Django views
- Images compressed client-side before upload
- `portfolio.js` and `portfolio.css` from dashboard are also used by products/orders/leads/categories/settings templates (shared utility code like drag-drop, image compression, AJAX delete)
