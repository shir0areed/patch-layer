
from typing import Dict, List, Optional


class UIAdapter:
    """UI 抽象化の基底クラス"""

    def show_error(self, title: str, message: str):
        raise NotImplementedError

    def select_composition(self, compositions: Dict[str, List[str]]) -> Optional[str]:
        raise NotImplementedError

    def destroy_prompt(self, title: str, message: str) -> bool:
        raise NotImplementedError

    def run_main_window(self, item, catalog_path, session) -> int:
        raise NotImplementedError
