# Fix: "Delivered" order status requires two attempts

## Problem

On `/dashboard/orders/`, marking an order as **Delivered** does not apply on the first
attempt. The page appears to do nothing, and only after reloading and trying again does
the status change to Delivered.

This happens only the **first** time an order is delivered. After a wallet exists in the
database, delivery works on a single attempt.

### Observed behavior

- First click on **Delivered** → nothing visibly happens.
- Reload the page, click **Delivered** again → the status changes normally.

### Root cause

The failure is a **server-side exception** (HTTP 500), not a frontend problem.

When an order is marked Delivered, the view `order_update_status`
(`dashboard/views/orders.py`) runs `credit_wallets_for_order(order)` inside a
`transaction.atomic()` block:

```python
# dashboard/views/orders.py
with transaction.atomic():
    if new_status == Order.OrderStatus.DELIVERED:
        compute_order_profit(order)
        credit_wallets_for_order(order)
    order.save()
```

`credit_wallets_for_order` credits each payee's wallet:

```python
# dashboard/utils.py
wallet, _wcreated = Wallet.objects.get_or_create(user=user)
wallet.balance += amount   # line 595
```

On the very first credit for a user, `get_or_create` builds a brand-new `Wallet`
instance in memory. Because the model field is defined as:

```python
# user_auth/models.py
balance = models.DecimalField(
    _("Balance (DZD)"), max_digits=12, decimal_places=2, default=0.00,
    ...
)
```

…the default `0.00` is a Python **`float`** (`0.0`), not a `Decimal`. Meanwhile
`amount` is a **`Decimal`**. Adding them raises:

```
TypeError: unsupported operand type(s) for +=: 'float' and 'decimal.Decimal'
File "/app/dashboard/utils.py", line 595, in credit_wallets_for_order
    wallet.balance += amount
```

This exception escapes the `transaction.atomic()` block, so **everything rolls back**,
including `order.save()`. The order stays `pending`, and the server returns HTTP 500.

The JS in `dashboard/static/js/orders.js` swallows the failure:

```js
fetch(url, {
    method: 'POST',
    body: new URLSearchParams({ 'status': status }),
    headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' }
})
.then(response => response.json())     // <-- 500 returns HTML, .json() throws
.then(data => {
    if (data.success) {
        window.location.reload();
    }
})
.catch(error => console.error('Error:', error));  // <-- error swallowed silently
```

Because a 500 response is HTML (not JSON), `response.json()` throws, the error is logged
to the console, nothing reloads, and the UI gives no feedback.

### Why the second attempt works

On a subsequent attempt the wallet **already exists** in the database, so
`get_or_create` loads the stored row, whose `balance` is a proper `Decimal` (the value
was normalized on save). `Decimal + Decimal` succeeds, so the delivery goes through.

---

## Solution

### 1. Fix the arithmetic — `dashboard/utils.py` (line 595)

Coerce the balance to `Decimal` before adding, so it works whether the wallet is new
(`0.0` float) or loaded (`Decimal`):

```python
wallet.balance = Decimal(str(wallet.balance or "0")) + amount
```

`Decimal` is already imported at the top of the file (used throughout the module).

### 2. Fix the model default — `user_auth/models.py` (optional but recommended)

Prevent new `Wallet` instances from carrying float values in the first place:

```python
from decimal import Decimal

balance = models.DecimalField(
    _("Balance (DZD)"), max_digits=12, decimal_places=2, default=Decimal("0.00"),
    help_text=_("Available balance that can be withdrawn")
)
pending_balance = models.DecimalField(
    _("Pending Balance (DZD)"), max_digits=12, decimal_places=2, default=Decimal("0.00"),
    help_text=_("Earnings from orders not yet delivered")
)
```

This requires a new migration:

```bash
python manage.py makemigrations user_auth
python manage.py migrate
```

### 3. Improve error feedback — `dashboard/static/js/orders.js`

