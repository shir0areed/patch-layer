import sys
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtWidgets

from catalog_parser import parse_catalog_text
from composition_select_dialog import CompositionSelectDialog
from session_folder import SessionFolder
from gui import MainWindow
from folder_gui import open_folder, close_folder


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
