# OTOG E-Wallet continuation backlog

Prepared 2026-11-09 from a read-only inspection of `F:\OTOG`, local branch `main`.

## What exists

- `README.md`: Java GUI / OOP course project description.
- `Class Diagram/ewallet_cd.png`: Main, User, Wallet, Transaction; CashInOut, SendMoney, InvestMoney, Loan; Security, TwoFactorAuth, Password, Pin.
- `src/UserLogin.java` and `.form`: Swing login UI, password step, and a second verification panel.
- Login checks hardcoded `admin` / `password`. The second step accepts any nonempty input; it does not verify an OTP. Successful verification shows a dialog, without dashboard navigation.
- No source implementations found for the wallet, transfers, cash in/out, investments, loans, or PIN. Treat these as diagrammed / user-reported features pending integration verification, not verified completed functionality. Compiled output contains the login class and GUI Designer support classes.
- No build configuration or test suite found. This is a static review; the app was not run, and remote branches were not fetched.

## Scope and priorities

Assumption: a Java Swing academic demonstration using simulated balances and a mock Bank API. Real provider integration is a separate scope. The tickets below are drafts, not issues submitted to a tracker.

P0 = foundation and correctness; P1 = required use cases; P2 = extensions after core flows work. Each acceptance criterion is also a suggested verification scenario.

## Foundation tickets

### EW-01 — Establish a reproducible build and reconcile existing work
**Priority:** P0. **Dependencies:** none.

As a developer, I can run the project from a clean checkout and identify which modules are implemented.

Acceptance criteria:
- Document JDK, build/run steps, and IntelliJ GUI Designer form compilation or replace the form dependency with ordinary Swing initialization.
- A clean build opens the login screen without uninitialized UI fields.
- Check team branches/contributions for the reported features; record implemented, partial, and missing modules before duplicating work.
- Add a small automated test setup for authentication and transaction services.

### EW-02 — Implement persistent users, wallets, and transactions
**Priority:** P0. **Dependencies:** EW-01.

As a user, my account, balance, and transactions survive an app restart.

Acceptance criteria:
- Persist users, wallet ownership, transactions, and ledger entries with unique IDs and referential integrity.
- Use `BigDecimal` with explicit PHP precision/rounding; reject zero, negative, and invalid payment amounts.
- Track transaction type, status, amount, fee, currency, timestamps, source/destination, and unique request reference.
- Balance changes and their ledger entries commit together or roll back together; reject insufficient available funds and duplicate requests.
- Verify persistence after restart and concurrent attempts to spend the same available funds.

### EW-03 — Replace hardcoded login with registration and authentication
**Priority:** P0. **Dependencies:** EW-02.

As a user, I can register and sign in to my own account.

Acceptance criteria:
- Validate required fields and unique login/mobile identifiers; create one wallet per demo user.
- Store salted password hashes using an established password-hashing library, never plaintext passwords.
- Reject incorrect credentials; enforce configured attempt limits and temporary lockout.
- Restrict authenticated screens until all required authentication steps succeed; logout clears the session.

### EW-04 — Implement actual OTP verification
**Priority:** P0. **Dependencies:** EW-03.

As a user, I must complete a valid second authentication step before accessing my wallet.

Acceptance criteria:
- Replace the nonempty-field check with verification of a generated challenge bound to the pending user/session.
- Enforce expiration, one-time use, attempt limits, and resend cooldown; resending invalidates the previous code.
- Wrong, expired, reused, or another user's code never authenticates the session.
- For the classroom build, use a clearly labeled simulated delivery adapter; do not describe simulated delivery as production 2FA.

### EW-05 — Add transaction PIN and security settings
**Priority:** P0. **Dependencies:** EW-03, EW-04.

As a user, I authorize outgoing payments with a PIN and manage my credentials.

Acceptance criteria:
- Set and change a hashed PIN after reauthentication; enforce failed-attempt lockout.
- Require valid PIN authorization for outgoing transactions; cancel or failure leaves balances unchanged.
- Password/PIN recovery requires a verified recovery challenge, never just an account identifier.
- Add inactivity timeout and invalidate sessions after credential recovery.

### EW-06 — Build the wallet dashboard
**Priority:** P1. **Dependencies:** EW-02, EW-03, EW-04.

As a user, I can see my available balance and navigate the wallet features.

Acceptance criteria:
- Show the current user's balance, recent activity, profile, logout, and navigation to implemented features.
- Refresh balances after completed operations; show loading, empty, and failure states.
- Keep long-running persistence/API operations off Swing's UI thread.

