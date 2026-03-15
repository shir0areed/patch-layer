import sys
from pathlib import Path
from typing import Dict, List, Optional

from catalog_parser import parse_catalog_text
from session_folder import SessionFolder


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
    try:
        try:
            from gui import QtUIAdapter
            ui = QtUIAdapter()
        except:
            from cli import CLIUIAdapter
            ui = CLIUIAdapter()
    except Exception as e:
        print(f"Failed to initialize UI:\n{e}")
        sys.exit(1)

    try:
        compositions: Optional[Dict[str, List[str]]] = None
        catalog_path: Optional[Path] = None

        if len(sys.argv) > 1:
            catalog_path = Path(sys.argv[1])
            try:
                compositions = _load_compositions_from_file(catalog_path)
            except Exception as e:
                ui.show_error("Catalog Error", f"Failed to parse catalog:\n{e}")
                sys.exit(1)
        else:
            ui.show_error("Usage Error", "Please provide the path to the catalog file as an argument.")
            sys.exit(1)

        if compositions is not None and len(compositions) == 0:
            ui.show_error("Catalog Error", "No compositions found in the catalog.")
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
                ui.show_error(
                    "Composition Error",
                    f"Composition '{forced_name}' not found in catalog."
                )
                sys.exit(1)

        else:
            # --- 通常の選択処理 ---
            selected = ui.select_composition(compositions)
            if not selected:
                sys.exit(0)
            item = (selected, compositions[selected])

        with SessionFolder(catalog_path, item[1], on_destroy_prompt=ui.destroy_prompt) as session:
            exit_code = ui.run_main_window(item, catalog_path, session)

        sys.exit(exit_code)
    except Exception as e:
        ui.show_error("Unexpected Error", f"An unexpected error occurred:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
