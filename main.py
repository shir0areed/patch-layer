"""Minimal UI skeleton for the catalog/session layer tool.

This is a minimal PySide-based UI with no business logic.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtWidgets, QtCore

from catalog_parser import parse_catalog_text


# -----------------------------
# Composition selection dialog
# -----------------------------
class CompositionSelectDialog(QtWidgets.QDialog):
    def __init__(self, compositions: Dict[str, List[str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Composition")

        # --- MainWindow と同じウィンドウ仕様 ---
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.CustomizeWindowHint |
            QtCore.Qt.WindowCloseButtonHint
        )

        # --- サイズ：幅だけ 2 倍 ---
        fm = QtWidgets.QApplication.fontMetrics()
        font_height = fm.height() or 16
        multiplier = 12
        fixed_size = QtCore.QSize(font_height * multiplier * 2,
                                  font_height * multiplier)
        self.setFixedSize(fixed_size)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # --- コンポジション一覧 ---
        self.list_widget = QtWidgets.QListWidget()
        for name in compositions.keys():
            item = QtWidgets.QListWidgetItem(name)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        # 最初から先頭を選択状態にする
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        # --- OK / Cancel ---
        self.btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)
        layout.addWidget(self.btns)

    def selected(self) -> Optional[str]:
        item = self.list_widget.currentItem()
        if not item:
            return None
        return item.text()


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

        self.save_button = QtWidgets.QPushButton("Write")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.on_save)
        layout.addWidget(self.save_button)

        self.patch_list = QtWidgets.QListWidget()
        for layer in layers:
            self.patch_list.addItem(layer)
        layout.addWidget(self.patch_list)

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
