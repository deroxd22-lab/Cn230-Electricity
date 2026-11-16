"""Run from project folder: python -m unittest discover -s tests -v"""
import csv
import hashlib
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from data_access import DATABASE, FIELDS, ROOT, export_rows, filter_rows, load_rows, row_key
from gui import ExportApp


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        (ROOT / 'exports').mkdir(exist_ok=True)

    def test_unique_cross_dataset_keys_and_filters(self):
        self.assertEqual(len(self.rows), 110)
        self.assertEqual(len({row_key(r) for r in self.rows}), 110)
        self.assertEqual(len(filter_rows(self.rows, 'water')), 20)
        self.assertEqual(len(filter_rows(self.rows, year='2567')), 22)
        self.assertEqual(len(filter_rows(self.rows, 'ghg', '2567')), 3)
        self.assertEqual(filter_rows(self.rows, search='no-such-observation'), [])

    def test_export_preserves_all_original_fields_and_order(self):
        selected = [self.rows[0], self.rows[33], self.rows[-1]]
        original = {}
        for dataset in ('electricity', 'water', 'air_emissions', 'ghg'):
            with (ROOT / 'data' / f'{dataset}.csv').open(encoding='utf-8-sig', newline='') as stream:
                for row in csv.DictReader(stream):
                    original[row_key(row)] = row
        with tempfile.TemporaryDirectory(dir=ROOT / 'exports') as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to((ROOT / 'exports').resolve()))
            path = Path(temporary) / 'selected.csv'
            self.assertEqual(export_rows(selected, path), 3)
            with path.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, list(FIELDS))
                self.assertEqual(list(reader), [original[row_key(row)] for row in selected])

    def test_protected_paths_and_empty_selection(self):
        with self.assertRaises(ValueError):
            export_rows(self.rows[:1], ROOT / 'data' / 'electricity.csv')
        with self.assertRaises(ValueError):
            export_rows(self.rows[:1], ROOT.parent / 'electricity_project' / 'data' / 'electricity.csv')
        with self.assertRaises(ValueError):
            export_rows([], ROOT / 'exports' / 'empty.csv')


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = hashlib.sha256(DATABASE.read_bytes()).hexdigest()
        (ROOT / 'exports').mkdir(exist_ok=True)
        cls.window = tk.Tk()
        cls.app = ExportApp(cls.window)
        cls.window.update()

    @classmethod
    def tearDownClass(cls):
        cls.window.destroy()
        assert hashlib.sha256(DATABASE.read_bytes()).hexdigest() == cls.before

    def setUp(self):
        self.app.reset_filters()
        self.window.update()

    def click(self, index, state=0):
        tree = self.app.tree
        key = tree.get_children()[index]
        tree.see(key)
        self.window.update()
        x, y, width, height = tree.bbox(key)
        tree.event_generate('<ButtonPress-1>', x=x + 10, y=y + height // 2, state=state)
        tree.event_generate('<ButtonRelease-1>', x=x + 10, y=y + height // 2, state=state)
        self.window.update()

    def test_ctrl_and_shift_selection(self):
        self.click(0)
        self.click(2, state=4)
        self.assertEqual(len(self.app.selected_rows()), 2)
        self.click(0)
        self.click(4, state=1)
        self.assertEqual(len(self.app.selected_rows()), 5)

    def test_drag_range(self):
        self.click(0)
        tree = self.app.tree
        children = tree.get_children()
        x, y, _, height = tree.bbox(children[0])
        _, last_y, _, _ = tree.bbox(children[3])
        tree.event_generate('<ButtonPress-1>', x=x + 10, y=y + height // 2)
        tree.event_generate('<B1-Motion>', x=x + 10, y=last_y + height // 2)
        tree.event_generate('<ButtonRelease-1>', x=x + 10, y=last_y + height // 2)
        self.window.update()
        self.assertEqual(len(self.app.selected_rows()), 4)

    def test_filter_clears_hidden_selection_and_select_all(self):
        self.app.select_all()
        self.assertEqual(len(self.app.selected_rows()), 110)
        self.app.dataset.set('water')
        self.app.apply_filters()
        self.assertEqual(len(self.app.selected_rows()), 0)
        self.app.select_all()
        self.assertEqual(len(self.app.selected_rows()), 20)
        self.app.sort_by('quantity_original')
        self.assertEqual(len(self.app.selected_rows()), 20)

    def test_export_button_exports_only_selected_rows(self):
        self.click(0)
        self.click(3, state=4)
        expected = self.app.selected_rows()
        with tempfile.TemporaryDirectory(dir=ROOT / 'exports') as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to((ROOT / 'exports').resolve()))
            path = Path(temporary) / 'gui_selection.csv'
            with patch('gui.filedialog.asksaveasfilename', return_value=str(path)), patch('gui.messagebox.showinfo'):
                self.app.export_selected()
            with path.open(encoding='utf-8-sig', newline='') as stream:
                exported = list(csv.DictReader(stream))
            self.assertEqual([row_key(r) for r in exported], [row_key(r) for r in expected])


if __name__ == '__main__':
    unittest.main()
