"""Read-only SQLite access and CSV export, independent of the graphical UI."""
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "electricity.db"
FIELDS = ("id", "year_be", "category", "source_id", "dataset_type", "scope",
          "metric", "quantity", "unit_original", "quantity_status", "source_url", "source_reference")


def load_rows(database=DATABASE):
    database = Path(database).resolve()
    if not database.is_file():
        raise FileNotFoundError("ไม่พบ electricity.db ในโฟลเดอร์เวอร์ชันนี้")
    conn = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only = ON")
        rows = [dict(row) for row in conn.execute(
            "SELECT o.*, s.source_name FROM all_observations AS o "
            "JOIN sources AS s ON o.source_id = s.source_id ORDER BY o.dataset_type, o.id")]
    finally:
        conn.close()
    return rows


def row_key(row):
    return f"{row['dataset_type']}/{row['id']}"


def filter_rows(rows, dataset="all", year="all", search=""):
    words = search.strip().casefold().split()
    result = []
    for row in rows:
        if dataset != "all" and row["dataset_type"] != dataset:
            continue
        if year != "all" and str(row["year_be"]) != str(year):
            continue
        text = " ".join(str(value) for value in row.values()).casefold()
        if all(word in text for word in words):
            result.append(row)
    return result


def export_rows(rows, destination):
    """Write original CSV columns, preserving the original decimal text."""
    rows = list(rows)
    if not rows:
        raise ValueError("ยังไม่ได้เลือกแถวข้อมูล")
    destination = Path(destination).resolve()
    if destination.suffix.lower() != ".csv":
        raise ValueError("กรุณาบันทึกเป็นไฟล์ .csv")
    # Never overwrite the previous version or this version's input/program files.
    original = ROOT.parent / "electricity_project"
    if destination == original or original in destination.parents:
        raise ValueError("ไม่อนุญาตให้ส่งออกทับไฟล์ในเวอร์ชันเดิม")
    if ROOT in destination.parents and ROOT / "exports" not in destination.parents:
        raise ValueError("หากบันทึกในโฟลเดอร์โปรแกรม กรุณาใช้โฟลเดอร์ exports")
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            exported = {field: row[field] for field in FIELDS}
            exported["quantity"] = row["quantity_original"]
            writer.writerow(exported)
    return len(rows)
