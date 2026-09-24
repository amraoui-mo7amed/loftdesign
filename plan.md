# Plan — Mobile 3D Scan Integration (StoreBilnov)

> Source : `Cahier_des_charges_StoreBilnov_Scan_3D.docx` (v1.0, 13/08/2026)
> Goal : let a supplier scan a real object with their phone (guided photos or import), automatically get a real-scale 3D GLB model, preview it (3D + AR) and attach it to the StoreBilnov product page.

---

## 1. Current state (codebase audit)

| Element | Current state | Impact |
|---|---|---|
| Stack | Django 5.2.5, PostgreSQL 15, Daphne (ASGI), Redis, Whitenoise | OK |
| Realtime | `django-eventstream` (SSE) already configured + Redis | Reuse for job progress |
| `Product` model | `dashboard/models.py` already has `model_3d` (FileField GLB/GLTF) | Final field exists; attach published asset here |
| 3D viewer | `frontend/templates/products/product_viewer_3d.html` + `<model-viewer>` + CSS `product_viewer.css` | Reuse/extend for AR + dimensions |
| Upload | `dashboard/static/js/products.js` / `product_create.js` validate GLB/GLTF | Extend for source photos + multipart |
| Job queue | **None** (no Celery/RQ) | To introduce (Redis already present) |
| Roles | `UserProfile.roleChoices`: admin, provider, affiliate, semi_affiliate, professional_client, final_client | Mapping: Supplier→`provider`, Bilnov architect→`professional_client`, Visitor→`final_client` |
| i18n | `LANGUAGES = (en, fr)` + `LocaleMiddleware` + `trans`/`_()` | All new text via i18n; RTL support |
| Storage | `FileSystemStorage` local (`media/`) | OK for dev; `STORAGES` abstraction ready for S3/object storage |
| Dashboard components | `components/custom_select.html`, `components/pagination.html`, `partials/errorList.html` | Mandatory per AGENTS.md conventions |

**Conclusion**: the foundation is sound. The bulk of the work is a **new `scans` module** (models, workflow, async pipeline, mobile capture, admin) + **wiring into the existing viewer**.

---

## 2. Architecture decisions

### 2.1 New Django app: `scans`
- Dedicated app: the spec isolates this feature; we don't touch `dashboard/` (already dense). `scans` owns its models, urls, views, utils, templates, static.
- Add `"scans"` to `INSTALLED_APPS` in `core/settings.py`.

### 2.2 Job queue: `django-rq` (Redis already present)
- Add `django-rq` to `requirements.txt` + `RQ_QUEUES` pointing at the existing Redis (`REDIS_HOST`/`REDIS_PORT`).
- New `worker` service in `docker-compose.dev.yml` (and `docker-compose.yml`): `python manage.py rqworker default`.
- Reconstruction jobs (pipeline stages 1→9) are enqueued on `default`; progress/polling via `django-eventstream` (SSE) — already in place.
- Documented alternative if needed later: Celery. Not chosen for V1 (overkill, Redis already here).

### 2.3 Reconstruction engine abstraction (`scans/engine/`)
Aligned with spec §12. Logical interface:
```
submit_job(scan, options) -> provider_job_id
get_status(provider_job_id) -> {stage, percent, message, error_code, retryable}
fetch_result(provider_job_id) -> asset_files
cancel_job(provider_job_id)
```
- `scans/engine/base.py`: abstract class + internal error codes.
- `scans/engine/simulator.py`: **mock** engine for development/acceptance (builds a trivial GLB from images, simulates stages + progress). Used when `SCAN_ENGINE=simulator` (default in dev).
- `scans/engine/<provider>.py`: adapter to the real engine(s) chosen for V1 (to decide: Polycam / Replicate Meshroom / third-party photogrammetry service). **Never expose secrets on the client** (§12).
- Selected via `SCAN_ENGINE` env var (decoupled, see spec §22.1).

### 2.4 Storage
- **Private**: source photos → `media/scans/sources/<scan_id>/` (not served by default, signed URLs).
- **Public**: GLB/thumbs assets → `media/scans/assets/<scan_id>/` served normally once `PUBLISHED`.
- Keep the **master** separate from the **Web version** (§8.3): `ModelAsset.type = master|web|usdz|thumbnail`.
- `scans/utils.py`: helpers — `signed_private_url(...)`, `validate_image_upload(...)`, `generate_storage_key(...)`, `build_bbox_dimensions(...)`, `normalize_errors(...)` (AGENTS convention: helpers in `<app>/utils.py`).

### 2.5 State machine
Statuses of §7 implemented via `TextChoices` on `Product3DScan.status` with an **allowed transition table** in `scans/validators.py` (or a `ScanStateMachine` class). Every transition logged in `ScanAuditEvent` (§7: timestamp, previous status, new status, actor, error code).

