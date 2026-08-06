# Execution Plan — Provider → Affiliate → Semi-Affiliate system

> Goal: Clone the existing **Admin creates Semi-Affiliate** flow so a **Provider can create Affiliates** (who then already can create Semi-Affiliates), with product-visibility scoping: **provider-created affiliates see only that provider's products**, and **semi-affiliates of those affiliates see only that affiliate's catalog** (which is inherently only provider products). The provider earns a **network profit** from its own affiliates/semi-affiliates, mirroring how admin (Loft) earns its margin. **Status: implemented — see section 9.**

---

## 1. How the existing admin system works (reference)

| Existing flow | Location | Allows | Behavior |
|---|---|---|---|
| Admin creates Semi-Affiliate | `dashboard/views/users.py:546` `semi_affiliate_create` | `[ADMIN, AFFILIATE]` | AJAX create → `UserProfile(role=SEMI_AFFILIATE, parent_affiliate=<creator>, is_approved=True)`, invite email via password-reset URL (`emails/semi_affiliate_set_password.html`) |
| Affiliate lists Semi-Affiliates | `users.py:654` `semi_affiliate_list` | admin (all) / affiliate (scoped `parent_affiliate=profile`) |
| Admin lists Affiliates | `users.py:430` `affiliate_list` | `[ADMIN]` only | self-registered affiliates waiting for approval |
| Admin approves Affiliate | `users.py:475` `affiliate_approve` | `[ADMIN]` | toggles `is_approved`/`is_active` |
| Available Products (catalog) | `partner_prices.py:89` `affiliate_catalog` | `[AFF, SEMI]` | affiliate sees **all approved products**; semi sees only parent affiliate's `PartnerPrice` catalog |
| Add to My Catalog | `partner_prices.py:171` `affiliate_catalog_add` | `[AFF, SEMI]` | builds `PartnerPrice`; semi's seller = parent affiliate, affiliate's seller = product.user (provider) |

Profit resolution (`dashboard/utils.py` `credit_wallets_for_order`) depends only on **role** + `PartnerPrice`/`LoftPrice` pricing, **NOT** on a `AFFILIATE` profile's `created_by`. So reusing the normal `AFFILIATE` role for provider-created affiliates keeps the profit math untouched.

---

## 2. New workflow

1. A **trusted provider** opens **My Affiliates** in their dashboard and clicks **Create Affiliate** (modal, same pattern as semi-affiliate create).
2. `affiliate_create` (new) creates a `UserProfile(role=AFFILIATE, created_by=<provider_profile>, is_approved=True, approved_at=now)` with `affiliate_code`, `set_unusable_password`, and sends a **new invite email** (`emails/affiliate_set_password.html`) — modeled on `semi_affiliate_set_password.html`.
3. The provider sees their own affiliates on the same `affiliate_list` page (scoped by `created_by`), incl. delete if needed.
4. That affiliate logs in, sees **Available Products** = **only the creating provider's** approved active products (scoped `affiliate_catalog`).
5. The affiliate creates Semi-Affiliates exactly as today (existing `semi_affiliate_create`, no change — they already can).
6. The semi-affiliate's Available Products = the affiliate's catalog (existing behavior) = provider products derived. No change.

---

## 3. Changes — Backend (Python)

### 3a. `dashboard/views/users.py`

- **NEW** `affiliate_create` (mirror `semi_affiliate_create`, line 546):
  - decorator: `@role_required(allowed_roles=[ADMIN, PROVIDER])`
  - validate `first_name`, `last_name`, `email` (unique).
  - `UserProfile(role=AFFILIATE, ...)` — all optional `affiliate_code`, `phone`.
  - **required** `affiliate_code = generate_affiliate_code()`.
  - `is_approved = True`, `approved_at = timezone.now()`. (Decided: provider-created = vouched = pre-approved ✓; no approval step needed.)
  - Send a **password-reset style invitation** so the user can set their password (non-transactional; wraps the account creation in a transaction so a failed **SMTP / email-send exception rolls back**).
  - Email template: `emails/affiliate_set_password.html`.
