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

        # ★ 追加：除外対象のため保持
        self.catalog_path = catalog_path
        self.layer_relpaths = layer_relpaths

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

        except Exception:
            # どこで失敗しても、積まれている undo だけを逆順に実行
            self._rollback()
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
        return self.repo_root

    def can_write(self) -> bool:
        # レイヤーが最低1つ必要
        if len(self.layer_commits) == 0:
            return False

        # ★ 除外付き diff で判定
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
            # HEAD → WT の差分（除外付き）
            return self._git_diff_excluding("HEAD")

        # 最上段以外は未実装
        if layer_index != n - 1:
            raise NotImplementedError("Only the topmost layer is supported for now.")

        # 最上段レイヤー Pn のひとつ下のコミット Pn-1 を基準にする
        if n >= 2:
            base = self.layer_commits[-2]
        else:
            # レイヤーが1つしかない場合は return_point が基準
            base = self.return_point

        # ★ 除外付き diff
        return self._git_diff_excluding(base)

    # ----------------------------------------
    # セッション終了（RAII: 明示的破棄）
    # ----------------------------------------
    def destroy(self):
        self._rollback()

    # ----------------------------------------
    # 除外パス関連
    # ----------------------------------------
    def _excluded_paths(self) -> list[str]:
        paths = []

        # カタログファイル
        paths.append(str(self.catalog_path.name))

        # レイヤーのパッチファイル
        for rel in self.layer_relpaths:
            paths.append(str(rel))

        return paths

    def _git_diff_excluding(self, base: str) -> str:
        args = ["diff", base, "--", "."]
        for p in self._excluded_paths():
            args.append(f":(exclude){p}")
        r = self._git(*args)
        return r.stdout

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
