#!/usr/bin/env bash
set -e

fold() {
  [[ "$_fold" ]] && echo -e "travis_fold:end:$_fold"
  [[ "$_fold" != "$1" ]] && echo -e "travis_fold:start:$1\n\033[33;1m$2\033[0m"
  [[ "$_fold" != "$1" ]] && _fold="$1" || unset _fold
}

fold check_schema "Check db schema"
sqlite3 test.mmb < tables.sql
sqlite3 test.mmb 'pragma integrity_check;'

fold test.upgrade "Test db upgrade"
cd incremental_upgrade
cp ../tests/mmex_0970.mmb upgrade_test.mmb
# The 0.9.7 test fixture has no report table, but migration v15 expects
# a pre-existing REPORT_V1. Supply the historical columns for this fixture.
sqlite3 upgrade_test.mmb <<'SQL'
CREATE TABLE IF NOT EXISTS REPORT_V1 (
  REPORTID INTEGER PRIMARY KEY,
  REPORTNAME TEXT COLLATE NOCASE NOT NULL UNIQUE,
  GROUPNAME TEXT COLLATE NOCASE,
  SQLCONTENT TEXT,
  LUACONTENT TEXT,
  TEMPLATECONTENT TEXT,
  DESCRIPTION TEXT
);
SQL
for sql in `ls database_version_*.sql | sort -n -t_ -k3`; do
  echo - $sql
  sqlite3 upgrade_test.mmb <$sql
  sqlite3 upgrade_test.mmb 'pragma integrity_check;'
done

fold test.currencies "Test currencies update"
sqlite3 upgrade_test.mmb <../debug_scripts/currencies_update_patch.mmdbg
sqlite3 upgrade_test.mmb 'pragma integrity_check;'
cd ..
fold test.currencies

fold test.virtual_recurring "Test virtual recurring transaction schema"
python3 tests/test_virtual_recurring_schema.py
fold test.virtual_recurring