---

## 3. Data model (`scans/models.py`)

Direct mapping of §11, adapted to Django + our existing `Product`/`User`.

### `Product3DScan`
| Field | Django type | Note |
|---|---|---|
| `product` | FK → `dashboard.Product` (related_name=`scans`) | Versioning: a product has many scans |
| `owner` | FK → `settings.AUTH_USER_MODEL` (related_name=`scans`) | Owning supplier |
| `status` | TextChoices (DRAFT→ARCHIVED of §7) | State machine |
| `capture_mode` | TextChoices: `guided` / `import` / `depth` | |
| `dimensions` | OneToOne → `ScanDimensions` | |
| `approved_at`, `published_at`, `created_at`, `updated_at` | DateTime | |

### `ScanSource` (source photos)
`scan` FK, `storage_key`, `mime_type`, `size`, `width`, `height`, `checksum`, `quality_flags` (JSON), `order`.

### `ScanDimensions`
`scan` OneToOne, `width/height/depth` (Decimal), `unit` (mm/cm/m, `TextChoices`), `scale_factor` (Decimal), `validated_by` FK, `validated_at`. **Rule §5**: publication impossible without a validated `scale_factor` → error `SCALE_MISSING`.

### `ProcessingJob`
`scan` FK, `engine` (str), `engine_version`, `provider_job_id`, `status` (queued/processing/succeeded/failed/cancelled), `stage`, `percent`, `error_code`, `error_message`, `started_at`, `finished_at`.

### `ModelAsset`
`scan` FK, `type` (master/web/usdz/thumbnail), `format` (glb/usdz/obj/fbx), `storage_key`, `size`, `polygon_count`, `texture_info` (JSON), `version` (int), `is_current` (bool). → attached to `Product.model_3d` only at publication (`is_current=True`, version incremented).

### `QualityReport`
`scan` OneToOne, `score` (Decimal), `warnings` (JSON), `missing_coverage`, `geometry_issues`, `texture_issues` (JSON), `generated_at`.

### `ScanAuditEvent`
`entity_id`, `actor` FK (nullable, service possible), `action`, `metadata` (JSON), `created_at`. Also used for sensitive admin actions (§2.1, §14).

### `ScanQuotaUsage` (P2, quota)
`owner` FK, `period` (YYYY-MM), `scans_used`, `storage_bytes`. Reserved for quota (§15).

---

## 4. Endpoints / Views (mapping §10 to Django)

App `scans`, `app_name = "scans"`. All views **function-based** (project convention), JSON/AJAX, `@login_required`, ownership check (`owner == request.user` or `is_staff`).

| Spec | Django URL | View | Role |
|---|---|---|---|
| POST `/products/{id}/3d-scans` | `POST products/<int:product_pk>/scan/create/` | `scan_create` | provider/owner |
| GET `/3d-scans/{scanId}` | `scans/<int:pk>/status/` (JSON) | `scan_status` | owner/admin |
| POST `/3d-scans/{scanId}/uploads` | `scans/<int:pk>/uploads/` | `source_upload` (resumable multipart) | owner |
| POST `/3d-scans/{scanId}/complete-upload` | `scans/<int:pk>/complete-upload/` | `source_complete_upload` | owner |
| PATCH `/3d-scans/{scanId}/dimensions` | `scans/<int:pk>/dimensions/` | `dimensions_save` | owner |
| POST `/3d-scans/{scanId}/process` | `scans/<int:pk>/process/` | `scan_process` (enqueue RQ job) | owner/admin |
| POST `/3d-scans/{scanId}/cancel` | `scans/<int:pk>/cancel/` | `scan_cancel` | owner/admin |
| POST `/3d-scans/{scanId}/approve` | `scans/<int:pk>/approve/` | `scan_approve` | admin |
| POST `/3d-scans/{scanId}/publish` | `scans/<int:pk>/publish/` | `scan_publish` (copy asset → `Product.model_3d`) | admin |
| POST `/3d-scans/{scanId}/retry` | `scans/<int:pk>/retry/` | `scan_retry` | owner/admin |
| DELETE `/3d-scans/{scanId}` | `POST scans/<int:pk>/archive/` | `scan_archive` (soft archive, §10 DELETE) | owner/admin |
| — (admin) | `scans/` (admin list, filters) + `scans/<int:pk>/detail/` | `scan_admin_list`, `scan_admin_detail` | admin |

**Conventions applied**: SweetAlert + AJAX for all object actions (approve/retry/cancel/archive/publish); translatable responses via i18n (AGENTS.md).

---

## 5. Async pipeline (`scans/tasks.py`)

RQ orchestration (`@job("default")`) of the §6 chain:

```
run_scan_pipeline(scan_id):
  QUEUED -> PROCESSING
  stage 1  ingestion  (validate sources, checksum, MIME, dims)   §16
  stage 2  preprocess (orientation/normalisation)
  stage 3  segmentation (if provided by engine)
  stage 4  reconstruction  -> engine.submit_job()
  stage 5  cleanup
  stage 6  textures
  stage 7  scale  (apply scale_factor)                           §5.1
  stage 8  optimize (configurable weight limit, texture LOD)     §8.3
  stage 9  export   (GLB web + keep master)
  stage 10 QA       -> QualityReport (score, warnings)           §6
  stage 11 -> QUALITY_CHECK -> READY_FOR_REVIEW
```

- Progress pushed via `django_eventstream.send_event` on each `stage`/`percent` change → the front end listens on `scans/<pk>/events/`.
- Errors: normalized to internal codes (§13), `retryable` flag, timeout + limited retries + idempotence (§12).
- A **new generation** of the same product creates a **new scan** and a **new asset version**; the old one is never overwritten (§19, §18 versioning).

---

## 6. Mobile capture module (PWA, `scans/templates/scans/` + `scans/static/scans/`)

Approach: **Web (PWA)** smartphone-compatible — no native app in V1. Camera via `navigator.mediaDevices.getUserMedia` (photos taken client-side then uploaded) or `<input type="file" capture="environment">`.

### 6.1 Screens
1. `scan_create.html` — entry point « Create my 3D model » from the product page.
2. `scan_capture.html` — **guided photo** mode (§4.2):
   - Circular guide showing angular coverage percentage around the object.
   - Valid/recommended images counter (threshold **configurable server-side**, §4.3: `SCAN_MIN_IMAGES`, `SCAN_MAX_IMAGE_SIZE`).
   - Basic client-side image quality check in JS (`canvas` → blur/too dark/overexposed); alert + retake without restarting the session.
   - Indication of missing angular sectors; contextual tips (« step back », « shoot the top », …).
   - Delete/replace a photo; **draft persistence** (DRAFT persisted server-side at each upload).
3. `scan_dimensions.html` — enter width/height/depth + unit (mm/cm/m), computed bounding box, scale factor (§5).
4. `scan_progress.html` — live tracking (SSE): stage, %, message, retryable errors (§10.1).
5. `scan_preview.html` — GLB preview (reuses existing viewer), quality check, retry/correction, validation.

### 6.2 Import mode
Same workflow as « guided » but multi-file selection from the gallery (V1 mandatory, §3.2).

### 6.3 Depth/LiDAR mode
Architecture planned (`capture_mode=depth`), enabled by device capability (P2).

### 6.4 Front-end conventions
- JS separate in `scans/static/scans/js/*.js`, CSS in `scans/static/scans/css/*.css` (AGENTS: separate JS/CSS from templates).
- Branding reused from `frontend/static/css/index.css` (no new palette).
- CSS written for `[dir="ltr"]` **and** `[dir="rtl"]`.
- Reuse dashboard components (`components/custom_select.html`, `partials/errorList.html`, `components/pagination.html`) for forms/lists.
- SweetAlert for deletions/retakes.

---

## 7. 3D Viewer & AR (improve existing)

Reuse `frontend/templates/products/product_viewer_3d.html` + `<model-viewer>`:
- Display **real dimensions** (from `ScanDimensions`).
- « View in my space » AR button with `ar-modes="scene-viewer webxr quick-look"` **only if supported**; 3D fallback (§9.2).
- Visible loading states + clean fallback when WebGL/WebGPU unavailable (§9.1).
- Material/color variants if matching `ProductItem` (P2).
- « 3D Model » block on product pages `product_detail.html`, `admin_product_detail.html`, `provider_product_detail.html`, `affiliate_product_detail.html`: CTA « Create my 3D model » for the supplier, « View in 3D » for others (§3.1).

---

## 8. Admin interface (`scans/templates/scans/admin/`)

- Scan list: filters status / supplier / product / date / engine / error + `components/pagination.html`.
- Detail: sources, progress, logs (`ScanAuditEvent`), dimensions, assets, quality score.
- Admin actions: retry, cancel, approve, reject, archive, republish (AJAX + SweetAlert).
- Preview before publication.
- Quota/limit configuration: extended `SiteSettings` screen (or `ScanLimits` singleton model): capture thresholds, max upload size, Web model weight, allowed formats, source retention (§14, §4.3).
- Sensitive action journal (deletion, publication, rejection, retry, replacement) → `ScanAuditEvent` (§2.1).

---

## 9. Quotas & subscription (P1)

`ScanQuotaUsage` model + check at session creation and upload:
- Scans per period, concurrent jobs, source weight, source retention, exports, master download (per role) (§15). Values via `SiteSettings`/env config. Counting reused for the « per-supplier consumption » view.

---

## 10. Security & storage (§16)

