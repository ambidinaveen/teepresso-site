# UPI Payments — How to add your business UPI ID **safely**

This guide explains, in plain English, how customer UPI payments flow to **your**
business account, and exactly how to plug in your real UPI ID so that money is
always collected safely.

> **TL;DR** — Your UPI ID lives in **server config (an environment variable)**,
> never in the page or the customer's hands. The amount is always calculated on
> the server. The order is **never** auto-marked "paid": a staff member confirms
> the money actually arrived before the order is fulfilled. That combination is
> what makes it safe.

---

## 1. What a "UPI ID" actually is

A **UPI ID / VPA** (Virtual Payment Address) looks like an email address:

```
yourbusiness@okhdfcbank
teepresso@okicici
9999999999@ybl
```

Important facts:

- A VPA is a **"receive money" handle**. It is **not a secret** — it's fine for it
  to appear on a QR code or an invoice. (It's public, like your email or shop
  address.)
- Knowing your VPA lets someone **send you money**. It does **not** let them
  withdraw money or see your balance.
- The risk is **not** "someone learns the VPA". The risks are:
  1. **Substitution** — a bad actor swaps your VPA for theirs so payments go to
     them instead of you.
  2. **Under-payment / fake claims** — a customer pays ₹1 (or nothing) but claims
     to have paid the full amount, and the order ships anyway.

This project is built to prevent both. See §4.

---

## 2. How the payment flows in this app

```
Customer at /pay/<order_no>/
        │
        │  sees a QR + PhonePe / GPay / Paytm / "Any UPI app" buttons + your VPA
        ▼
Pays YOUR business VPA from their own UPI app  (money → your bank)
        │
        │  enters the 12-digit UPI reference (UTR) → "I've paid"
        ▼
Payment row saved as  status = "Awaiting verification"   (order NOT paid yet)
        │
        ▼
Staff opens Dashboard → Order → checks bank/UPI statement for that amount/UTR
        │
        ▼
Clicks "Verify & mark paid"  →  order becomes PAID + CONFIRMED
```

The customer-facing UPI ID / QR / app buttons are all generated **server-side**
from your configured VPA, so the customer can never influence where the money
goes or how much is requested.

The relevant code:

| Concern | File |
| --- | --- |
| Where your VPA is read from | `config/settings.py` → `BUSINESS_UPI` |
| UPI link + QR builders | `payments/service.py` → `upi_uri`, `upi_app_links`, `upi_qr_data_uri` |
| Customer submits UTR (no auto-paid) | `payments/views.py` → `upi_confirm` + `record_upi_submission` |
| Staff verifies & marks paid | `dashboard/views.py` → `order_detail` (`action == "verify_payment"`) |

---

## 3. Adding your real UPI ID (step by step)

### Step 3.1 — Get a business UPI ID
Open a **current/business bank account** or a business app (PhonePe for Business,
Paytm for Business, BharatPe, Google Pay, etc.) and note the VPA it gives you,
e.g. `yourbrand@okhdfcbank`. Prefer a **verified merchant** VPA — merchant VPAs
show your registered business name to the payer, which builds trust and reduces
substitution fraud.

### Step 3.2 — Put it in the environment (NOT in code)
Never hard-code the VPA in a template or commit it into a public place where it
could be edited without review. Set it as an environment variable.

**Local (PowerShell), just to try it:**
```powershell
$env:BUSINESS_UPI_VPA = "yourbrand@okhdfcbank"
$env:BUSINESS_UPI_NAME = "Your Brand Pvt Ltd"
python manage.py runserver
```

**Docker / production — add to your `.env` file:**
```dotenv
UPI=1
BUSINESS_UPI_VPA=yourbrand@okhdfcbank
BUSINESS_UPI_NAME=Your Brand Pvt Ltd
# BUSINESS_UPI_MCC=5945     # optional merchant category code
```

That's it. The demo-VPA warning banner disappears automatically once the value is
no longer the placeholder `teepresso@upi`, and the QR + app buttons now point to
your account.

> **Why an env var and not the database or the page?** So the destination account
> can only be changed by someone with server access (a deliberate, reviewable
> deploy) — never by a customer, and never by tampering with the web page.

### Step 3.3 (Recommended) — Verify with a ₹1 test
Place a test order, scan the QR, pay ₹1 to yourself, and confirm the money lands
in the **correct** account. Then refund yourself. Only after this should you take
real orders.

---

## 4. Why this is safe — the guarantees

1. **The destination account is fixed on the server.** The VPA comes from
   `settings.BUSINESS_UPI["VPA"]` (an env var). It is inserted into the UPI link
   and QR server-side. A customer editing the page or the link **cannot** redirect
   the money to another account — they'd only be editing their own copy of a link
   that still shows *your* `pa=` VPA when they actually open their UPI app against
   the QR you rendered.
2. **The amount is server-computed.** `am=` is taken from `order.total`, not from
   any form field. Even if someone crafts a link that requests ₹1, they've simply
   under-paid — which brings us to point 3.
3. **Orders are never auto-marked paid.** Submitting a UTR only sets the payment to
   *"Awaiting verification"* and the order to *"Payment pending"*. A human confirms
   the money actually arrived (matching amount + UTR on your bank/UPI statement)
   before clicking **Verify & mark paid**. So a fake or partial payment claim
   never results in a shipped order.
4. **No secrets in the browser.** Only the public VPA is ever sent to the client.
   Gateway secrets (Razorpay key secret, webhook secret) stay in env vars on the
   server and are never rendered into a page.
5. **HTTPS in production.** With `DJANGO_DEBUG=0`, the app forces HTTPS, secure
   cookies and HSTS (see `config/settings.py`), so the page and QR can't be
   tampered with in transit.

---

## 5. Stronger / automated options (optional)

The manual-verify flow above needs no gateway and no fees, but a person must
confirm each payment. If you want **automatic, cryptographically-verified**
confirmation, turn on a gateway instead of (or alongside) direct UPI:

- **Razorpay** is already wired in. Set `RAZORPAY=1`, `RAZORPAY_KEY_ID`,
  `RAZORPAY_KEY_SECRET` in your `.env`. Razorpay handles UPI/cards/net-banking and
  returns a **signed** confirmation that the server verifies
  (`payments/service.py → verify_signature`) before marking the order paid — no
  human step needed.
- For direct-UPI **auto-verification** without Razorpay, you'd integrate a UPI
  collect/PSP API (e.g. via your bank or an aggregator) and confirm payments from
  their **server-to-server webhook** — never from the browser. The same rule
  applies: only mark an order paid from a verified server callback.

> Do **not** try to auto-confirm a UPI payment purely from what the customer's
> browser reports. A browser claim is not proof of payment.

---

## 6. Quick checklist before going live

- [ ] `BUSINESS_UPI_VPA` set to your **real** VPA (banner gone, demo VPA replaced).
- [ ] `BUSINESS_UPI_NAME` set to your registered business name.
- [ ] Did a ₹1 test — money reached the **correct** account.
- [ ] Staff know to **verify against the bank/UPI statement** before "Verify & mark paid".
- [ ] `DJANGO_DEBUG=0` and HTTPS enabled in production.
- [ ] Gateway secrets (if using Razorpay) are in env vars, not in code.
