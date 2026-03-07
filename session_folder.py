# session_folder.py
import subprocess
from pathlib import Path
from typing import Callable, List


class SessionFolder:
    def __init__(self, catalog_path: Path, layer_relpaths: list[str]):
        # ----------------------------------------
        # 基本情報
        # ----------------------------------------
        self.repo_root = self._git_repo_root(catalog_path)
        self.catalog_dir = catalog_path.parent

        # 元のブランチ名とコミット（O）
        self.original_ref = self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.original_commit = self._git("rev-parse", "HEAD").stdout.strip()

        # 「レイヤー破棄後に戻るべきコミット」
        self.return_point = self.original_commit

        # レイヤー適用コミット（P1, P2, …, Pn）
        self.layer_commits: list[str] = []
        self.base_commit: str | None = None

        # RAII 用 undo スタック
        self._undo_stack: List[Callable[[], None]] = []

        # ----------------------------------------
        # セッション開始（RAII）
        # ----------------------------------------
        try:
            # 1. detached HEAD に移行
            r = self._git("checkout", "--detach", "HEAD")
            if r.returncode != 0:
                raise RuntimeError(f"Failed to detach HEAD:\n{r.stderr}")

            # detach の逆操作：元ブランチへ戻す
            self._push_undo(lambda: self._git("checkout", self.original_ref))

            # 2. dirty があれば snapshot commit を作る（A）
            if self._has_dirty():
                r = self._git("add", "-A")
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to add dirty changes:\n{r.stderr}")

                r = self._git("commit", "-m", "session-snapshot")
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to create session snapshot:\n{r.stderr}")

                self.return_point = self._git("rev-parse", "HEAD").stdout.strip()

            # snapshot の有無に関わらず、
            # 「return_point と original_commit の差分を dirty として復元する」逆操作を積む
            self._push_undo(lambda: self._git("reset", "--mixed", self.original_commit))

            # 3. レイヤー適用（P1, P2, …, Pn）
            abs_layers = [(self.catalog_dir / p).resolve() for p in layer_relpaths]

            if abs_layers:
                # レイヤー全体の逆操作：return_point まで hard reset
                self._push_undo(lambda: self._git("reset", "--hard", self.return_point))

            for abs_layer in abs_layers:
                r = self._git("apply", str(abs_layer))
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to apply layer: {abs_layer}\n{r.stderr}")

                r = self._git("add", "-A")
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to add after applying layer: {abs_layer}\n{r.stderr}")

                r = self._git("commit", "-m", f"apply {abs_layer.name}")
                if r.returncode != 0:
                    raise RuntimeError(f"Failed to commit after applying layer: {abs_layer}\n{r.stderr}")

                commit_hash = self._git("rev-parse", "HEAD").stdout.strip()
                self.layer_commits.append(commit_hash)

            # 4. Pn−1 を base_commit として保持（なければ return_point）
            if len(self.layer_commits) >= 2:
                self.base_commit = self.layer_commits[-2]
            elif self.layer_commits:
                self.base_commit = self.return_point
            else:
                self.base_commit = self.return_point

        except Exception:
            # どこで失敗しても、積まれている undo だけを逆順に実行
            self._rollback()
            raise

    # ----------------------------------------
    # 公開 API
    # ----------------------------------------
    @property
    def path(self) -> Path:
        return self.repo_root

    def diff_from_last_layer(self) -> str:
        base = self.base_commit or self.return_point
        r = self._git("diff", base)
        return r.stdout

    # ----------------------------------------
    # セッション終了（RAII: 明示的破棄）
    # ----------------------------------------
    def destroy(self):
        self._rollback()

    # ----------------------------------------
    # RAII: undo スタック
    # ----------------------------------------
    def _push_undo(self, action: Callable[[], None]) -> None:
        self._undo_stack.append(action)

    def _rollback(self) -> None:
        # 逆順に実行していく
        while self._undo_stack:
            action = self._undo_stack.pop()
            try:
                action()
            except Exception:
                # ロールバック中の失敗は握りつぶす（ログに出すならここ）
                pass

    # ----------------------------------------
    # 内部ユーティリティ
    # ----------------------------------------
    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

    def _git_repo_root(self, catalog_path: Path) -> Path:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=catalog_path.parent,
            text=True,
            capture_output=True,
            check=False,
        )
        if r.returncode != 0:
            raise RuntimeError("catalog_path が Git リポジトリ内にありません")
        return Path(r.stdout.strip())

    def _has_dirty(self) -> bool:
        r = self._git("status", "--porcelain")
        return bool(r.stdout.strip())
