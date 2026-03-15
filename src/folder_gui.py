import sys
from pathlib import Path

# Windows 専用
if sys.platform == "win32":
    import win32com.client


def open_folder(path: Path):
    if sys.platform == "win32":
        shell = win32com.client.Dispatch("Shell.Application")
        shell.Open(str(path))

def close_folder(path: Path):
    if sys.platform == "win32":
        shell = win32com.client.Dispatch("Shell.Application")
        target = str(path.resolve()).lower()

        for w in shell.Windows():
            try:
                if w and w.Document and w.Document.Folder:
                    folder = w.Document.Folder.Self.Path.lower()
                    if folder == target:
                        w.Quit()
            except Exception:
                pass
