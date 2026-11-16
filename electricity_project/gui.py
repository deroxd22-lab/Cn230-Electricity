"""Select SQLite records with a mouse and export them as CSV. Python + Tkinter."""
import tkinter as tk
from datetime import datetime
from decimal import Decimal
from tkinter import filedialog, messagebox, ttk

from data_access import ROOT, export_rows, filter_rows, load_rows, row_key

DATASETS = ("all", "electricity", "water", "air_emissions", "ghg")
COLUMNS = ("dataset_type", "id", "year_be", "category", "metric", "quantity_original", "unit_original", "scope")
HEADINGS = ("ประเภท", "ID", "ปี พ.ศ.", "หมวดข้อมูล", "ตัวชี้วัด", "ปริมาณ", "หน่วย", "ขอบเขต")
WIDTHS = (130, 55, 80, 240, 230, 125, 130, 240)


class ExportApp:
    def __init__(self, window):
        self.window = window
        self.rows = load_rows()
        self.by_key = {row_key(row): row for row in self.rows}
        self.visible = []
        self.sort_column = None
        self.sort_reverse = False
        self.drag_anchor = None
        self.drag_start = None
        self.search_job = None

        window.title("Electricity — เลือกข้อมูลและส่งออก CSV (เวอร์ชันแยก)")
        window.geometry("1360x820")
        window.minsize(960, 640)
        style = ttk.Style(window)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", font=("Tahoma", 10))
        style.configure("Treeview", rowheight=30, font=("Tahoma", 10))
        style.configure("Treeview.Heading", font=("Tahoma", 10, "bold"), padding=(5, 9))
        style.map("Treeview", background=[("selected", "#245eaa")], foreground=[("selected", "white")])

        main = ttk.Frame(window, padding=20)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="เลือกข้อมูลที่ต้องการส่งออก", font=("Tahoma", 20, "bold")).pack(anchor="w")
        ttk.Label(main, text="SQLite • เปิดฐานแบบอ่านอย่างเดียว • ส่งออกครบทุกคอลัมน์ของ CSV ต้นฉบับ").pack(anchor="w", pady=(4, 16))

        filters = ttk.Frame(main)
        filters.pack(fill="x", pady=(0, 12))
        ttk.Label(filters, text="ประเภท").pack(side="left")
        self.dataset = tk.StringVar(value="all")
        self.dataset_box = ttk.Combobox(filters, textvariable=self.dataset, values=DATASETS, state="readonly", width=18)
        self.dataset_box.pack(side="left", padx=(8, 18))
        ttk.Label(filters, text="ปี พ.ศ.").pack(side="left")
        self.year = tk.StringVar(value="all")
        self.year_box = ttk.Combobox(filters, textvariable=self.year,
                                   values=("all", *sorted({str(r['year_be']) for r in self.rows})), state="readonly", width=9)
        self.year_box.pack(side="left", padx=(8, 18))
        ttk.Label(filters, text="ค้นหา").pack(side="left")
        self.search = tk.StringVar()
        self.search_entry = ttk.Entry(filters, textvariable=self.search, width=26)
        self.search_entry.pack(side="left", padx=8, fill="x", expand=True)
        ttk.Button(filters, text="ล้างตัวกรอง", command=self.reset_filters).pack(side="left", padx=(8, 0))
        self.dataset_box.bind("<<ComboboxSelected>>", self.apply_filters)
        self.year_box.bind("<<ComboboxSelected>>", self.apply_filters)
        self.search.trace_add("write", self.schedule_filter)

        help_text = "คลิกเลือกแถว  •  Ctrl + คลิก เพิ่ม/ยกเลิกทีละแถว  •  Shift + คลิก เลือกช่วง  •  คลิกแล้วลากเลือกช่วง  •  Ctrl + A เลือกทั้งหมดที่แสดง"
        ttk.Label(main, text=help_text, wraplength=1250).pack(anchor="w", pady=(0, 10))
        table_frame = ttk.Frame(main)
        table_frame.pack(fill="both", expand=True)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", selectmode="extended")
        for column, heading, width in zip(COLUMNS, HEADINGS, WIDTHS):
            self.tree.heading(column, text=heading, command=lambda c=column: self.sort_by(c))
            self.tree.column(column, width=width, minwidth=55, stretch=False,
                             anchor="e" if column in ("id", "year_be", "quantity_original") else "w")
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self.selection_changed)
        self.tree.bind("<Control-a>", self.select_all)
        self.tree.bind("<Control-A>", self.select_all)
        self.tree.bind("<ButtonPress-1>", self.begin_drag, add="+")
        self.tree.bind("<B1-Motion>", self.drag_select)
        self.tree.bind("<ButtonRelease-1>", self.end_drag, add="+")

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=12)
        self.status = tk.StringVar()
        ttk.Label(actions, textvariable=self.status).pack(side="left")
        self.export_button = ttk.Button(actions, text="ส่งออกแถวที่เลือกเป็น CSV…", command=self.export_selected, state="disabled")
        self.export_button.pack(side="right")
        ttk.Button(actions, text="ยกเลิกการเลือก", command=self.clear_selection).pack(side="right", padx=8)
        ttk.Button(actions, text="เลือกทั้งหมดที่แสดง", command=self.select_all).pack(side="right")

        ttk.Label(main, text="รายละเอียดแถวที่โฟกัส", font=("Tahoma", 10, "bold")).pack(anchor="w")
        self.details = tk.Text(main, height=5, wrap="word", font=("Tahoma", 10), relief="solid", borderwidth=1,
                               background="#f5f7fa", padx=10, pady=8)
        self.details.pack(fill="x", pady=(6, 0))
        self.details.configure(state="disabled")
        self.notice = tk.StringVar(value="เปลี่ยนตัวกรองจะยกเลิกการเลือกเดิม เพื่อให้ส่งออกเฉพาะแถวที่เห็น")
        ttk.Label(main, textvariable=self.notice, wraplength=1250).pack(anchor="w", pady=(8, 0))
        self.apply_filters()

    def schedule_filter(self, *_):
        if self.search_job:
            self.window.after_cancel(self.search_job)
        self.search_job = self.window.after(180, self.apply_filters)

    def reset_filters(self):
        self.dataset.set("all")
        self.year.set("all")
        self.search.set("")
        self.apply_filters()

    def apply_filters(self, _event=None):
        if self.search_job:
            self.window.after_cancel(self.search_job)
            self.search_job = None
        self.visible = filter_rows(self.rows, self.dataset.get(), self.year.get(), self.search.get())
        self.drag_anchor = None
        if self.sort_column:
            self.visible.sort(key=lambda r: self.sort_value(r, self.sort_column), reverse=self.sort_reverse)
        old = self.tree.get_children()
        if old:
            self.tree.delete(*old)
        for row in self.visible:
            self.tree.insert("", "end", iid=row_key(row), values=[row[c] for c in COLUMNS])
        self.selection_changed()
        if not self.visible:
            self.notice.set("ไม่พบข้อมูลตามตัวกรอง ลองเปลี่ยนปี ประเภท หรือคำค้น")
        else:
            self.notice.set("เปลี่ยนตัวกรองจะยกเลิกการเลือกเดิม เพื่อให้ส่งออกเฉพาะแถวที่เห็น")

    @staticmethod
    def sort_value(row, column):
        if column == "quantity_original":
            return Decimal(row[column])
        if column in ("id", "year_be"):
            return int(row[column])
        return str(row[column]).casefold()

    def sort_by(self, column):
        self.sort_reverse = not self.sort_reverse if self.sort_column == column else False
        self.sort_column = column
        self.visible.sort(key=lambda r: self.sort_value(r, column), reverse=self.sort_reverse)
        for index, row in enumerate(self.visible):
            self.tree.move(row_key(row), "", index)
        for col, title in zip(COLUMNS, HEADINGS):
            self.tree.heading(col, text=title + ((" ▼" if self.sort_reverse else " ▲") if col == column else ""))

    def select_all(self, _event=None):
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children)
            self.tree.focus(children[0])
        self.selection_changed()
        return "break"

    def clear_selection(self):
        selected = self.tree.selection()
        if selected:
            self.tree.selection_remove(selected)
        self.selection_changed()

    def begin_drag(self, event):
        # Preserve Treeview's normal Ctrl/Shift behavior. A plain drag selects a row range.
        self.drag_anchor = None
        if not event.state & (0x0001 | 0x0004) and self.tree.identify_region(event.x, event.y) in ("cell", "tree"):
            self.drag_anchor = self.tree.identify_row(event.y)
            self.drag_start = (event.x, event.y)

    def drag_select(self, event):
        if not self.drag_anchor or not self.drag_start:
            return None
        if abs(event.x - self.drag_start[0]) + abs(event.y - self.drag_start[1]) < 5:
            return None
        if event.y < 28:
            self.tree.yview_scroll(-1, "units")
        elif event.y > self.tree.winfo_height() - 12:
            self.tree.yview_scroll(1, "units")
        target = self.tree.identify_row(max(30, min(event.y, self.tree.winfo_height() - 3)))
        children = self.tree.get_children()
        if target and self.drag_anchor in children:
            first, last = sorted((children.index(self.drag_anchor), children.index(target)))
            self.tree.selection_set(children[first:last + 1])
            self.tree.focus(target)
            self.selection_changed()
        return "break"

    def end_drag(self, _event=None):
        self.drag_anchor = None
        self.drag_start = None

    def selected_rows(self):
        selected = set(self.tree.selection())
        return [self.by_key[key] for key in self.tree.get_children() if key in selected]

    def selection_changed(self, _event=None):
        selected = self.tree.selection()
        self.status.set(f"แสดง {len(self.visible)} / {len(self.rows)} แถว   •   เลือก {len(selected)} แถว")
        self.export_button.configure(state="normal" if selected else "disabled")
        key = self.tree.focus()
        if key not in selected:
            key = selected[-1] if selected else None
        row = self.by_key.get(key)
        text = "เลือกแถวเพื่อดูหน่วย ขอบเขต และแหล่งอ้างอิง"
        if row:
            text = (f"{row_key(row)} | ปี {row['year_be']} | {row['category']} | {row['quantity_original']} {row['unit_original']}\n"
                    f"ตัวชี้วัด: {row['metric']} | ขอบเขต: {row['scope']} | สถานะต้นฉบับ: {row['quantity_status']}\n"
                    f"แหล่ง: {row['source_name']} | {row['source_reference']}\n{row['source_url']}")
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def export_selected(self):
        # Resolve pending search before taking a selection, so hidden stale rows cannot export.
        if self.search_job:
            self.apply_filters()
        rows = self.selected_rows()
        if not rows:
            messagebox.showinfo("ยังไม่ได้เลือกข้อมูล", "กรุณาเลือกอย่างน้อยหนึ่งแถว", parent=self.window)
            return
        folder = ROOT / "exports"
        folder.mkdir(exist_ok=True)
        destination = filedialog.asksaveasfilename(
            parent=self.window, title=f"ส่งออก {len(rows)} แถวเป็น CSV", initialdir=folder,
            initialfile=f"selected_{datetime.now():%Y%m%d_%H%M%S}.csv", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")])
        if not destination:
            return
        try:
            count = export_rows(rows, destination)
        except (OSError, ValueError) as exc:
            messagebox.showerror("ส่งออกไม่สำเร็จ", str(exc), parent=self.window)
            return
        self.notice.set(f"ส่งออก {count} แถวสำเร็จ: {destination}")
        messagebox.showinfo("ส่งออกสำเร็จ", f"บันทึก {count} แถว พร้อมหัวตารางและครบ 12 คอลัมน์\n{destination}", parent=self.window)


def main():
    window = tk.Tk()
    try:
        ExportApp(window)
    except Exception as exc:
        messagebox.showerror("เปิดโปรแกรมไม่สำเร็จ", str(exc), parent=window)
        window.destroy()
        return
    window.mainloop()


if __name__ == "__main__":
    main()
