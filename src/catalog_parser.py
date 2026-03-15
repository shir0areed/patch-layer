"""Catalog parser module.

This module provides a simple parser for the catalog format.
It is intentionally decoupled from GUI dependencies.

Use it as a library via :func:`parse_catalog_text`.

A lightweight debug UI is available when run as a script.
"""

from typing import Dict, List


def parse_catalog_text(text: str) -> List[Dict[str, object]]:
    """Parse catalog text according to the "empty line separated blocks" rule.

    Each block is separated by one or more empty lines.
    The first non-empty line in a block is treated as `Key: Value`.
    Whitespace around the key or value (including around the colon) is ignored.
    The remaining lines (if any) are treated as data lines.
    """

    lines = text.splitlines()
    blocks: List[Dict[str, object]] = []
    current_block: List[str] = []

    def flush_block():
        if not current_block:
            return
        head = current_block[0]
        parts = head.split(":", 1)
        key = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else ""
        blocks.append({"key": key, "value": value, "data": current_block[1:]})

    for line in lines:
        if not line.strip():
            flush_block()
            current_block = []
            continue
        current_block.append(line)

    flush_block()
    return blocks


def _run_debug_ui():
    # Import GUI components only when running as a standalone tool.
    import sys

    from PySide6 import QtWidgets, QtCore


    class ParseViewer(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Catalog Parse Debug")
            self.resize(640, 480)

            central = QtWidgets.QWidget()
            self.setCentralWidget(central)

            layout = QtWidgets.QHBoxLayout(central)

            self.editor = QtWidgets.QPlainTextEdit()
            self.editor.setPlainText(
                """# Sample catalog\nKey: Value\nline1\nline2\n\nOther: Stuff\nmore\n"""
            )
            layout.addWidget(self.editor, 1)

            self.result_view = QtWidgets.QPlainTextEdit()
            self.result_view.setReadOnly(True)
            self.result_view.setPlaceholderText("Parse result will appear here")
            layout.addWidget(self.result_view, 1)

            # Update parse result whenever the source text changes.
            self.editor.textChanged.connect(self.on_parse)
            self.on_parse()

        def on_parse(self):
            text = self.editor.toPlainText()
            blocks = parse_catalog_text(text)

            lines: List[str] = []
            for idx, blk in enumerate(blocks, start=1):
                lines.append(f"Block {idx}:")
                lines.append(f"  Key: \"{blk['key']}\"")
                lines.append(f"  Value: \"{blk['value']}\"")
                lines.append("  Data:")
                if blk["data"]:
                    for dl in blk["data"]:
                        lines.append(f"    \"{dl}\"")
                else:
                    lines.append("    (none)")
                lines.append("")

            self.result_view.setPlainText("\n".join(lines))

    app = QtWidgets.QApplication(sys.argv)
    w = ParseViewer()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    _run_debug_ui()
