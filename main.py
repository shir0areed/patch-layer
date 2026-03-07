"""Minimal UI skeleton for the catalog/session layer tool.

This is a minimal PySide-based UI with no business logic.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtWidgets, QtCore

from catalog_parser import parse_catalog_text
from composition_select_dialog import CompositionSelectDialog


# -----------------------------
# Main window
# -----------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, item: tuple[str, List[str]], catalog_path: Optional[Path]):
        super().__init__()

        composition_name, layers = item

        title = f"[{composition_name}]"
        if catalog_path is not None:
            title += f" {catalog_path.name}"
        self.setWindowTitle(title)

        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        fm = QtWidgets.QApplication.fontMetrics()
        font_height = fm.height() or 16
        multiplier = 12
        fixed_size = QtCore.QSize(font_height * multiplier, font_height * multiplier)
        self.setFixedSize(fixed_size)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # --- buttons row ---
        button_row = QtWidgets.QHBoxLayout()
        self.open_button = QtWidgets.QPushButton("Open")
        self.open_button.clicked.connect(self.on_open)
        button_row.addWidget(self.open_button)

        self.save_button = QtWidgets.QPushButton("Write")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.on_save)
        button_row.addWidget(self.save_button)

        layout.addLayout(button_row)

        # --- list ---
        self.patch_list = QtWidgets.QListWidget()
        for layer in layers:
            self.patch_list.addItem(layer)
        layout.addWidget(self.patch_list)

    def on_open(self):
        # TODO: implement session folder open
        pass

    def on_save(self):
        pass



# -----------------------------
# Catalog loader
# -----------------------------
def _load_compositions_from_file(path: Path) -> Dict[str, List[str]]:
    raw = path.read_text(encoding="utf-8")
    blocks = parse_catalog_text(raw)

    compositions: Dict[str, List[str]] = {}
    allowed_keys = {"composition"}

    for blk in blocks:
        key = blk.get("key", "")
        value = blk.get("value", "")
        data = blk.get("data", [])

        if key not in allowed_keys:
            raise ValueError(f"Unknown key: {key!r}")
        if not value:
            raise ValueError("Empty composition key value is not allowed")

        compositions.setdefault(value, []).extend(data)

    return compositions


# -----------------------------
# Application entry
# -----------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)

    compositions: Optional[Dict[str, List[str]]] = None
    catalog_path: Optional[Path] = None

    if len(sys.argv) > 1:
        catalog_path = Path(sys.argv[1])
        try:
            compositions = _load_compositions_from_file(catalog_path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None, "Catalog Error", f"Failed to parse catalog:\n{e}"
            )
            sys.exit(1)

    if compositions is not None and len(compositions) == 0:
        QtWidgets.QMessageBox.critical(
            None, "Catalog Error", "No compositions found in the catalog."
        )
        sys.exit(1)

    # --- コンポジション選択 ---
    if compositions and len(compositions) > 1:
        dlg = CompositionSelectDialog(compositions)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            sys.exit(0)

        selected_name = dlg.selected()
        if not selected_name:
            QtWidgets.QMessageBox.critical(
                None, "Selection Error", "No composition selected."
            )
            sys.exit(1)

        item = (selected_name, compositions[selected_name])

    else:
        # 1 個だけの場合
        item = next(iter(compositions.items()))

    w = MainWindow(item=item, catalog_path=catalog_path)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
