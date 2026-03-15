from typing import Dict, List, Optional

from .ui_adapter import UIAdapter


class CLIUIAdapter(UIAdapter):
    """CLI 版 UIAdapter"""

    def show_error(self, title: str, message: str):
        print(f"[{title}] {message}")
        input("Press Enter to continue...")

    def select_composition(self, compositions: Dict[str, List[str]]) -> Optional[str]:
        keys = list(compositions.keys())

        # 1 個だけなら即決
        if len(keys) == 1:
            return keys[0]

        # 複数 → 無限ループで選択
        while True:
            print("Select composition:")
            for i, k in enumerate(keys):
                print(f"  {i}: {k}")

            ans = input("index (or blank to cancel): ").strip()
            if ans == "":
                return None  # Cancel と同じ扱い

            if ans.isdigit():
                idx = int(ans)
                if 0 <= idx < len(keys):
                    return keys[idx]

            self.show_error("Selection Error", "Invalid selection.")

    def destroy_prompt(self, title: str, message: str) -> bool:
        print(f"[{title}]\n{message}")
        while True:
            ans = input("(r)etry / (c)ancel: ").strip().lower()
            if ans.startswith("r"):
                return True
            if ans.startswith("c"):
                return False
            print("Please enter r or c.")

    def run_main_window(self, item, catalog_path, session) -> int:
        """
        CLI 版のメインループ。
        write / quit のみを受け付ける。
        差分がなければ write をスキップする。
        """
        print("CLI mode")
        print(f"Session folder: {session.path}")
        print("Commands: write, quit")

        layers = item[1]
        write_idx = len(layers) - 1
        patch_name = layers[write_idx]

        while True:
            cmd = input("> ").strip().lower()

            if cmd == "quit":
                return 0

            if cmd == "write":
                if not session.can_write():
                    print(f"No changes to write for {patch_name}. Skipped.")
                    continue

                print(f"Writing patch: {patch_name}")
                session.write(write_idx)
                session.reapply_layers()
                print("Write + reapply done.")
                continue

            print("Unknown command. Available: write, quit")
