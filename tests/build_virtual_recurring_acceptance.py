#!/usr/bin/env python3
"""Create an isolated, synthetic MMEX v22 acceptance database.

No real financial database is read or modified. All names, amounts and
accounts in this fixture are fictitious. The output is intended for
manual Desktop/Android cross-client acceptance tests.
"""

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "tables.sql").read_text(encoding="utf-8")
VIRTUAL_FIELDS = (
    ", ISVIRTUAL INTEGER NOT NULL DEFAULT 0\n"
    ", VIRTUALFREQUENCY TEXT DEFAULT NULL\n"
    ", VIRTUALSTARTDATE TEXT DEFAULT NULL\n"
)


def create_schema(database, version=22):
    if version == 21:
        assert SCHEMA.count(VIRTUAL_FIELDS) == 1
        database.executescript(SCHEMA.replace(VIRTUAL_FIELDS, "", 1))
    elif version == 22:
        database.executescript(SCHEMA)
    else:
        raise ValueError("Only synthetic schema versions 21 and 22 are supported")
    database.execute(f"PRAGMA user_version={version}")


def seed_accounts_and_ledger(database):
    accounts = [
        (901, "Acceptance EUR", "Checking", "Open", "TRUE", 2, 1000),
        (902, "Acceptance USD", "Checking", "Open", "TRUE", 1, 250),
        (903, "Acceptance Closed", "Checking", "Closed", "FALSE", 2, 100),
    ]
    database.executemany(
        "INSERT INTO ACCOUNTLIST_V1 "
        "(ACCOUNTID, ACCOUNTNAME, ACCOUNTTYPE, STATUS, FAVORITEACCT, "
        "CURRENCYID, INITIALBAL) VALUES (?, ?, ?, ?, ?, ?, ?)",
        accounts,
    )
    database.executemany(
        "INSERT INTO PAYEE_V1 (PAYEEID, PAYEENAME, ACTIVE) VALUES (?, ?, 1)",
        [(901, "Acceptance Expenses"), (902, "Acceptance Income")],
    )
    database.execute(
        "UPDATE CURRENCYFORMATS_V1 SET BASECONVRATE=0.9 "
        "WHERE CURRENCYID=1"
    )
    database.execute(
        "INSERT OR REPLACE INTO INFOTABLE_V1 (INFONAME, INFOVALUE) "
        "VALUES ('BASECURRENCYID', '2')"
    )
    posted = [
        (910, 901, None, 901, "Withdrawal", 50, "R", "2026-11-01", None),
        (911, 901, None, 902, "Deposit", 125, "R", "2026-12-01", None),
        (912, 901, 902, 901, "Transfer", 20, "R", "2026-12-05", 22),
        (913, 902, None, 902, "Deposit", 40, "R", "2026-11-02", None),
        (914, 903, None, 901, "Withdrawal", 10, "R", "2026-11-04", None),
    ]
    database.executemany(
        "INSERT INTO CHECKINGACCOUNT_V1 "
        "(TRANSID, ACCOUNTID, TOACCOUNTID, PAYEEID, TRANSCODE, "
        "TRANSAMOUNT, STATUS, TRANSDATE, TOTRANSAMOUNT) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        posted,
    )


def seed_schedules(database, version=22):
    scheduled = [
        (920, 901, None, 901, "Withdrawal", 30, 3, "2026-11-30", 5,
         "Weekly", "2026-11-20"),
        (921, 901, None, 901, "Withdrawal", 120, 7, "2027-11-30", -1,
         "Monthly", "2026-11-20"),
        (922, 901, None, 902, "Deposit", 91, 5, "2026-11-30", 2,
         "Monthly", "2026-11-20"),
        (923, 902, None, 902, "Deposit", 31, 16, "2027-01-29", -1,
         "Daily", "2026-11-20"),
        (924, 901, 902, 901, "Transfer", 20, 3, "2026-11-30", -1,
         None, None),
        (925, 903, None, 901, "Withdrawal", 15, 3, "2026-11-30", 1,
         "Weekly", "2026-11-20"),
        (926, 901, None, 901, "Withdrawal", 12, 3, "2026-09-30", 1,
         "Daily", "2026-09-01"),
    ]
    for (schedule_id, account_id, destination_id, payee_id, kind, amount,
         repeats, next_due, payments_left, frequency, activated) in scheduled:
        fields = (
            "BDID, ACCOUNTID, TOACCOUNTID, PAYEEID, TRANSCODE, TRANSAMOUNT, "
            "STATUS, CATEGID, REPEATS, NEXTOCCURRENCEDATE, NUMOCCURRENCES"
        )
        values = [
            schedule_id, account_id, destination_id, payee_id, kind,
            amount, "", 51 if kind == "Deposit" else 1,
            repeats, next_due, payments_left,
        ]
        if version == 22:
            fields += ", ISVIRTUAL, VIRTUALFREQUENCY, VIRTUALSTARTDATE"
            values.extend([1 if frequency else 0, frequency, activated])
        placeholders = ", ".join("?" for _ in values)
        database.execute(
            f"INSERT INTO BILLSDEPOSITS_V1 ({fields}) "
            f"VALUES ({placeholders})", values
        )


def build_database(path, version=22):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing file: {output}")
    with sqlite3.connect(output) as database:
        create_schema(database, version)
        seed_accounts_and_ledger(database)
        seed_schedules(database, version)
        database.commit()
        assert database.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="Path to a new synthetic .mmb database")
    parser.add_argument("--version", type=int, choices=(21, 22), default=22)
    args = parser.parse_args()
    print(build_database(args.output, args.version))