## Core use-case tickets

### EW-07 — Complete send money with atomic transfers
**Priority:** P1. **Dependencies:** EW-02, EW-05, EW-06.

As a user, I can send money to another registered wallet.

Acceptance criteria:
- Validate active recipient, positive amount, available funds including fees, and configured limits; reject self-transfer for this demo.
- Show recipient, amount, fee, and total before PIN confirmation.
- Commit sender debit, recipient credit, ledger entries, and completed status atomically.
- Duplicate clicks/retries create only one transfer; failure creates no partial debit or credit.
- Verify successful transfer, insufficient funds, invalid recipient, and competing transfers.

### EW-08 — Complete cash in/out with a mock Bank API
**Priority:** P1. **Dependencies:** EW-02, EW-05, EW-06.

As a user, I can fund my wallet or withdraw to a linked demo payment method.

Acceptance criteria:
- Add a `PaymentMethod` model and `BankApiClient` interface with a deterministic mock adapter.
- Validate account ownership, method status, amount, fees, and limits before submission.
- Credit cash-in only on confirmed success. Reserve cash-out funds while pending, settle on success, and release on confirmed failure.
- Track provider references; timeout remains pending/unknown until status lookup resolves it.
- Repeated responses/retries do not double-credit or double-debit; exercise success, rejection, timeout, and eventual resolution.

### EW-09 — Add bill payments
**Priority:** P1. **Dependencies:** EW-02, EW-05, EW-08.

As a user, I can pay a supported demo biller.

Acceptance criteria:
- Select a biller, validate subscriber/reference format, enter amount, and review fees before PIN confirmation.
- Create a bill-payment transaction linked to the biller and account reference.
- Handle pending, successful, and failed provider outcomes without duplicate charges; release reserved funds after confirmed failure.
- Show a receipt/reference and preserve the result in transaction history.

### EW-10 — Add merchant QR payments
**Priority:** P1. **Dependencies:** EW-02, EW-05, EW-07.

As a merchant, I can display a payment QR; as a user, I can scan or import it and pay.

Acceptance criteria:
- Add merchant registration/profile and QR generation with merchant identifier, currency, and optional fixed amount.
- Support QR image import for the desktop demo; camera scanning is optional.
- Reject malformed payloads, unknown/inactive merchants, invalid amounts, and unsupported currencies.
- Show merchant identity and final amount before PIN confirmation; complete exactly one wallet transfer per confirmed request.
- Merchant can see received payments. Use a documented project QR format; interoperability with GCash/PayMaya is not implied.

### EW-11 — Add transaction history and receipts
**Priority:** P1. **Dependencies:** EW-02, EW-07; extend to EW-08–10 as delivered.

As a user, I can trace money entering and leaving my wallet.

Acceptance criteria:
- List only authorized wallet activity, with filters for date, type, and status.
- Show transaction ID, counterparty, amount, fee, total, timestamp, and status.
- Provide a printable/exportable receipt with masked account identifiers and no credentials.
- Pending and failed records remain distinguishable from completed payments.

### EW-12 — Add an in-app notification inbox
**Priority:** P1. **Dependencies:** EW-02, EW-07.

As a user or merchant, I receive payment updates.

Acceptance criteria:
- Persist notifications for successful transfers and resolved payment outcomes, linked to the transaction and recipient.
- Notify sender and recipient after commit, not before a balance update succeeds.
- Track read/unread status; failed notification delivery can retry without repeating the financial transaction.
- Keep inbox contents scoped to the signed-in account; email/SMS are optional adapters.

### EW-13 — Add admin access and an audit trail
**Priority:** P1. **Dependencies:** EW-02, EW-03.

As an admin, I can review accounts and transactions and suspend abusive demo accounts.

Acceptance criteria:
- Enforce User/Merchant/Admin permissions in services as well as navigation; ordinary users cannot invoke admin actions directly.
- Search accounts and transactions; suspend/reactivate accounts with recorded reason and timestamp.
- Suspension prevents new payments and is checked again during transaction execution.
- Record administrative and security events without secrets; prohibit deleting financial history or directly editing balances.
- Demonstrate that users cannot read another account's private history or invoke privileged actions.

## Extensions to the diagrammed features

### EW-14 — Complete a simulated loan lifecycle
**Priority:** P2. **Dependencies:** EW-02, EW-05, EW-13.

As a user, I can apply for a demo loan, view a repayment schedule, and repay it.

