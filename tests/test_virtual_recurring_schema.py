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
)


class VirtualRecurringSchemaTest(unittest.TestCase):
    def setUp(self):
        self.database = sqlite3.connect(":memory:")

    def tearDown(self):
        self.database.close()

    def get_schedule(self):
        return self.database.execute(
            "SELECT BDID, TRANSCODE, TRANSAMOUNT, ISVIRTUAL, "
            "VIRTUALFREQUENCY FROM BILLSDEPOSITS_V1 WHERE BDID = 10"
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
            self.get_schedule(), (10, "Withdrawal", 30, 0, None)
        )
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 "
            "SET ISVIRTUAL = 1, VIRTUALFREQUENCY = 'Daily' WHERE BDID = 10"
        )
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 1, "Daily")
        )

    def test_version_21_upgrade_preserves_existing_schedule(self):
        self.assertEqual(SCHEMA.count(NEW_FIELDS), 1)
        previous_schema = SCHEMA.replace(NEW_FIELDS, "", 1)
        self.database.executescript(previous_schema)
        self.add_existing_schedule()
        self.database.executescript(MIGRATION)
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 0, None)
        )
        self.database.execute(
            "UPDATE BILLSDEPOSITS_V1 "
            "SET ISVIRTUAL = 1, VIRTUALFREQUENCY = 'Monthly' WHERE BDID = 10"
        )
        self.assertEqual(
            self.get_schedule(), (10, "Withdrawal", 30, 1, "Monthly")
        )


if __name__ == "__main__":
    unittest.main()
