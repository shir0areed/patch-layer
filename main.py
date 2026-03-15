"""Minimal UI skeleton for the catalog/session layer tool.

This is a minimal PySide-based UI with no business logic.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from PySide6 import QtWidgets, QtCore

from catalog_parser import parse_catalog_text
from composition_select_dialog import CompositionSelectDialog
from session_folder import SessionFolder
from folder_gui import open_folder, close_folder


# -----------------------------
# Main window
# -----------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, item: Tuple[str, List[str]], catalog_path: Optional[Path], session: SessionFolder):
        super().__init__()

        composition_name, layers = item
        self.layers = layers
        self.catalog_path = catalog_path
        self.session = session  # ← セッションフォルダ管理クラス

        # -----------------------------
        # タイトル設定
        # -----------------------------
        title = f"[{composition_name}]"
        if catalog_path is not None:
            title += f" {catalog_path.name}"
        self.setWindowTitle(title)

        # -----------------------------
        # ウィンドウ仕様（最小構成）
        # -----------------------------
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )

        fm = QtWidgets.QApplication.fontMetrics()
        font_height = fm.height() or 16
        multiplier = 12
        fixed_size = QtCore.QSize(font_height * multiplier, font_height * multiplier)
        self.setFixedSize(fixed_size)

        # -----------------------------
        # レイアウト
        # -----------------------------
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # -----------------------------
        # ボタン行（Open / Write）
        # -----------------------------
        button_row = QtWidgets.QHBoxLayout()

        self.open_button = QtWidgets.QPushButton("Open")
        self.open_button.clicked.connect(self.on_open)
        button_row.addWidget(self.open_button)

        self.write_button = QtWidgets.QPushButton("Write")
        self.write_button.clicked.connect(self.on_write)
        button_row.addWidget(self.write_button)

        layout.addLayout(button_row)

        # -----------------------------
        # レイヤー一覧
        # -----------------------------
        self.patch_list = QtWidgets.QListWidget()
        for layer in layers:
            self.patch_list.addItem(layer)
        layout.addWidget(self.patch_list)

    # -----------------------------
    # Open → セッションフォルダを Explorer で開く
    # -----------------------------
    def on_open(self):
        open_folder(self.session.path)

    # -----------------------------
    # Write
    # -----------------------------
    def on_write(self):
        if not self.session.can_write():
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Write",
            "パッチを更新してレイヤーを再適用します。\nよろしいですか？",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )

        if reply != QtWidgets.QMessageBox.Ok:
            return

        self.session.write(len(self.layers) - 1)
        self.session.reapply_layers()

    # -----------------------------
    # 終了時にセッションフォルダ削除
    # -----------------------------
    def closeEvent(self, event):
        if not self.session.can_write():
            event.accept()
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Exit",
            "変更を保存しますか？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.session.write(len(self.layers) - 1)
            event.accept()
        elif reply == QtWidgets.QMessageBox.No:
            event.accept()
        else:
            event.ignore()




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

    # --- 第二引数でコンポジション名が指定されている場合 ---
    forced_name: Optional[str] = None
    if len(sys.argv) > 2:
        forced_name = sys.argv[2]

    if forced_name:
        if forced_name in compositions:
            # ダイアログをスキップ
            item = (forced_name, compositions[forced_name])
        else:
            # 存在しない → エラー
            QtWidgets.QMessageBox.critical(
                None,
                "Composition Error",
                f"Composition '{forced_name}' not found in catalog."
            )
            sys.exit(1)

    else:
        # --- 通常の選択処理 ---
        if len(compositions) > 1:
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

    with SessionFolder(catalog_path, item[1]) as session:
        open_folder(session.path)
        w = MainWindow(
            item=item,
            catalog_path=catalog_path,
            session=session,
        )
        w.show()
        exit_code = app.exec()
        close_folder(session.path)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
