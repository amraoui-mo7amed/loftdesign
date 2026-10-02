# Store Bilnov — API v1

For BILNOV (web), BILNOV Desktop and CAD plugins (SketchUp, Revit, Archicad).
Base URL: `https://store.bilnov.com/api/v1/`. Responses are JSON (UTF-8).

## Authentication

- Catalog reads (`GET /products…`) are public: they only expose public prices,
  stock and design files. A key is optional.
- Writes (`POST /shopping-lists`, `POST /cart/from-shopping-list`) need a key:

```
Authorization: Bearer sb_1a2b3c4d.XXXXXXXXXXXXXXXXXXXXXXXX
```

Create a key on the server (it is shown once):

```
python manage.py api_key create "BILNOV Desktop"
python manage.py api_key list
python manage.py api_key revoke sb_1a2b3c4d
```

An invalid or revoked key gives `401 {"error": "invalid API key"}`. CORS is
open (`Access-Control-Allow-Origin: *`) so the BILNOV web viewer can call the API.

## Identifiers

| Field | Example | Meaning |
|---|---|---|
| `bpid` | `BPID-000000010` | BILNOV Product ID, permanent, never reused |
| `variantId` | `BPID-000000010-V01` | commercial variant (colour, size…) |
| `sku` | `NOR-BGE-01` | supplier reference of a variant |
| `manufacturer.id` | `MFR-00001` | manufacturer |
| `supplierId` | `SUP-00001` | supplier on the Store |
| IFC GUID | `3Hs8JK…` | one placed instance in a project: never a product identity |

Write `bpid` and `variantId` in each object (IFC `Pset_BilnovProduct`,
SketchUp attributes, GLB `extras`): see `GET /products/{bpid}` → `ifcPropertySet`.

## Catalog

### `GET /products`
Query: `q` (text, BPID, Variant ID, SKU, manufacturer reference), `category`
(code `FUR` or name), `format` (`skp`, `ifc`, `glb`, `rfa`…), `updatedSince`
(ISO 8601, for desktop sync), `page`, `pageSize` (max 100).

```json
{"count": 128, "page": 1, "pageSize": 24, "next": "https://…?page=2",
 "results": [{"bpid": "BPID-000000010", "name": "Canapé Nora", "categoryCode": "FUR",
   "manufacturer": {"id": "MFR-00001", "name": "Loft Home"}, "manufacturerReference": "NOR-3P",
   "supplierId": "SUP-00001", "price": {"dzd": 149000.0, "eur": 990.0}, "available": true,
   "modelVersion": 2, "storeUrl": "https://store.bilnov.com/store/product/BPID-000000010/"}]}
```

### `GET /products/{bpid}`
Summary + `description`, `variants`, current `assets`, `ifcPropertySet`.

### `GET /products/{bpid}/variants`
`[{variantId, sku, manufacturerReference, name, color, dimensions, stock}]`

### `GET /products/{bpid}/assets` (`?all=1` for every version)
```json
{"bpid": "BPID-000000010", "modelVersion": 2, "assets": [
 {"format": "skp", "version": 2, "current": true, "variantId": null, "url": "https://…/canape-nora.skp",
  "unit": "cm", "scale": "1:1", "polygons": 48200, "size": 2400000,
  "sha256": "9f2c…", "compatibility": "SketchUp 2021+", "date": "2026-10-02T12:00:00+00:00"}]}
```
Compare `sha256` (or `version`) with the file already in the project to show
"Update available". Never replace a placed object automatically.

### `GET /products/{bpid}/availability`, `GET /products/{bpid}/price`
Stock per variant; public retail price in DZD and EUR.

Unknown BPID → `404 {"error": "not found"}`.

## Shopping lists

### `POST /shopping-lists` (key required)
Create a list from a BILNOV project or a desktop scene.

```json
{"name": "Villa Hydra", "client": "M. Hamidi", "ownerRole": "architect",
 "bilnovProjectId": "PRJ-42", "budget": 2500000,
 "rooms": [{"name": "Salon", "budget": 900000}],
 "items": [{"bpid": "BPID-000000010", "variantId": "BPID-000000010-V01", "quantity": 1,
            "room": "Salon", "note": "Mur nord"}]}
```

`201` returns the list (below) plus `editUrl` (private edit link to open in
the browser) and `rejected` (lines whose BPID is unknown, with the reason).
Lines are created with status `proposed_architect` (or `proposed_client`).

### `GET /shopping-lists/{id}`
```json
{"id": "V2Y8PCVX", "name": "Villa Hydra", "status": "shared", "ownerRole": "architect",
 "bilnovProjectId": "PRJ-42", "budget": 2500000.0, "rooms": [{"name": "Salon", "budget": 900000.0}],
 "items": [{"id": 12, "bpid": "BPID-000000010", "variantId": "BPID-000000010-V01", "name": "…",
   "room": "Salon", "quantity": 1, "status": "accepted", "availability": "available",
   "price": {"snapshot": 149000.0, "current": 155000.0, "snapshotAt": "…"}, "replacedBy": null}],
 "url": "https://store.bilnov.com/list/V2Y8PCVX/", "updatedAt": "…"}
```
`availability`: `available`, `low` (less than the quantity), `out_of_stock`,
`unavailable` (no longer sold). `status`: `proposed_client`,
`proposed_architect`, `to_discuss`, `accepted`, `refused`, `replaced`,
`integrated`, `validated`. The snapshot price is the price when the line was
added; `current` is today's price.

### `POST /cart/from-shopping-list` (key required)
`{"id": "V2Y8PCVX"}` → `{"cartUrl": "https://…/list/V2Y8PCVX/cart/?t=…", "lines": 3,
"total": {"dzd": 412000.0}, "expiresInDays": 7}`. Open `cartUrl` in the user's
browser: the cart is filled with the lines still counting and available, at
today's price, and the user checks out on the Store.

## Legacy

`/api/catalog/…` (products, search, `POST bim/resolve`) stays available; see
`BILNOV-REFERENTIEL.md`.
