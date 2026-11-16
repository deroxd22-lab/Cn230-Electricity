"""Read-only presentation tool. No external packages or DB Browser required."""
import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLES = ("electricity", "water", "air_emissions", "ghg")


def show(conn, sql, parameters=()):
    print("\nSQL:", sql)
    if parameters:
        print("Parameters:", parameters)
    cursor = conn.execute(sql, parameters)
    rows = cursor.fetchall()
    columns = [c[0] for c in cursor.description] if cursor.description else []
    print(" | ".join(columns))
    print("-" * 70)
    for row in rows:
        print(" | ".join("NULL" if value is None else str(value) for value in row))
    print(f"({len(rows)} rows)\n")


def summary(conn):
    show(conn, "SELECT dataset_type, COUNT(*) AS rows FROM all_observations GROUP BY dataset_type ORDER BY dataset_type")
    show(conn, "SELECT COUNT(*) AS total_observations FROM all_observations")
    show(conn, "SELECT COUNT(*) AS total_sources FROM sources")


def by_year(conn, year):
    show(conn, "SELECT dataset_type, id, year_be, category, metric, quantity_original AS quantity, "
         "unit_original, source_id FROM all_observations WHERE year_be = ? ORDER BY dataset_type, id", (year,))


def browse(conn, table):
    if table not in TABLES:
        raise ValueError("Choose: " + ", ".join(TABLES))
    show(conn, f"SELECT id, year_be, category, metric, quantity_original AS quantity, unit_original, source_id FROM {table} ORDER BY id")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--summary", action="store_true")
    group.add_argument("--year", type=int)
    group.add_argument("--table", choices=TABLES)
    group.add_argument("--sql-file", type=Path, help="Run one read-only SQL statement from a UTF-8 file")
    args = parser.parse_args()
    db = ROOT / "electricity.db"
    if not db.exists():
        raise SystemExit("Database missing. Run: python build_db.py")
    conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    try:
        if args.summary:
            summary(conn)
        elif args.year is not None:
            by_year(conn, args.year)
        elif args.table:
            browse(conn, args.table)
        elif args.sql_file:
            show(conn, args.sql_file.read_text(encoding="utf-8-sig"))
        else:
            while True:
                print("1 Summary | 2 Browse dataset | 3 Filter year | 4 Sources | 5 SQL | 0 Exit")
                choice = input("Choose: ").strip()
                try:
                    if choice == "0":
                        break
                    if choice == "1":
                        summary(conn)
                    elif choice == "2":
                        browse(conn, input("Dataset (electricity/water/air_emissions/ghg): ").strip())
                    elif choice == "3":
                        by_year(conn, int(input("Year BE, e.g. 2567: ")))
                    elif choice == "4":
                        show(conn, "SELECT * FROM sources ORDER BY source_id")
                    elif choice == "5":
                        show(conn, input("SQL (one line, read-only): "))
                    else:
                        print("Choose 0-5.")
                except (ValueError, sqlite3.Error) as exc:
                    print(f"Query failed: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error) as exc:
        raise SystemExit(f"Demo failed: {exc}")
    except (EOFError, KeyboardInterrupt):
        print("\nDemo closed.")
