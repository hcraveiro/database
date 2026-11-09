# Virtual Recurring Transactions — Cross-client acceptance checklist

This is a **synthetic-data-only** acceptance plan for the MMEX Desktop and
Android feature branches. Do not open a production finance database.

## Test assets

- `mmex-virtual-acceptance-v21.mmb`: synthetic legacy database; opening a
  **copy** in a v22 client should upgrade its schema without altering ledger
  rows or the source file.
- `mmex-virtual-acceptance-v22.mmb`: synthetic database already containing
  Virtual schedules, real posted transactions, two currencies, a closed
  account, and a transfer.
- `virtual_recurring_acceptance.csv`: the canonical **20-case** allocation
  contract used by the C++ and Java tests. Inputs specify their own dates;
  results are in signed minor units, with exact per-day bucket dates.

The GitHub Actions database workflow builds the two sample databases
automatically from `tests/build_virtual_recurring_acceptance.py`.
The C++ and Java workflows pin the same commit of this repository when
testing the CSV contract.

## Safety and consistency

1. Download the GitHub Actions acceptance database artifact and extract it.
2. Keep the original files untouched; make separate Desktop and Android
   *copies from the same synthetic source*. Do not use cloud sync.
3. Record SHA-256 for each source file and compare it after the tests.
4. Test the v21 migration on a duplicate, then reopen the upgraded copy.
5. Never use the user's personal database as a test source.

## Desktop and Android acceptance checks

| Case | Action | Required observation |
| --- | --- | --- |
| A01 | Open v22 synthetic database | Both clients read the same 7 schedules and 5 posted transactions |
| A02 | Filter account 901 only | Only the EUR account's Virtual forecasts affect its cash flow |
| A03 | Include account 902 | USD account forecasts are included and converted at the fixture's configured rate |
| A04 | Select open accounts | Account 903 (closed) is excluded |
| A05 | Review Virtual schedule 920 | Monthly EUR 30, Weekly buckets, activated 2026-11-20; no retroactive entries |
| A06 | Review annual Virtual schedule 921 | Monthly allocations already appear before its 2027-11-30 due date |
| A07 | Review schedule 922 | Deposit amounts increase forecast balance, never decrease it |
| A08 | Review schedule 923 | Last-business-day dates and the USD currency are preserved |
| A09 | Review schedule 924 | Transfer is **not** Virtual and cannot be converted to Virtual |
| A10 | Review schedule 926 | The final nominal occurrence is past; no implicit renewal or forecast |
| A11 | Check actual future transactions 911–912 | Actual future rows are independent of all Virtual forecasts |
| A12 | Edit schedule 920 amount and frequency | Activation date remains unchanged; only future projections recalculate |
| A13 | Turn Virtual off for schedule 920 | No overdue transactions are posted, mode remains manual, and old occurrences are advanced |
| A14 | Reactivate schedule 920 | New activation date is stored, the last Virtual Frequency selection is retained |
| A15 | Confirm Desktop Daily/Monthly/Transactions views | Virtual amounts and grouping agree with the dated breakdown |
| A16 | Reopen the synthetic file | No extra real transactions have been created by Virtual projections |

**Expected fixed-date reference (2026-11-20):** For a nominal EUR 30
recurrence due 2026-11-30, Weekly Virtual Frequency produces EUR 3 on
2026-11-23 and EUR 7 on 2026-11-30, total EUR 10.
Since live UI forecasts use the device's current date, compare both clients
on the same day; do not expect the fixed-date reference after 2026-11-20.

## Exit criteria

- Schema migration succeeds on both clients from a **copy** of v21.
- Same CSV vector dates and amounts pass CI in Desktop and Android.
- Identical v22 fixture produces matching cash-flow totals and date grouping
  in Desktop and Android for the same account selection.
- No real rows are added/updated by forecast-only actions.
- Editing, turning off, and reactivating Virtual behaves as specified.
- Date boundaries, currencies, account filters, and void/finite schedules
  have been checked in both user interfaces.

Automated tests and green CI are necessary but are **not** proof that the
whole UI acceptance checklist has been manually executed.