- **MODIFY** `affiliate_list` (line 430):
  - decorator → `[ADMIN, PROVIDER]`.
  - provider scope: if `is_superuser`: all `role=AFFILIATE`; else (`provider`) `filter(created_by=profile)`.
  - when provider, also show any providers... no — only `created_by=profile`.
- **MODIFY** `send_affiliate_activation_email` / approval: unchanged — provider-created affiliates are pre-approved; the admin `affiliate_approve` remains admin-only and won't affect provider-created ones (they start approved).
- **NEW** `affiliate_delete` (mirror `semi_affiliate_delete`), `[ADMIN, PROVIDER]`, provider may only delete affiliates where `created_by=profile`.

### 3b. `dashboard/views/partner_prices.py` (catalog scoping)

- **MODIFY** `affiliate_catalog` (line 89):
  - For an **AFF rolls** whose `profile.created_by` exists and is a **provider** → restrict `base_qs` to `Product.objects.filter(user=profile.created_by, status=APPROVED, is_active=True)`.
  - Admin-created / self-registered affiliates (created_by=None) keep seeing **all approved products** (unchanged).
  - **Semi-affiliate path unchanged**: still scoped to parent affiliate's `PartnerPrice` catalog. Because the parent affiliate can only see/add provider products, the chain stays consistent.
- **MODIFY** `affiliate_catalog_add` (line 171):
  - Guard: a provider-created affiliate may only add a product if `product.user == profile.created_by`; otherwise return a JSON error ("This product is not available to you").
  - (Semi path unchanged.)
- **MODIFY** `catalog_details` (line ~30-58): apply the same provider scope for AFF when computing `available` list. (Optional; catalog view already gates.)

### 3c. `dashboard/context_processors.py`

- In the **provider** blocked (`is_admin or role == provider and is_trusted`), append a menu item:
  - `{"title": _("My Affiliates"), "icon": "fas fa-user-friends", "url_name": "dash:affiliate_list"}`.

### 3d. `dashboard/urls.py`

- Add routes (affiliates namespace):
  - `path("affiliates/create/", users.affiliate_create, name="affiliate_create")`
  - `path("affiliates/delete/<int:pk>/", users.affiliate_delete, name="affiliate_delete")`
  - `affiliate_list` route unchanged (`dash:affiliate_list`) — decorator now also allows PROVIDER.

---

## 4. Templates & static (JS/CSS)

- **TEMPLATE** `dashboard/templates/users/affiliate_list.html`:
  - Add a **Create Affiliate** button (primary) shown only to provider/admin, opens a modal identical in style to the `semi_affiliate_list.html` create modal (`{% include "components/custom_select.html" %}` / Bootstrap `.form` classes / `{% block ... %}`, translations `{% trans %}`).
  - Add AJAX delete button (`data-url` move to `dash:affiliate_delete`) wired via SweetAlert.
  - Provider sees the grid only of their own affiliates (server-scoped). Admin sees all.
  - The "Approve" button present only for pending; provider-created are always approved.
- **NEW** modal partial `components/affiliate_create_modal.html` (Clone the `semiAffiliateForm` pattern).
- **JS** `dashboard/static/js/affiliate_create.js` — AJAX submit → SweetAlert success/error (translatable), clone `semi_affiliate.js`.
- **EMAIL** `dashboard/templates/emails/affiliate_set_password.html` — clone of `emails/semi_affiliate_set_password.html`, wording "Affiliate" + bilingual (EN/FR).

All CSS uses Bootstrap form control classes + existing `frontend/static/css/index.css` palette. **No** inline palette.

---

## 5. Profit-chain impact

> Superseded by the confirmed profit model in Section 8. The provider now earns a network margin on its own affiliates' sales; see `compute_item_profit`'s provider-network branch.

---

## 6. Verification (manual)

