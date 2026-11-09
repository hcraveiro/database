# Virtual recurring transactions (schema version 22)

Three scheduling attributes are added to `BILLSDEPOSITS_V1`:

| Column | Type | Default | Purpose |
| --- | --- | --- | --- |
| `ISVIRTUAL` | `INTEGER NOT NULL` | `0` | `1` enables a forecast-only recurring transaction. |
| `VIRTUALFREQUENCY` | `TEXT` | `NULL` | Forecast posting cadence: `Daily`, `Weekly`, `Monthly`, or `Quarterly`. |
| `VIRTUALSTARTDATE` | `TEXT` | `NULL` | Local date (`YYYY-MM-DD`) when virtual forecasting was last enabled. |

The existing `REPEATS` field continues to define the total amount's recurrence period.
`VIRTUALFREQUENCY` controls how the amount is allocated *within* that period, anchored
to the recurring transaction's due date. It must be strictly more frequent than
`REPEATS`; `Yearly` is not a valid virtual frequency. Only `Withdrawal` and
`Deposit` may be virtual. These cross-column rules are enforced by application logic
because the existing `REPEATS` value encodes both frequency and execution mode.

Existing rows default to `ISVIRTUAL = 0`, `VIRTUALFREQUENCY = NULL`,
and `VIRTUALSTARTDATE = NULL`.
When virtual mode is turned off after configuration, applications may retain the
previous `VIRTUALFREQUENCY` value for later reuse, while treating `ISVIRTUAL = 0`
as a normal recurring transaction. `VIRTUALSTARTDATE` should be set to the
current local date when virtual mode is first enabled or re-enabled, and cleared
when disabled; updating the amount or virtual frequency must not reset it.
A virtual forecast cannot include dates on or before its activation date, nor
on or before the report's current local date. The original nominal due date,
not `VIRTUALSTARTDATE`, anchors the virtual frequency blocks.

The date is deliberately nullable so migration never retroactively activates
legacy recurring transactions. As with frequency compatibility and transfer
restrictions, applications validate activation semantics rather than relying
on database constraints.

Virtual schedules only affect cash-flow forecasts. They must never create real
transactions, auto-execute, or issue payment notifications. Forecast calculations
must consider only future days, respect recurrence limits, account/currency filters,
and keep each full period's allocated amounts equal to the configured amount.

## Upgrade and compatibility

`incremental_upgrade/database_version_22.sql` upgrades existing version-21
databases and preserves their records. Schema creation is updated in `tables.sql`.
The version-22 migration is feature-branch-only; databases already migrated with
an earlier development version of this migration must be recreated from a
version-21 backup before testing the revised version-22 schema.
The SQL migration itself does not update `PRAGMA user_version`; the desktop and
Android database-upgrade managers own that step.

**Use a backup of a financial database for testing.** Both applications must
support version 22 before they open a migrated database. Unmodified official
version-21 applications are not guaranteed to read version-22 files.
