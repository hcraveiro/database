#!/usr/bin/env python3
"""On-disk acceptance tests for isolated MMEX virtual recurrence databases."""

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from build_virtual_recurring_acceptance import build_database

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "incremental_upgrade" / "database_version_22.sql"
).read_text(encoding="utf-8")

SCHEDULE_COLUMNS = (
    "BDID, ACCOUNTID, TOACCOUNTID, PAYEEID, TRANSCODE, TRANSAMOUNT, "
    "STATUS, CATEGID, TRANSDATE, REPEATS, NEXTOCCURRENCEDATE, NUMOCCURRENCES"
)


def snapshot(database):
    return {
        "accounts": database.execute(
            "SELECT * FROM ACCOUNTLIST_V1 ORDER BY ACCOUNTID"
        ).fetchall(),
        "posted": database.execute(
            "SELECT * FROM CHECKINGACCOUNT_V1 ORDER BY TRANSID"
        ).fetchall(),
        "schedules": database.execute(
            f"SELECT {SCHEDULE_COLUMNS} FROM BILLSDEPOSITS_V1 ORDER BY BDID"
        ).fetchall(),
        "balance_eur": database.execute(
            "SELECT COALESCE(SUM(CASE WHEN TRANSCODE='Deposit' "
            "THEN TRANSAMOUNT ELSE -TRANSAMOUNT END), 0) "
            "FROM CHECKINGACCOUNT_V1 WHERE ACCOUNTID=901"
        ).fetchone()[0],
    }


class AcceptanceDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mmex-acceptance-")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_synthetic_v22_is_persistent_and_contains_only_test_data(self):
        path = build_database(self.folder / "synthetic_v22.mmb")
        with sqlite3.connect(path) as database:
            self.assertEqual(database.execute("PRAGMA user_version").fetchone(), (22,))
            self.assertEqual(database.execute(
                "SELECT INFOVALUE FROM INFOTABLE_V1 WHERE INFONAME='DATAVERSION'"
            ).fetchone(), ("22",))
            self.assertEqual(database.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(database.execute(
                "SELECT COUNT(*) FROM BILLSDEPOSITS_V1 WHERE ISVIRTUAL=1"
            ).fetchone(), (6,))
            self.assertEqual(database.execute(
                "SELECT COUNT(*) FROM CHECKINGACCOUNT_V1"
            ).fetchone(), (5,))
            self.assertEqual(database.execute(
                "SELECT COUNT(*) FROM BILLSDEPOSITS_V1 "
                "WHERE TRANSCODE='Transfer' AND ISVIRTUAL=1"
            ).fetchone(), (0,))
            baseline = snapshot(database)
        with sqlite3.connect(path) as database:
            self.assertEqual(snapshot(database), baseline)

    def test_v21_copy_migrates_without_touching_original_or_real_ledger(self):
        source = build_database(self.folder / "original_v21.mmb", version=21)
        digest_before = hashlib.sha256(source.read_bytes()).hexdigest()

        destination = self.folder / "upgraded_copy_v22.mmb"
        with sqlite3.connect(source) as original:
            old = snapshot(original)
            self.assertEqual(original.execute("PRAGMA user_version").fetchone(), (21,))
            self.assertEqual(original.execute(
                "SELECT INFOVALUE FROM INFOTABLE_V1 WHERE INFONAME='DATAVERSION'"
            ).fetchone(), ("21",))
            with sqlite3.connect(destination) as copy:
                original.backup(copy)

        with sqlite3.connect(destination) as database:
            self.assertEqual(database.execute("PRAGMA user_version").fetchone(), (21,))
            database.executescript(MIGRATION)
            database.execute("PRAGMA user_version=22")
            database.execute(
                "UPDATE INFOTABLE_V1 SET INFOVALUE='22' "
                "WHERE INFONAME='DATAVERSION'"
            )
            self.assertEqual(snapshot(database), old)
            self.assertEqual(database.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(database.execute(
                "SELECT COUNT(*) FROM BILLSDEPOSITS_V1 WHERE ISVIRTUAL<>0"
            ).fetchone(), (0,))
            self.assertEqual(database.execute(
                "SELECT COUNT(*) FROM BILLSDEPOSITS_V1 "
                "WHERE VIRTUALFREQUENCY IS NOT NULL OR VIRTUALSTARTDATE IS NOT NULL"
            ).fetchone(), (0,))

            # Enable a forecast schedule, edit amount and frequency, then disable.
            # None of these schema-level changes may insert a real payment.
            database.execute(
                "UPDATE BILLSDEPOSITS_V1 SET "
                "ISVIRTUAL=1, VIRTUALFREQUENCY='Weekly', "
                "VIRTUALSTARTDATE='2026-11-20' WHERE BDID=920"
            )
            database.execute(
                "UPDATE BILLSDEPOSITS_V1 SET TRANSAMOUNT=35, "
                "VIRTUALFREQUENCY='Daily' WHERE BDID=920"
            )
            self.assertEqual(database.execute(
                "SELECT VIRTUALSTARTDATE FROM BILLSDEPOSITS_V1 "
                "WHERE BDID=920"
            ).fetchone(), ("2026-11-20",))
            database.execute(
                "UPDATE BILLSDEPOSITS_V1 SET "
                "ISVIRTUAL=0, VIRTUALSTARTDATE=NULL WHERE BDID=920"
            )
            self.assertEqual(database.execute(
                "SELECT ISVIRTUAL, VIRTUALFREQUENCY, VIRTUALSTARTDATE "
                "FROM BILLSDEPOSITS_V1 WHERE BDID=920"
            ).fetchone(), (0, "Daily", None))
            self.assertEqual(database.execute(
                "SELECT * FROM CHECKINGACCOUNT_V1 ORDER BY TRANSID"
            ).fetchall(), old["posted"])
            database.commit()

        # Check again after the upgraded database is closed and reopened.
        with sqlite3.connect(destination) as upgraded:
            self.assertEqual(upgraded.execute("PRAGMA user_version").fetchone(), (22,))
            self.assertEqual(upgraded.execute(
                "SELECT INFOVALUE FROM INFOTABLE_V1 WHERE INFONAME='DATAVERSION'"
            ).fetchone(), ("22",))
            self.assertEqual(upgraded.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(upgraded.execute(
                "SELECT * FROM CHECKINGACCOUNT_V1 ORDER BY TRANSID"
            ).fetchall(), old["posted"])

        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest_before)
        with sqlite3.connect(source) as original:
            self.assertEqual(original.execute("PRAGMA user_version").fetchone(), (21,))
            self.assertEqual(snapshot(original), old)


if __name__ == "__main__":
    unittest.main()