Acceptance criteria:
- Show principal, configured interest calculation, fees, installment dates, and total repayment before application.
- Admin approval/rejection updates the application; approval disburses once and creates a linked transaction.
- Repayment updates wallet funds and outstanding principal/interest consistently; prevent duplicate disbursement and overpayment.
- Track loan state independently from payment transaction state; demonstrate rejected, active, paid, and overdue cases using simulated time/data.

### EW-15 — Complete simulated investments
**Priority:** P2. **Dependencies:** EW-02, EW-05.

As a user, I can buy and withdraw demo investment holdings.

Acceptance criteria:
- Use seeded products and explicitly simulated prices/returns.
- Preview units, price, fees, and wallet impact before confirmation.
- Persist holdings separately from buy/sell transactions; prevent overselling and insufficient-funds purchases.
- Keep cash and holding updates consistent, and show gain/loss using an explicit valuation timestamp.

### EW-16 — Add saved recipients and request money
**Priority:** P2. **Dependencies:** EW-07, EW-12.

As a user, I can save frequent recipients and request payment from another user.

Acceptance criteria:
- Save/remove recipient aliases; revalidate the current recipient account before payment.
- Requests have pending, paid, declined, canceled, and expired states.
- A request never moves funds without the payer's explicit confirmation and PIN.
- Link a paid request to one successful transfer and prevent payment after closure.

### EW-17 — Add disputes and traceable refunds
**Priority:** P2. **Dependencies:** EW-10, EW-11, EW-13.

As a user, I can report a payment issue; authorized staff can resolve it.

Acceptance criteria:
- Open a case linked to an owned transaction with a reason and visible status.
- Authorized resolution records reviewer, decision, and timestamp.
- A refund creates a compensating transaction, preserving the original; enforce available funding and cumulative refund limits.
- Retry cannot issue a duplicate refund; notify affected accounts.

## Class-diagram changes

Keep `Main` responsible for startup/navigation. Move authentication and payment rules into services so they can be verified without clicking Swing screens.

| Addition/change | Purpose |
|---|---|
| `PaymentMethod`, `BankApiClient`, `MockBankApiClient` | Model external funding/withdrawal and isolate simulated provider behavior. |
| `Notification`, `NotificationService` | Persistent payment updates and delivery retry. |
| `MerchantProfile`, `Role`, admin permissions | Represent the missing Merchant and Admin actors; Bank API is an external interface, not a user subclass. |
| `Biller`, `BillPayment`, `MerchantPayment` | Cover bills and QR use cases. |
| `LedgerEntry`, `TransactionStatus`, `TransactionType` | Trace balance movement and enforce explicit transaction states. |
| `AuthService`, `OtpChallenge`, `Session` | Separate login workflows from stored credentials and views. |
| `WalletService`, `TransferService`, repositories | Centralize validation, atomic persistence, and wallet ownership checks. |
| `LoanAccount`, `LoanApplication`, `RepaymentSchedule` | Model a long-lived loan separately from its disbursement/repayment transactions. |
| `InvestmentProduct`, `InvestmentHolding` | Model holdings separately from purchase/redemption transactions. |
| `AuditEvent` | Record privileged and security actions. |

Add multiplicities: one demo `User` owns one `Wallet`; a wallet has many ledger entries; a transaction has multiple ledger entries; a user has many payment methods and notifications. Each notification may reference a transaction. A transfer references both source and destination wallets, rather than a single ambiguous wallet association.

`Password`, `Pin`, and `TwoFactorAuth` can retain a common verification interface for the OOP exercise, but pass explicit verification context rather than relying on a parameterless `verify()`. Store OTP challenges separately from permanent account settings. Map diagram `decimal` values to Java `BigDecimal`.

## Send-money sequence

1. User enters recipient and amount.
2. Service validates session, ownership, recipient, amount, fees, limits, and available balance.
3. UI presents confirmation; user authorizes with PIN.
4. Service rechecks authorization and balances within the database transaction, then writes the sender debit, recipient credit, ledger entries, and completed transaction using a unique request key.
5. Commit all changes; on failure, roll back all financial changes.
6. Persist/deliver notifications after successful commit, using retryable notification work so a delivery failure cannot repeat the payment.
7. Display receipt and refreshed balances.

## Suggested delivery order

1. Foundation: EW-01–05.
2. First complete demo: EW-06–08, EW-11–12.
3. Complete original actors/use cases: EW-09–10, EW-13.
4. Broader features: EW-14–17.

Definition of done for each implemented ticket: acceptance criteria demonstrated, relevant service tests pass, authorization and failure paths checked, persistence survives restart where applicable, and README/class diagram updated. Prefer completing core payments before expanding loans and investments.
