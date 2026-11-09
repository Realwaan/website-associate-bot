# OTOG E-Wallet: one-month capstone ticket plan

Planning window: November 9-December 8, 2026 (Asia/Manila).
Laboratory presentations: December 9 (F1), December 10 (F2), December 12 (G9).
All sections target readiness on December 8. Feature freeze: November 29. Release candidate: December 4.

## Scope and capacity

Deliver a Java Swing demonstration with User, Merchant, Admin, and a simulated Bank API. Include registration/login, OTP verification with simulated delivery, PIN, dashboard, cash in/out, send money, bill payments, QR payment, history, receipts, and notifications. Include small simulated loan and investment flows because they are part of the team's stated feature set.

The scan found only a login prototype in the current source. Verify any work held by teammates on November 9 before implementing duplicates. These are proposed tickets, not published tracker issues or confirmed assignments.

Assume five contributors based on the README. Assign actual names during kickoff:

| Role | Primary responsibility |
|---|---|
| A | Authentication and security |
| B | Database, wallets, and transaction correctness |
| C | Swing UI, history, notifications, and integration |
| D | Bank simulation, bills, and loans |
| E | Merchant QR, admin, investments, and documentation coordination |

Each owner also tests and documents their work. Integration and presentation are shared responsibilities. Estimates are focused person-days, not elapsed calendar days; this plan budgets about 46 person-days across the team, plus rehearsal. Confirm availability at kickoff. Weekends are buffer, not required working days.

## Weekly milestones

| Period | Outcome | Exit check |
|---|---|---|
| Week 1: Nov 9-15 | Runnable project, persistent models, password login, dashboard scaffold | Register, verify password login and persisted account data; review dashboard scaffold. |
| Week 2: Nov 16-22 | OTP/PIN, integrated dashboard, send money, cash in/out, activity, notifications, admin | Complete authentication, a transfer, and funding cycle; demonstrate rejection without balance corruption. |
| Week 3: Nov 23-29 | Bills, merchant QR, basic loans/investments, integrated demo | Every promised feature works on one shared build; freeze features Nov 29. |
| Week 4: Nov 30-Dec 6 | Regression fixes, diagrams, slides, packaged release | Run the complete demo on the presentation laptop; release candidate Dec 4. |
| Final buffer: Dec 7-8 | Rehearsal and release verification | Two successful rehearsals, offline backup, final checklist signed off. |

## Scheduled tickets

All tickets start as **To do**. Use board columns: To do, In progress, Review, Done, Blocked. A dependency must pass review before dependent financial behavior is merged; UI scaffolds may proceed against agreed interfaces.

### CAP-01 - Confirm scope and make the project reproducible
**Dates:** Nov 9-10. **Owner:** C, with all contributors. **Estimate:** 1 day. **Priority:** Must. **Dependencies:** none. **Backlog:** EW-01.

- Inventory team code and mark every feature implemented, partial, or missing.
- Agree JDK, build/run commands, database, package structure, and service interfaces; address IntelliJ form initialization.
- A second teammate builds and opens login from a clean checkout.
- Record owner names and confirm whether the rubric requires loans/investments.

### CAP-02 - Persist the wallet domain and transaction rules
**Dates:** Nov 10-13. **Owner:** B. **Estimate:** 3 days. **Priority:** Must. **Dependencies:** CAP-01. **Backlog:** EW-02.

- Persist User, Wallet, Transaction, PaymentMethod, and ledger entries with ownership and unique references.
- Use BigDecimal for money; validate positive amounts and explicit currency precision.
- Commit balance changes and entries atomically; reject insufficient funds and duplicate requests.
- Verify restart persistence, rollback on failure, and competing attempts to spend the same funds.

### CAP-03 - Registration and password authentication
**Dates:** Nov 11-13. **Owner:** A. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-01; CAP-02 before integration. **Backlog:** EW-03.

- Register a unique account and create its wallet; replace hardcoded credentials with salted password hashes.
- Reject incorrect passwords and duplicate account identifiers; enforce failed-login limits.
- Protect authenticated screens and clear session state on logout.

### CAP-04 - OTP, transaction PIN, and session controls
**Dates:** Nov 16-18. **Owner:** A. **Estimate:** 3 days. **Priority:** Must. **Dependencies:** CAP-03. **Backlog:** EW-04, EW-05 subset.

- Verify an account-bound OTP with expiry, one-time use, resend cooldown, and attempt limits.
- Label delivery as simulated; reject random, expired, reused, and another account's codes.
- Set/change hashed PIN with reauthentication; enforce PIN attempt limits and inactivity timeout.
- Block outgoing payments without valid PIN authorization. Full account recovery is deferred.

