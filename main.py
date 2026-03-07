"""Minimal UI skeleton for the catalog/session layer tool.

This is a minimal PySide-based UI with no business logic.
"""

import sys
from PySide6 import QtWidgets, QtCore

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Patch Layer - Patches")

        # Use a window style with only a close button (no minimize/maximize).
        # This is similar to a tool window but is implemented via window flags.
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowCloseButtonHint)

        # Size based on font metrics (height) so the UI scales with font size.
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
        self.patch_list.addItem("(no patches applied)")
        layout.addWidget(self.patch_list)

    def on_save(self):
        pass


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
