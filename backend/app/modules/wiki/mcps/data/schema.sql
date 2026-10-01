PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;
CREATE TABLE dataset_manifest (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    source TEXT NOT NULL CHECK (source = 'gaia_synthetic_db'),
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    generator_version TEXT NOT NULL,
    seed TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    manifest_json TEXT NOT NULL
);
CREATE TABLE subjects (
    id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('person', 'company')),
    display_name TEXT NOT NULL,
    synthetic_identifier TEXT NOT NULL UNIQUE,
    municipality TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE districts (
    id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, active INTEGER NOT NULL
);
CREATE TABLE parcels (
    id TEXT PRIMARY KEY, municipality_code TEXT NOT NULL, sheet TEXT NOT NULL,
    parcel_number TEXT NOT NULL, subaltern TEXT NOT NULL,
    district_id TEXT NOT NULL REFERENCES districts(id),
    surface_m2 INTEGER NOT NULL CHECK (surface_m2 > 0), crop TEXT NOT NULL,
    is_current INTEGER NOT NULL,
    UNIQUE (municipality_code, sheet, parcel_number, subaltern)
);
CREATE TABLE irrigation_accounts (
    id TEXT PRIMARY KEY, account_code TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
    campaign_year INTEGER NOT NULL, district_id TEXT REFERENCES districts(id),
    irrigated_surface_m2 INTEGER NOT NULL
);
CREATE TABLE subject_accounts (
    id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES subjects(id),
    account_id TEXT NOT NULL REFERENCES irrigation_accounts(id),
    role TEXT NOT NULL CHECK (role IN ('holder', 'coholder', 'delegate')),
    UNIQUE (subject_id, account_id)
);
CREATE TABLE account_parcels (
    id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES irrigation_accounts(id),
    parcel_id TEXT NOT NULL REFERENCES parcels(id), irrigated_surface_m2 INTEGER NOT NULL,
    valid_from_year INTEGER NOT NULL, valid_to_year INTEGER NOT NULL,
    CHECK (valid_to_year >= valid_from_year), UNIQUE (account_id, parcel_id, valid_from_year)
);
CREATE TABLE irrigation_applications (
    id TEXT PRIMARY KEY, application_code TEXT NOT NULL UNIQUE,
    account_id TEXT NOT NULL REFERENCES irrigation_accounts(id),
    campaign_year INTEGER NOT NULL, status TEXT NOT NULL, submitted_at TEXT NOT NULL
);
CREATE TABLE role_notices (
    id TEXT PRIMARY KEY, notice_code TEXT NOT NULL UNIQUE,
    subject_id TEXT NOT NULL REFERENCES subjects(id), tax_year INTEGER NOT NULL,
    account_code TEXT NOT NULL REFERENCES irrigation_accounts(account_code),
    total_amount_cents INTEGER NOT NULL CHECK (total_amount_cents >= 0),
    status TEXT NOT NULL CHECK (status IN ('unpaid', 'partial', 'paid'))
);
CREATE TABLE role_lines (
    id TEXT PRIMARY KEY, notice_id TEXT NOT NULL REFERENCES role_notices(id),
    parcel_id TEXT REFERENCES parcels(id), tribute_code TEXT NOT NULL,
    maintenance_amount_cents INTEGER NOT NULL, irrigation_amount_cents INTEGER NOT NULL,
    institutional_amount_cents INTEGER NOT NULL
);
CREATE TABLE payments (
    id TEXT PRIMARY KEY, notice_id TEXT NOT NULL REFERENCES role_notices(id),
    paid_at TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    method TEXT NOT NULL, status TEXT NOT NULL
);
CREATE INDEX subject_accounts_subject ON subject_accounts(subject_id, account_id);
CREATE INDEX account_parcels_parcel_year ON account_parcels(parcel_id, valid_from_year, valid_to_year);
CREATE INDEX account_parcels_account_year ON account_parcels(account_id, valid_from_year, valid_to_year);
CREATE INDEX role_notices_subject ON role_notices(subject_id, tax_year);
CREATE INDEX role_lines_notice ON role_lines(notice_id);
CREATE INDEX payments_notice ON payments(notice_id);