### CAP-05 - Dashboard and navigation
**Dates:** Nov 11-13; authenticated integration Nov 18. **Owner:** C. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-01; CAP-02-04 for final integration. **Backlog:** EW-06.

- Show signed-in user's balance, recent activity, logout, and feature navigation.
- Refresh after payments; display useful empty, loading, and failure states.
- Keep database/provider work off the Swing UI thread; hide unfinished features from the final demo.

### CAP-06 - Send money
**Dates:** Nov 16-19. **Owner:** B. **Estimate:** 3 days. **Priority:** Must. **Dependencies:** CAP-02; CAP-04-05 before completion. **Backlog:** EW-07.

- Validate recipient, amount, balance including any fee, and configured limits.
- Show recipient and total before PIN confirmation.
- Debit sender and credit recipient atomically; repeated confirmation produces one transfer.
- Verify success, invalid recipient, insufficient balance, wrong PIN, and failed persistence.

### CAP-07 - Cash in/out and mock Bank API
**Dates:** Nov 16-20. **Owner:** D. **Estimate:** 4 days. **Priority:** Must. **Dependencies:** CAP-02; CAP-04-05 before completion. **Backlog:** EW-08.

- Link seeded demo bank methods and implement BankApiClient with a mock adapter.
- Credit cash-in only on success; reserve cash-out funds until settlement, releasing them on confirmed failure.
- Support success, rejection, and timeout followed by status lookup; unknown outcomes stay pending.
- Repeated provider responses never duplicate money movement; display provider reference and status.

### CAP-08 - History, receipts, and notifications
**Dates:** Nov 19-20; extend to new payment types Nov 27. **Owner:** C. **Estimate:** 3 days total. **Priority:** Must. **Dependencies:** CAP-02, CAP-06; CAP-07 for funding records. **Backlog:** EW-11, EW-12.

- List owned transactions with date/type/status filters and a receipt detail view.
- Show amount, fee, reference, counterparty, timestamp, and status; mask private account identifiers.
- Persist read/unread notifications after successful commit; notification retries never repeat payments.
- Verify sender/recipient notifications and account isolation. Printable/exported receipts are stretch scope.

### CAP-09 - Admin permissions and account controls
**Dates:** Nov 16-18. **Owner:** E. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-02, CAP-03. **Backlog:** EW-13.

- Seed an admin account and enforce User/Merchant/Admin permissions in services.
- View accounts/transactions and suspend/reactivate users with a recorded reason.
- Suspended accounts cannot initiate payments; record admin actions without secrets.
- Ordinary users cannot invoke admin operations or inspect another user's history; prohibit direct balance editing.

### CAP-10 - Pay bills
**Dates:** Nov 23-25. **Owner:** D. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-07, CAP-08. **Backlog:** EW-09.

- Offer a small seeded biller list, reference validation, amount entry, fee preview, and PIN confirmation.
- Reuse provider pending/success/failure handling and duplicate protection.
- Create bill-payment history, receipt details, and notification; confirmed failure releases reserved funds.

### CAP-11 - Merchant QR payments
**Dates:** Nov 19-25. **Owner:** E. **Estimate:** 4 days. **Priority:** Must. **Dependencies:** CAP-06, CAP-09; CAP-08 for activity integration. **Backlog:** EW-10.

- Seed a merchant profile; generate and import QR images using a documented project format.
- Validate merchant, currency, and amount; show recipient confirmation before PIN approval.
- Reuse the atomic transfer service; merchant sees received payments.
- Reject malformed/inactive-merchant QR codes and duplicate submissions. Camera scanning and real-provider QR compatibility are excluded.

### CAP-12 - Basic simulated loan workflow
**Dates:** Nov 26-27. **Owner:** D. **Estimate:** 2 days. **Priority:** Planned, subject to Nov 20 scope gate. **Dependencies:** CAP-02, CAP-04, CAP-09. **Backlog:** EW-14 reduced scope.

- Offer one configured loan product with documented interest/fee calculation and total repayment preview.
- User applies; admin approves/rejects; approval credits the wallet exactly once.
- Show amount due and support full repayment with atomic wallet/loan updates.
- Reject duplicate disbursement, insufficient-funds repayment, and repeat repayment of a paid loan.
- Defer installment scheduling, partial repayment, penalties, and advanced eligibility scoring.

### CAP-13 - Basic simulated investment workflow
**Dates:** Nov 26-27. **Owner:** E. **Estimate:** 2 days. **Priority:** Planned, subject to Nov 20 scope gate. **Dependencies:** CAP-02, CAP-04. **Backlog:** EW-15 reduced scope.

- Offer one seeded investment product with clearly simulated prices.
- Preview units and cost; buying debits wallet and increases holdings atomically.
- Redeeming credits wallet and decreases holdings atomically; reject insufficient funds and overselling.
- Persist holdings and activity. Defer live prices, forecasting, and multiple product types.

