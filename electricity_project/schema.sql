-- Create a NEW database with build_db.py; this file does not migrate existing tables.
-- quantity is REAL for SQL numeric operations; quantity_original preserves CSV decimals.
PRAGMA foreign_keys = ON;

CREATE TABLE sources (
    source_id INTEGER PRIMARY KEY CHECK (source_id > 0),
    source_name TEXT NOT NULL CHECK (LENGTH(TRIM(source_name)) > 0),
    source_url TEXT NOT NULL CHECK (LENGTH(TRIM(source_url)) > 0)
);

CREATE TABLE electricity (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    year_be INTEGER NOT NULL CHECK (year_be BETWEEN 2563 AND 2567),
    category TEXT NOT NULL CHECK (LENGTH(TRIM(category)) > 0),
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    dataset_type TEXT NOT NULL CHECK (dataset_type = 'electricity'),
    scope TEXT NOT NULL CHECK (LENGTH(TRIM(scope)) > 0),
    metric TEXT NOT NULL CHECK (LENGTH(TRIM(metric)) > 0),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    unit_original TEXT NOT NULL CHECK (LENGTH(TRIM(unit_original)) > 0),
    quantity_status TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_status)) > 0),
    source_url TEXT NOT NULL CHECK (LENGTH(TRIM(source_url)) > 0),
    source_reference TEXT NOT NULL CHECK (LENGTH(TRIM(source_reference)) > 0),
    quantity_original TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_original)) > 0)
);

-- Observation identity includes the report (source_id), scope, metric and unit.
CREATE UNIQUE INDEX uq_electricity_observation ON electricity
    (source_id, year_be, TRIM(category), TRIM(scope), TRIM(metric), TRIM(unit_original));
CREATE INDEX ix_electricity_year ON electricity(year_be);

CREATE TABLE water (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    year_be INTEGER NOT NULL CHECK (year_be BETWEEN 2563 AND 2567),
    category TEXT NOT NULL CHECK (LENGTH(TRIM(category)) > 0),
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    dataset_type TEXT NOT NULL CHECK (dataset_type = 'water'),
    scope TEXT NOT NULL CHECK (LENGTH(TRIM(scope)) > 0),
    metric TEXT NOT NULL CHECK (LENGTH(TRIM(metric)) > 0),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    unit_original TEXT NOT NULL CHECK (LENGTH(TRIM(unit_original)) > 0),
    quantity_status TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_status)) > 0),
    source_url TEXT NOT NULL CHECK (LENGTH(TRIM(source_url)) > 0),
    source_reference TEXT NOT NULL CHECK (LENGTH(TRIM(source_reference)) > 0),
    quantity_original TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_original)) > 0)
);

-- Observation identity includes the report (source_id), scope, metric and unit.
CREATE UNIQUE INDEX uq_water_observation ON water
    (source_id, year_be, TRIM(category), TRIM(scope), TRIM(metric), TRIM(unit_original));
CREATE INDEX ix_water_year ON water(year_be);

CREATE TABLE air_emissions (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    year_be INTEGER NOT NULL CHECK (year_be BETWEEN 2563 AND 2567),
    category TEXT NOT NULL CHECK (LENGTH(TRIM(category)) > 0),
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    dataset_type TEXT NOT NULL CHECK (dataset_type = 'air_emissions'),
    scope TEXT NOT NULL CHECK (LENGTH(TRIM(scope)) > 0),
    metric TEXT NOT NULL CHECK (LENGTH(TRIM(metric)) > 0),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    unit_original TEXT NOT NULL CHECK (LENGTH(TRIM(unit_original)) > 0),
    quantity_status TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_status)) > 0),
    source_url TEXT NOT NULL CHECK (LENGTH(TRIM(source_url)) > 0),
    source_reference TEXT NOT NULL CHECK (LENGTH(TRIM(source_reference)) > 0),
    quantity_original TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_original)) > 0)
);

-- Observation identity includes the report (source_id), scope, metric and unit.
CREATE UNIQUE INDEX uq_air_emissions_observation ON air_emissions
    (source_id, year_be, TRIM(category), TRIM(scope), TRIM(metric), TRIM(unit_original));
CREATE INDEX ix_air_emissions_year ON air_emissions(year_be);

CREATE TABLE ghg (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    year_be INTEGER NOT NULL CHECK (year_be BETWEEN 2563 AND 2567),
    category TEXT NOT NULL CHECK (LENGTH(TRIM(category)) > 0),
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    dataset_type TEXT NOT NULL CHECK (dataset_type = 'ghg'),
    scope TEXT NOT NULL CHECK (LENGTH(TRIM(scope)) > 0),
    metric TEXT NOT NULL CHECK (LENGTH(TRIM(metric)) > 0),
    quantity REAL NOT NULL CHECK (quantity >= 0),
    unit_original TEXT NOT NULL CHECK (LENGTH(TRIM(unit_original)) > 0),
    quantity_status TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_status)) > 0),
    source_url TEXT NOT NULL CHECK (LENGTH(TRIM(source_url)) > 0),
    source_reference TEXT NOT NULL CHECK (LENGTH(TRIM(source_reference)) > 0),
    quantity_original TEXT NOT NULL CHECK (LENGTH(TRIM(quantity_original)) > 0)
);

-- Observation identity includes the report (source_id), scope, metric and unit.
CREATE UNIQUE INDEX uq_ghg_observation ON ghg
    (source_id, year_be, TRIM(category), TRIM(scope), TRIM(metric), TRIM(unit_original));
CREATE INDEX ix_ghg_year ON ghg(year_be);

-- A view is a saved query, not another copy of the observations.
-- An observation across the whole project is identified by (dataset_type, id).
CREATE VIEW all_observations AS
SELECT * FROM electricity
UNION ALL
SELECT * FROM water
UNION ALL
SELECT * FROM air_emissions
UNION ALL
SELECT * FROM ghg;

