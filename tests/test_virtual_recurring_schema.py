#!/usr/bin/env python3
"""Schema and migration tests for virtual recurring transactions."""

import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "tables.sql").read_text(encoding="utf-8")
MIGRATION = (
    ROOT / "incremental_upgrade" / "database_version_22.sql"
).read_text(encoding="utf-8")
NEW_FIELDS = (
    ", ISVIRTUAL INTEGER NOT NULL DEFAULT 0\n"
    ", VIRTUALFREQUENCY TEXT DEFAULT NULL\n"
    ", VIRTUALSTARTDATE TEXT DEFAULT NULL\n"
)


class VirtualRecurringSchemaTest(unittest.TestCase):
    def setUp(self):
        self.database = sqlite3.connect(":memory:")

    def tearDown(self):
        self.database.close()

    def get_schedule(self):
        return self.database.execute(
            "SELECT BDID, TRANSCODE, TRANSAMOUNT, ISVIRTUAL, "
            "VIRTUALFREQUENCY, VIRTUALSTARTDATE FROM BILLSDEPOSITS_V1 "
            "WHERE BDID = 10"
        ).fetchone()

    def add_existing_schedule(self):
        self.database.execute(
            "INSERT INTO BILLSDEPOSITS_V1 "
            "(BDID, ACCOUNTID, PAYEEID, TRANSCODE, TRANSAMOUNT, "
            "REPEATS, NEXTOCCURRENCEDATE) "
            "VALUES (10, 1, 1, 'Withdrawal', 30, 1, '2026-11-30')"
        )

    def test_new_database_has_defaults(self):
        self.database.executescript(SCHEMA)
        self.add_existing_schedule()
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 0, None, None)
        )
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 "
            "SET ISVIRTUAL = 1, VIRTUALFREQUENCY = 'Daily', "
            "VIRTUALSTARTDATE = '2026-11-20' WHERE BDID = 10"
        )
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 1, "Daily", "2026-11-20")
        )

    def test_version_21_upgrade_preserves_existing_schedule(self):
        self.assertEqual(SCHEMA.count(NEW_FIELDS), 1)
        previous_schema = SCHEMA.replace(NEW_FIELDS, "", 1)
        self.database.executescript(previous_schema)
        self.add_existing_schedule()
        self.database.executescript(MIGRATION)
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 0, None, None)
        )
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 "
            "SET ISVIRTUAL = 1, VIRTUALFREQUENCY = 'Monthly', "
            "VIRTUALSTARTDATE = '2026-11-20' WHERE BDID = 10"
        )
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 1, "Monthly", "2026-11-20")
        )

    def test_reactivation_resets_start_date_and_preserves_frequency(self):
        self.database.executescript(SCHEMA)
        self.add_existing_schedule()
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 "
            "SET ISVIRTUAL = 1, VIRTUALFREQUENCY = 'Weekly', "
            "VIRTUALSTARTDATE = '2026-11-20' WHERE BDID = 10"
        )
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 "
            "SET ISVIRTUAL = 0, VIRTUALSTARTDATE = NULL WHERE BDID = 10"
        )
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 0, "Weekly", None)
        )
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 "
            "SET ISVIRTUAL = 1, VIRTUALSTARTDATE = '2026-11-26' "
            "WHERE BDID = 10"
        )
        self.assertEqual(
            self.get_schedule(),
            (10, "Withdrawal", 30, 1, "Weekly", "2026-11-26"),
        )
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 SET TRANSAMOUNT = 35 WHERE BDID = 10"
        )
        self.assertEqual(
            self.get_schedule(),
            (10, "Withdrawal", 35, 1, "Weekly", "2026-11-26"),
        )

    def test_migration_preserves_nominal_schedule_and_real_transactions(self):
        previous_schema = SCHEMA.replace(NEW_FIELDS, "", 1)
        self.database.executescript(previous_schema)
        self.add_existing_schedule()
        self.database.execute(
            "INSERT INTO CHECKINGACCOUNT_V1 "
            "(TRANSID, ACCOUNTID, PAYEEID, TRANSCODE, TRANSAMOUNT, TRANSDATE) "
            "VALUES (20, 1, 1, 'Withdrawal', 100, '2026-11-20')"
        )
        self.database.executescript(MIGRATION)
        nominal = self.database.execute(
            "SELECT REPEATS, NEXTOCCURRENCEDATE FROM BILLSDEPOSITS_V1 "
            "WHERE BDID = 10"
        ).fetchone()
        self.assertEqual(nominal, (1, "2026-11-30"))
        transaction = self.database.execute(
            "SELECT TRANSCODE, TRANSAMOUNT, TRANSDATE "
            "FROM CHECKINGACCOUNT_V1 WHERE TRANSID = 20"
        ).fetchone()
        self.assertEqual(transaction, ("Withdrawal", 100, "2026-11-20"))


if __name__ == "__main__":
    unittest.main()
