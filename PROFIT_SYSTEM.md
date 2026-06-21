# Profit System — Loft Design Marketplace

## The Chain

```
Supplier → Loft Design → Affiliate → Semi-Affiliate → Customer
```

Each level charges the next level a (wholesale) price. Profit = `(price_they_charge − price_they_pay) × quantity`.

## Price Sources

| Level | Price Field | Source |
|---|---|---|
| Supplier cost | `supplier_wholesale` | `SupplierPrice.loft_purchase_price` |
| Loft wholesale | `loft_wholesale` | `LoftPrice.loft_default_wholesale_price` |
| Affiliate wholesale | `affiliate_wholesale` | `PartnerPrice.wholesale_price` (seller=admin, buyer=affiliate) |
| Semi wholesale | `semi_wholesale` | `PartnerPrice.wholesale_price` (seller=affiliate, buyer=semi) |
| Customer price | `retail_price_charged` | `PartnerPrice.retail_price` (of the referring partner) |

## Profit Calculation (`compute_item_profit`)

Three cases depending on referral chain depth:

```
                    ┌──────────────┬────────────┬─────────────┬──────────┐
                    │ Supplier     │ Loft       │ Affiliate   │ Semi     │
├────────────────────┼──────────────┼────────────┼─────────────┼──────────┤
│ No referral        │ sup × qty   │ (price − sup) × qty │ 0          │ 0        │
│ Affiliate direct   │ sup × qty   │ (loft − sup) × qty  │ (price − loft) × qty │ 0        │
│ Semi-affiliate     │ sup × qty   │ (loft − sup) × qty  │ (aff − loft) × qty   │ (price − aff) × qty │
└────────────────────┴──────────────┴────────────┴─────────────┴──────────┘
```

Where:
- `sup` = `supplier_wholesale`, `loft` = `loft_wholesale`
- `aff` = `affiliate_wholesale`, `price` = customer's purchase price
- All shares floored at 0 (no negative profits)

## Admin's Two Cases

### Case 1 — Admin creates product himself
No supplier, no wholesale cost. Admin just sets `LoftPrice.loft_default_wholesale_price`.
The order skips validation: `PENDING → SHIPPED / DELIVERED` directly.

### Case 2 — Admin gets product from a supplier
Supplier has a `SupplierPrice` with `loft_purchase_price`. Supplier gets paid at delivery.
Flow: `PENDING → ADMIN_VALIDATED → SUPPLIER_FULFILLING → SHIPPED → DELIVERED`.

## Key Files & Functions

| File | Function | Role |
|---|---|---|
| `dashboard/utils.py:198` | `resolve_chain()` | Traces price chain for a product + referral code |
| `dashboard/utils.py:260` | `compute_item_profit()` | Calculates per-item profit for all 4 levels |
| `dashboard/utils.py:303` | `compute_order_profit()` | Sums per-item profits, stores on Order model |
| `dashboard/utils.py:347` | `credit_wallets_for_order()` | Credits wallets, creates Transaction records, sends notifications |
| `dashboard/views/orders.py:21` | `_admin_transitions_for_order()` | Dynamic admin status transitions (checks for provider) |
| `dashboard/views/orders.py:535` | `order_update_status()` | Triggers profit+wallet on DELIVERED transition |

## Wallet System

- `Wallet.balance` — available for withdrawal
- `Wallet.pending_balance` — earnings from undelivered orders (not actively used yet)
- `Transaction` — records every EARNING, WITHDRAWAL, or ADJUSTMENT

When DELIVERED: wallet balance is credited immediately. Admin can withdraw without approval; affiliates/semi-affiliates require admin approval.

## Margins

Affiliate commission is calculated on the difference between the price charged to the customer and the wholesale price at which the affiliate bought the product from Loft Design. This means:

- **Affiliate margin**: `(customer_price − loft_wholesale) × quantity` (when affiliate refers directly)
- **Semi-affiliate margin**: `(customer_price − affiliate_wholesale) × quantity` (when semi refers)
- **Affiliate margin (via semi)**: `(affiliate_wholesale − loft_wholesale) × quantity` (affiliate's cut when semi sells)