### CAP-14 - Integration checkpoint and feature freeze
**Dates:** Nov 23-27; freeze Nov 29. **Owner:** B, with C. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-06-11; CAP-12-13 if retained.

- Merge reviewed features into one runnable build and exercise cross-feature balance/history consistency.
- Prepare deterministic user, merchant, admin, biller, and bank demo data.
- Complete the original sequence: send money, validate, update both balances, deliver notifications.
- Confirm no new features after Nov 29; unresolved work becomes a bug or explicitly deferred scope.

### CAP-15 - Regression testing and defect fixes
**Dates:** Nov 30-Dec 3. **Owners:** A and B; each module owner fixes their defects. **Estimate:** 6 person-days total. **Priority:** Must. **Dependencies:** CAP-14.

- Test login/OTP/PIN failures, role boundaries, invalid amounts, insufficient funds, duplicate requests, provider timeout, and app restart.
- Verify every completed payment balances correctly and failed payments do not leave partial updates.
- Check keyboard navigation, validation messages, and UI responsiveness.
- Resolve all demo-blocking defects and incorrect balance/security behavior; record remaining cosmetic issues.

### CAP-16 - Final diagrams, documentation, and slides
**Dates:** Nov 30-Dec 3. **Owner:** E, with each contributor supplying their module notes. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-14.

- Update class diagram to match implemented classes, relationships, and multiplicities.
- Include use-case diagram for all four actors and send-money sequence diagram.
- Explain encapsulation, abstraction, inheritance/interfaces, and polymorphism using actual code examples.
- Document setup, mock integrations, implemented scope, limitations, testing evidence, and team contributions.
- Prepare slides and a timed demo outline; avoid claiming deferred features are complete.

### CAP-17 - Package and verify the release candidate
**Dates:** Dec 2-4. **Owner:** C, with D. **Estimate:** 2 days. **Priority:** Must. **Dependencies:** CAP-15 and CAP-16 before release sign-off.

- Package a runnable release with required runtime/dependencies and documented launch instructions.
- Test installation/launch on the presentation laptop without relying on the developer IDE.
- Provide a resettable demo database, QR sample, release backup, screenshots, and a short backup demo recording.
- Verify the classroom demonstration can run offline using simulated integrations.
- Label the Dec 4 release candidate and record its commit/build identifier.

### CAP-18 - Rehearse and approve the final presentation build
**Dates:** Dec 7-8. **Owner:** All. **Estimate:** Two 60-90 minute team sessions. **Priority:** Must. **Dependencies:** CAP-17.

- Run two timed rehearsals, assign speaking sections, and practice OOP/security/transaction questions.
- Reset and complete the demo from the packaged release on the actual laptop.
- Confirm slides, source, diagrams, database, QR sample, and recording are backed up.
- Allow only verified critical fixes; rerun affected scenarios after every fix and preserve the previous working package.
- Final readiness sign-off on Dec 8 for F1/F2/G9.

## Scope gates and contingency

- **Nov 13:** Persistent accounts and login should work. OTP/PIN complete Nov 18; week 1 security work is therefore only the password foundation. If foundation work slips, move available UI/documentation help to integration and reassess scope immediately.
- **Nov 20:** Core transfers and funding must work. If they do not, use Nov 23-27 extension capacity for fixes. Loans/investments may move to future work only if the rubric and agreed presentation scope permit; otherwise reduce them to the basic flows above and remove polish/stretch work.
- **Nov 27:** All required flows run together. No saved recipients, request money, disputes/refunds, full recovery, camera scanning, real SMS, or live financial integrations in this month.
- **Dec 4:** If a blocker remains, use Dec 7 for the fix and Dec 8 for final validation. Do not spend the buffer on new features.
- F2 and G9 may use the days after Dec 8 for rehearsal and verified critical fixes; keep the common readiness deadline.

## Suggested 8-10 minute demo

1. Introduce actors, architecture, and OOP examples (1 minute).
2. Log in with password and simulated OTP; show wallet balance (1 minute).
3. Cash in through the mock Bank API and send money with PIN (2 minutes).
4. Show recipient balance, transaction receipt, notification, and one rejected transaction (1 minute).
5. Pay a bill and import a merchant QR payment (2 minutes).
6. Show admin controls and basic loan/investment flows if included (1-2 minutes).
7. Summarize testing and clearly identify simulated integrations (1 minute).

Adjust this outline if the instructor specifies a different time limit.

## Definition of done

A ticket is Done only when its acceptance criteria pass, code is reviewed and integrated, relevant service tests or repeatable checks pass, and the shared build still runs. Financial changes require failure-path and duplicate-request checks. Update the documentation when delivered scope differs from the original backlog.
