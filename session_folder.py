# session_folder.py
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List


class SessionFolder:
    def __init__(self, catalog_path: Path, layer_relpaths: list[str]):
        # ----------------------------------------
        # 基本情報
        # ----------------------------------------
        self.catalog_dir = catalog_path.parent
        self.catalog_path = catalog_path
        self.layer_relpaths = layer_relpaths

        # セッション用一時フォルダ
        self._tmpdir = tempfile.TemporaryDirectory()
        self.session_root = Path(self._tmpdir.name) / self.catalog_dir.name

        # レイヤー適用コミット（P1, P2, …, Pn）
        self.layer_commits: List[str] = []

        try:
            # 1. カタログフォルダの内容を一時フォルダへコピー（.git は除外）
            self._copy_worktree(self.catalog_dir, self.session_root)

            # 2. 一時フォルダで git init → first commit
            r = self._git("init")
            if r.returncode != 0:
                raise RuntimeError(f"Failed to init session repo:\n{r.stderr}")

            # ★ Author 設定を追加
            self._git("config", "user.name", "patch-layer")
            self._git("config", "user.email", "patch-layer@example.com")

            r = self._git("add", "-A")
            if r.returncode != 0:
                raise RuntimeError(f"Failed to add initial files:\n{r.stderr}")

            r = self._git("commit", "-m", "first commit")
            if r.returncode != 0:
                raise RuntimeError(f"Failed to create first commit:\n{r.stderr}")

            # 3. レイヤー適用（P1, P2, …, Pn）
            abs_layers = [(self.catalog_dir / p).resolve() for p in layer_relpaths]

            for abs_layer in abs_layers:
                r = self._git("apply", str(abs_layer), "--allow-empty")
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to apply layer: {abs_layer}\n{r.stderr}")

                r = self._git("add", "-A")
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to add after applying layer: {abs_layer}\n{r.stderr}")

                r = self._git("commit", "-m", f"apply {abs_layer.name}", "--allow-empty")
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to commit after applying layer: {abs_layer}\n{r.stderr}")

                commit_hash = self._git("rev-parse", "HEAD").stdout.strip()
                self.layer_commits.append(commit_hash)

        except Exception:
            self.destroy()
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # 例外の有無に関わらず destroy を呼ぶ
        self.destroy()
        # 例外を抑制しない
        return False

    # ----------------------------------------
    # 公開 API
    # ----------------------------------------
    @property
    def path(self) -> Path:
        return self.session_root

    def can_write(self) -> bool:
        # レイヤーが最低1つ必要
        if len(self.layer_commits) == 0:
            return False

        idx = len(self.layer_commits)
        diff = self.diff_merged_with_layer(idx)
        return bool(diff.strip())

    def diff_merged_with_layer(self, layer_index: int) -> str:
        """
        任意レイヤーとワーキングツリー差分をマージした diff を返す。
        範囲外 index の場合は WT-only diff（HEAD → WT）を返す。
        とりあえず最上段レイヤー以外は未実装。
        """

        n = len(self.layer_commits)

        # ----------------------------------------
        # フォールバック：WT-only diff
        # ----------------------------------------
        if layer_index < 0 or layer_index >= n:
            return self._git("diff", "HEAD").stdout

        # 最上段以外は未実装
        if layer_index != n - 1:
            raise NotImplementedError("Only the topmost layer is supported for now.")

        # 最上段レイヤー Pn のひとつ下のコミット Pn-1 を基準にする
        if n >= 2:
            base = self.layer_commits[-2]
        else:
            # レイヤーが1つしかない場合は first commit が基準
            base = "HEAD~1"

        return self._git("diff", base).stdout

    # ----------------------------------------
    # セッション終了
    # ----------------------------------------
    def destroy(self):
        from PySide6.QtWidgets import QMessageBox
        if self._tmpdir is None:
            return

        while True:
            try:
                self._tmpdir.cleanup()
                break
            except Exception as e:
                m = QMessageBox()
                m.setIcon(QMessageBox.Warning)
                m.setWindowTitle("セッションフォルダの削除に失敗しました")
                m.setText(f"セッションフォルダを削除できませんでした。\n\n{e}")
                m.setInformativeText("フォルダやファイルが開かれていないか確認してください。")
                m.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
                ret = m.exec()

                if ret == QMessageBox.Cancel:
                    break

        self._tmpdir = None


    # ----------------------------------------
    # 内部ユーティリティ
    # ----------------------------------------
    def _copy_worktree(self, src: Path, dst: Path):
        # 除外すべき絶対パス
        exclude_abspaths = {
            self.catalog_path.resolve(),
            *[(self.catalog_dir / rel).resolve() for rel in self.layer_relpaths],
            (self.catalog_dir / ".git").resolve(),
        }

        def ignore(dirpath, names):
            ignored = []
            dirpath = Path(dirpath).resolve()
            for name in names:
                candidate = (dirpath / name).resolve()
                if candidate in exclude_abspaths:
                    ignored.append(name)
            return ignored

        shutil.copytree(src, dst, ignore=ignore)

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=self.session_root,
            text=True,
            capture_output=True,
            check=False,
        )
