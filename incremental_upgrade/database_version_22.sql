-- Virtual recurring transactions are forecast-only schedules.
-- The values for VIRTUALFREQUENCY are Daily, Weekly, Monthly and Quarterly.
-- Existing schedules remain non-virtual after upgrade.
ALTER TABLE BILLSDEPOSITS_V1 ADD COLUMN ISVIRTUAL INTEGER NOT NULL DEFAULT 0;
ALTER TABLE BILLSDEPOSITS_V1 ADD COLUMN VIRTUALFREQUENCY TEXT DEFAULT NULL;
-- Local activation date (YYYY-MM-DD); null for legacy and non-virtual schedules.
ALTER TABLE BILLSDEPOSITS_V1 ADD COLUMN VIRTUALSTARTDATE TEXT DEFAULT NULL;
