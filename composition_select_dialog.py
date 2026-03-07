from typing import Dict, List, Optional

from PySide6 import QtWidgets, QtCore

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
