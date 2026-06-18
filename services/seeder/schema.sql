-- Schema for the synthetic Artemis SAP-procurement system of record.
--
-- Column names are lowercase so Data API Builder exposes lowercase REST/GraphQL
-- fields, which the OData headline query uses directly:
--   $filter=program eq 'Artemis-3' and criticality eq 'Critical'
--           and sole_source eq true and avg_delay_days gt 30
--
-- Idempotent: the seeder runs this on every load (DROP then CREATE). Sensitivity
-- labels are applied as COMMENT ON COLUMN by the seeder from data/classification.yml
-- (classify-before-exposure), not hard-coded here.

DROP TABLE IF EXISTS supply_risk;
DROP TABLE IF EXISTS purchase_orders;
DROP TABLE IF EXISTS materials;
DROP TABLE IF EXISTS vendors;

-- LFA1-style vendor master.
CREATE TABLE vendors (
    lifnr           BIGINT PRIMARY KEY,
    name1           TEXT NOT NULL,
    cage_code       TEXT,
    regio           TEXT,
    land1           TEXT,
    sole_source     BOOLEAN NOT NULL DEFAULT FALSE,
    past_perf_score NUMERIC(3, 1),
    small_business  BOOLEAN NOT NULL DEFAULT FALSE
);

-- MARA-style material master.
CREATE TABLE materials (
    matnr              TEXT PRIMARY KEY,
    maktx              TEXT NOT NULL,
    matkl              TEXT,
    program            TEXT,
    criticality        TEXT,
    std_lead_time_days INTEGER,
    std_unit_cost_usd  NUMERIC(14, 2),
    uom                TEXT
);

-- EKKO/EKPO-style purchase order header+line (one line per order here).
CREATE TABLE purchase_orders (
    ebeln           TEXT NOT NULL,
    ebelp           TEXT NOT NULL,
    matnr           TEXT,
    maktx           TEXT,
    lifnr           BIGINT,
    program         TEXT,
    criticality     TEXT,
    menge           INTEGER,
    meins           TEXT,
    netpr           NUMERIC(14, 2),
    netwr           NUMERIC(16, 2),
    waers           TEXT,
    eindt           DATE,
    bedat           DATE,
    actual_delivery DATE,
    delay_days      INTEGER,
    pad_anomaly     BOOLEAN NOT NULL DEFAULT FALSE,
    status          TEXT,
    PRIMARY KEY (ebeln, ebelp)
);

-- Derived per-material supply-risk view (materialized as a table for the demo).
CREATE TABLE supply_risk (
    matnr          TEXT PRIMARY KEY,
    maktx          TEXT,
    program        TEXT,
    criticality    TEXT,
    sole_source    BOOLEAN NOT NULL DEFAULT FALSE,
    po_count       INTEGER,
    late_po_count  INTEGER,
    avg_delay_days NUMERIC(8, 1),
    risk_score     INTEGER,
    risk_tier      TEXT
);

CREATE INDEX idx_po_matnr ON purchase_orders (matnr);
CREATE INDEX idx_po_program ON purchase_orders (program);
CREATE INDEX idx_risk_program ON supply_risk (program);
CREATE INDEX idx_risk_tier ON supply_risk (risk_tier);