Replace the silent `.catch` with visible, translatable feedback. On a non-OK HTTP
response or `success: false`, show a SweetAlert with the server message instead of doing
nothing:

```js
document.addEventListener('DOMContentLoaded', () => {
    const statusButtons = document.querySelectorAll('.update-status-btn');
    statusButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            const status = this.getAttribute('data-status');
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

            fetch(url, {
                method: 'POST',
                body: new URLSearchParams({ 'status': status }),
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (ok && data.success) {
                    window.location.reload();
                    return;
                }
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: data.message || 'Could not update the order status.',
                    confirmButtonColor: 'var(--brand-danger)'
                });
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'Network error. Please try again.',
                    confirmButtonColor: 'var(--brand-danger)'
                });
            });
        });
    });
});
```

---

## How to apply

### Locally (development)

```bash
# 1. Edit the files:
#    - dashboard/utils.py        (fix wallet.balance += amount)
#    - user_auth/models.py       (optional: Decimal defaults)
#    - dashboard/static/js/orders.js  (optional: SweetAlert feedback)

# 2. Apply the model migration (only if step 2 was done)
python manage.py makemigrations user_auth
python manage.py migrate

# 3. Verify with the test client
python manage.py shell
```

Quick verification snippet (run inside the project):

```python
from decimal import Decimal
from user_auth.models import Wallet
from django.contrib.auth.models import User

w, created = Wallet.objects.get_or_create(user=User.objects.get(username="admin"))
print(type(w.balance))               # Decimal, not float
w.balance = Decimal(str(w.balance or "0")) + Decimal("100.00")
w.save(update_fields=["balance"])
print(w.balance)
```

### On the Docker deployment

The app runs in a Podman container named `loftdesign_web_1`. The Django code lives at
`/app` inside the container and is copied in via `podman cp`, so edit the files on the
host and copy them over.

```bash
# 1. Copy the edited files into the container
podman cp dashboard/utils.py                 loftdesign_web_1:/app/dashboard/utils.py
podman cp user_auth/models.py                loftdesign_web_1:/app/user_auth/models.py
podman cp dashboard/static/js/orders.js      loftdesign_web_1:/app/dashboard/static/js/orders.js

# 2. Apply migration (only if the model default was changed)
podman exec loftdesign_web_1 python3 manage.py makemigrations user_auth
podman exec loftdesign_web_1 python3 manage.py migrate

# 3. Collect static files so the JS change is served
podman exec loftdesign_web_1 python3 manage.py collectstatic --noinput

# 4. Restart the web container
podman restart loftdesign_web_1
```

### Verify the fix end-to-end

```bash
podman exec loftdesign_web_1 python3 - <<'PY'
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from dashboard.models import Order
from user_auth.models import Wallet, Transaction

c = Client()
c.force_login(User.objects.get(username='admin'))

order = Order.objects.get(pk=1)               # pending order
r = c.post(f'/dashboard/orders/{order.pk}/status/',
           {'status': 'delivered'}, HTTP_HOST='localhost')
print('HTTP', r.status_code)                  # expect 200
print('JSON', r.json())                       # expect success: True

order.refresh_from_db()
print('order.status =', order.status)         # expect 'delivered'

for w in Wallet.objects.all():
    print('wallet', w.user.username, 'balance =', repr(w.balance))  # Decimal

print('transactions =', Transaction.objects.count())  # expect >= 1
PY
```

After the fix, delivering an order succeeds on the **first** attempt, with no page reload
required.

---

## Files touched

| File | Change |
|------|--------|
| `dashboard/utils.py` | Coerce `wallet.balance` to `Decimal` before `+=` (line 595) |
| `user_auth/models.py` | (Optional) `Decimal` defaults for `balance` / `pending_balance` |
| `user_auth/migrations/0008_*.py` | (Optional) Generated migration for the default change |
| `dashboard/static/js/orders.js` | (Optional) SweetAlert error feedback instead of silent `.catch` |
