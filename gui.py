from pathlib import Path
from typing import List, Tuple, Optional

from PySide6 import QtWidgets, QtCore

from session_folder import SessionFolder
from folder_gui import open_folder

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

        write_idx = len(self.layers) - 1

        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Write",
            f"{self.layers[write_idx]} を更新してレイヤーを再適用します。\nよろしいですか？",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )

        if reply != QtWidgets.QMessageBox.Ok:
            return

        self.session.write(write_idx)
        self.session.reapply_layers()

    # -----------------------------
    # 終了時にセッションフォルダ削除
    # -----------------------------
    def closeEvent(self, event):
        if not self.session.can_write():
            event.accept()
            return

        write_idx = len(self.layers) - 1

        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Exit",
            f"変更を{self.layers[write_idx]}に保存しますか？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel,
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.session.write(write_idx)
            event.accept()
        elif reply == QtWidgets.QMessageBox.No:
            event.accept()
        else:
            event.ignore()
