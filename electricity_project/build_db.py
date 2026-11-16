"""Build a fresh SQLite database from the five CSV files. Standard library only."""
import csv
import hashlib
import json
import math
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "electricity.db"
TABLES = {"electricity": 45, "water": 20, "air_emissions": 30, "ghg": 15}
FIELDS = ["id", "year_be", "category", "source_id", "dataset_type", "scope",
          "metric", "quantity", "unit_original", "quantity_status", "source_url",
          "source_reference"]


def read_csv(filename, fields):
    path = ROOT / "data" / filename
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != fields:
            raise ValueError(f"{filename}: expected columns {fields}")
        rows = list(reader)
    for number, row in enumerate(rows, 2):
        if None in row or any(value is None or not value.strip() for value in row.values()):
            raise ValueError(f"{filename}, line {number}: missing/extra/empty fields")
    return rows


def load_inputs():
    sources = read_csv("sources.csv", ["source_id", "source_name", "source_url"])
    source_map = {}
    for row in sources:
        source_id = int(row["source_id"])
        if source_id <= 0 or source_id in source_map:
            raise ValueError("Duplicate or invalid source ID")
        source_map[source_id] = row["source_url"]
    if len(sources) != 5:
        raise ValueError("Expected 5 sources for this submission")
    datasets = {}
    for table, expected in TABLES.items():
        rows = read_csv(f"{table}.csv", FIELDS)
        if len(rows) != expected:
            raise ValueError(f"{table}: expected {expected} rows, found {len(rows)}")
        seen_ids, seen_keys = set(), set()
        for row in rows:
            record_id = int(row["id"])
            year = int(row["year_be"])
            source_id = int(row["source_id"])
            amount = Decimal(row["quantity"])
            key = tuple(row[field].strip() for field in
                        ("source_id", "year_be", "category", "scope", "metric", "unit_original"))
            if record_id <= 0 or record_id in seen_ids or key in seen_keys:
                raise ValueError(f"{table}, ID {record_id}: duplicate/invalid ID or observation")
            if not 2563 <= year <= 2567 or row["dataset_type"] != table:
                raise ValueError(f"{table}, ID {record_id}: wrong year or dataset type")
            if not amount.is_finite() or amount < 0 or not math.isfinite(float(amount)):
                raise ValueError(f"{table}, ID {record_id}: invalid quantity")
            if source_map.get(source_id) != row["source_url"]:
                raise ValueError(f"{table}, ID {record_id}: source ID/URL mismatch")
            seen_ids.add(record_id)
            seen_keys.add(key)
        datasets[table] = rows
    return sources, datasets


def build():
    # Validate first; never change the CSV originals.
    sources, datasets = load_inputs()
    handle, temporary_name = tempfile.mkstemp(prefix="building_", suffix=".db", dir=ROOT)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        conn = sqlite3.connect(temporary)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
            with conn:
                conn.executemany("INSERT INTO sources VALUES (?, ?, ?)",
                                 [(int(r["source_id"]), r["source_name"], r["source_url"]) for r in sources])
                for table, rows in datasets.items():
                    # Table names come only from the fixed TABLES list, not user input.
                    conn.executemany(f"INSERT INTO {table} ({', '.join(FIELDS)}, quantity_original) "
                                     f"VALUES ({', '.join('?' for _ in range(13))})", [
                        (int(r["id"]), int(r["year_be"]), r["category"], int(r["source_id"]),
                         r["dataset_type"], r["scope"], r["metric"], float(Decimal(r["quantity"])),
                         r["unit_original"], r["quantity_status"], r["source_url"],
                         r["source_reference"], r["quantity"]) for r in rows])
            counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                      for table in TABLES}
            fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            # Compare every imported field with the CSV, including original decimal text.
            conn.row_factory = sqlite3.Row
            for table, rows in datasets.items():
                imported = {r["id"]: dict(r) for r in conn.execute(f"SELECT * FROM {table}")}
                for source_row in rows:
                    saved = imported[int(source_row["id"])]
                    for field in FIELDS:
                        if field == "quantity":
                            expected = float(Decimal(source_row[field]))
                        elif field in ("id", "year_be", "source_id"):
                            expected = int(source_row[field])
                        else:
                            expected = source_row[field]
                        if saved[field] != expected:
                            raise ValueError(f"Imported cell differs: {table}/{source_row['id']}/{field}")
                    if saved["quantity_original"] != source_row["quantity"]:
                        raise ValueError("Original decimal text differs")
            if counts != TABLES or fk_errors or integrity != "ok":
                raise ValueError("Database checks failed")
        finally:
            conn.close()
        # Only replace this project's generated DB after a successful build and check.
        os.replace(temporary, DB)
        report = {
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "rows": counts, "total_observations": sum(counts.values()), "sources": len(sources),
            "integrity_check": integrity, "foreign_key_errors": fk_errors,
            "all_imported_cells_match_csv": True,
            "validation_scope": "Import structure and CSV-to-database equality; not source verification",
            "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted((ROOT / "data").glob("*.csv"))},
        }
        evidence = ROOT / "evidence"
        evidence.mkdir(exist_ok=True)
        (evidence / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        for table, count in counts.items():
            print(f"{table}: {count} rows")
        print(f"sources: {len(sources)} rows")
        print(f"TOTAL: {sum(counts.values())} observations")
        print("Integrity: ok; foreign key errors: 0; all CSV cells preserved")
        print(f"Database: {DB}")
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    try:
        build()
    except (ValueError, InvalidOperation, OSError, sqlite3.Error) as exc:
        raise SystemExit(f"Build failed: {exc}")