- Server-side validation: MIME, extension, size, image dimensions (Pillow already present).
- Unpredictable storage names (`generate_storage_key` → UUID).
- Signed/temporary URLs for private sources (helper in `scans/utils.py`, based on `django.core.signing`), never public by default.
- Rate-limiting on uploads and job creation (`scans/utils.py`).
- Validation of generated assets before publication (reject corrupt files) — `ModelAsset` + GLB header check in the pipeline.
- Technical logs without tokens/sensitive paths exposed to the front end.

---

## 11. StoreBilnov → Bilnov integration (§18)

- The product keeps its metadata: `productId`, `modelAssetId`, real dimensions, manufacturer/supplier, reference, price, variants, product-page URL, **model version**.
- **Strict versioning**: an existing Bilnov project never silently changes geometry → every new generation increments `ModelAsset.version`; publication only points `Product.model_3d` at the new version. A future endpoint (`GET /scans/<pk>/assets/` or a dedicated field) supplies asset + metadata to Bilnov consumers.
- Traceability: `product.productId` and `modelAssetId` exposed in the publication response.

---

## 12. i18n / RTL

- All new models, views, templates use `_()` / `{% trans %}` (en + fr configured).
- Capture overlays and viewer tested in `dir="rtl"` (dual-direction CSS required).
- Translatable SweetAlert/AJAX responses.

---

## 13. Dependencies to add

```
django-rq            # job queue (existing Redis)
# (V1 optional) chosen 3D engine provider SDK
```
Nothing else: `<model-viewer>` stays CDN-loaded (already the case), Pillow/Redis/daphne/django-eventstream already installed.

---

## 14. Environment variables (`.env`)

| Variable | Default | Usage |
|---|---|---|
| `SCAN_ENGINE` | `simulator` | Reconstruction engine |
| `SCAN_MIN_IMAGES` | `20` | Minimal photo threshold (configurable) |
| `SCAN_MAX_IMAGE_SIZE` | `20MB` | Max size per image |
| `SCAN_MAX_TOTAL_UPLOAD` | `500MB` | Max session size |
| `SCAN_MODEL_MAX_WEIGHT` | `30MB` | Max Web model weight (§8.3) |
| `SCAN_SOURCE_RETENTION_DAYS` | `30` | Source retention |
| `SCAN_PROVIDER_TIMEOUT` / `SCAN_PROVIDER_MAX_RETRIES` | `300` / `3` | Engine timeout/retries |

---

## 15. Implementation phases

### Phase 0 — Foundations (P0)
- [ ] `scans` app + `INSTALLED_APPS`, `urls.py` wired into `core/urls.py`.
- [ ] §3 models + migrations.
- [ ] `django-rq` + `worker` service in both compose files.
- [ ] `scans/engine/` (base + simulator).
- [ ] `scans/utils.py` (helpers) + `scans/validators.py` (state machine).
- [ ] §4 endpoints (create, upload, dimensions, status, process, cancel, retry, archive).
- [ ] RQ pipeline `scans/tasks.py` (stages 1→11) + SSE progress.

### Phase 1 — User experience (P0)
- [ ] Guided PWA capture (§6): circular guide, counter, image quality, retake, draft.
- [ ] Photo import mode.
- [ ] Dimensions + scale screen (§5).
- [ ] Progress screen (SSE) + preview.
- [ ] « 3D Model » block on product pages + CTA.
- [ ] Improved viewer: dimensions, conditional AR, fallbacks (§7).

### Phase 2 — Administration & reliability (P1)
- [ ] Scan admin: filtered list, detail, actions, journal (§8).
- [ ] Quotas & configurable limits (§9).
- [ ] §13 errors normalized + retry UX.
- [ ] Asset versioning + Bilnov integration (§11).
- [ ] Automated tests + acceptance scenarios (§20 of the spec).
- [ ] Technical documentation (install, env, engine, queue, retry/diagnosis).

### Phase 3 — Evolution (P2/P3)
- [ ] Depth/LiDAR scan, OBJ/FBX exports per need, LOD, material variants, analytics, hybrid AI reconstruction (§23).

---

## 16. V1 acceptance criteria (operational reminder, §19)

1. Create a scan session from a product ✅
2. Multiple photos from mobile + resume after interruption ✅
3. Delete/replace a photo before validation ✅
4. Dimensions entered and persisted ✅
5. Async job without blocking the front end ✅
6. Status + progress displayed ✅
7. Retry after recoverable failure without recreating the product ✅
8. GLB previewable on mobile & desktop ✅
9. Validated scale preserved ✅
10. Published product → 3D action; AR only if supported ✅
11. Admin reviews/acts on errored scans ✅
12. Private files not publicly accessible ✅
13. New generation → new version, old one preserved ✅
14. Logs/errors identify the failing stage ✅