1. Login as provider → "My Affiliates" appears; create an affiliate → SweetAlert success; invite email sent.
2. New affiliate logs in; Available Products = only the creating provider's products.
3. Affiliate creates a Semi-Affiliate (existing flow works).
4. Semi-Affiliate logs in; Available Products = only that affiliate's catalog (provider products); submit order → commission credited without provider cut.
5. Admin `affiliate_list` still lists **all** affiliates; existing admin approve flow intact.

## 7. Open questions for the reviewer

- **A.** Should provider-created affiliates be `is_approved=True` automatically (recommended), or pending until provider approves them separately? => yes. auto approved
- **B.** Should a provider-creating-affiliate be able to also **delete** their own affiliates (recommended: yes)? => yes
- **C.** Invite email — copy `semi_affiliate` pattern with **set-password** link. OK? => yes
- **D.** Keep the existing `affiliate_list` (with region-flags). or give the provider a **separate** `my_affiliates` page? (Recommend reusing `affiliate_list` with role-aware rendering.) => re-use it

## 8. Profit-model decisions (confirmed)

| # | Decision | Value |
|---|---|---|
| 1 | Provider payout per unit | **`provider_wholesale − supplier_base` in total** (network margin replaces supplier share on that leg) |
| 2 | Coverage | Provider earns from **both** its affiliate's direct sales **and** its semi-affiliates' sales |
| 3 | Loft cut | Loft **keeps its commission** (`supplier_base × commission%`) on provider-network legs |
| 4 | Where the provider wholesale is configured | New field **`SupplierPrice.affiliate_wholesale_price`** (set by provider/admin on the product price form) |

## 9. Implementation status

**Backend**
- `dashboard/models.py`: added `SupplierPrice.affiliate_wholesale_price` + `Order.provider_share` (+ migration `0026`).
- `dashboard/utils.py`:
  - `resolve_chain` — detects provider network (affiliate/semi whose `created_by` is the provider who owns the product) and exposes `provider_wholesale`.
  - `compute_item_profit` — new provider-network branch: provider = `(pw − supplier_base)`, Loft = `(supplier_base − actual_supplier_base)` (commission), affiliate = `(aff_base − pw)`, semi = `(retail − aff_base)`; returns `provider_share`.
  - `compute_order_profit` — accumulates + persists `order.provider_share`.
  - `credit_wallets_for_order` — credits provider `provider_share` (combined with supplier share) + updated notifications/breakdown.
- `dashboard/views/partner_prices.py`: `affiliate_catalog` scoped to provider's products for provider-created affiliates; `affiliate_catalog_add` uses `affiliate_wholesale_price` as purchase price + ownership guard; `catalog_details` ownership guard.
- `dashboard/views/users.py`: new `affiliate_create` (`[ADMIN, PROVIDER]`, pre-approved, invite email) + `affiliate_delete` (owner-scoped); `affiliate_list` scoped to `created_by` for providers.
- `dashboard/urls.py`: `affiliates/create/`, `affiliates/<pk>/delete/`.
- `dashboard/context_processors.py`: "My Affiliates" menu item for trusted providers + admins.
- `dashboard/views/products.py`: persists `affiliate_wholesale_price` on SupplierPrice (admin + provider branches).
- `dashboard/views/orders.py`: `provider` field in `order.profit_breakdown`.

**Templates / static**
- `users/affiliate_list.html`: Create Affiliate modal (`affiliateCreateForm`) + delete buttons with translatable SweetAlert data attrs.
- `dashboard/static/js/affiliate_manage.js`: AJAX create + SweetAlert delete.
- `emails/affiliate_set_password.html`: cloned from semi-affiliate (EN/FR), wording "affiliate".
- `products/edit.html`: "Affiliate Wholesale" price field.

**Notes**
- Migration `0026` applied to the dev DB; columns `dashboard_order.provider_share` and `dashboard_supplierprice.affiliate_wholesale_price` verified.
- The running production `web` container runs older code (no bind mount) — it must be rebuilt/restarted for the provider-network logic to be active.
- "My Affiliates" menu shows for trusted providers; non-trusted providers still must be approved/trusted by admin first.