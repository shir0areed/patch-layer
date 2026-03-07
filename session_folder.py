# session_folder.py
import subprocess
from pathlib import Path


class SessionFolder:
    def __init__(self, catalog_path: Path):
        # リポジトリルートを特定
        self.repo_root = self._git_repo_root(catalog_path)

        # 元のブランチ名 or HEAD を記録（O）
        self.original_ref = self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.original_commit = self._git("rev-parse", "HEAD").stdout.strip()

        # pre-session commit（A）のハッシュ
        self.pre_session_commit: str | None = None

        # まず detached HEAD に移行（dirty があっても checkout --detach は可能）
        self._git("checkout", "--detach", "HEAD")

        # dirty があれば pre-session commit を作る
        if self._has_dirty():
            self._git("add", "-A")
            self._git("commit", "-m", "pre-session")
            self.pre_session_commit = self._git("rev-parse", "HEAD").stdout.strip()

        # ここからセッション開始（テンプレート展開やパッチ適用は別途）

    # -----------------------------
    # 公開 API
    # -----------------------------
    @property
    def path(self) -> Path:
        # セッションの作業対象はリポジトリのワーキングツリー
        return self.repo_root

    def has_diff(self) -> bool:
        r = self._git("status", "--porcelain")
        return bool(r.stdout.strip())

    def get_diff(self) -> str:
        r = self._git("diff")
        return r.stdout

    def destroy(self):
        # セッション中の変更を破棄
        self._git("reset", "--hard")

        # 元のブランチに戻る（HEAD → original_ref）
        self._git("checkout", self.original_ref)

        # pre-session commit がある場合だけ dirty を復元
        if self.pre_session_commit is not None:
            # working tree を A に戻す
            self._git("reset", "--hard", self.pre_session_commit)

            # HEAD と index を O に戻しつつ、working tree はそのまま
            # → A と O の差分（＝元の dirty）が未ステージとして復元される
            self._git("reset", "--mixed", self.original_commit)

    # -----------------------------
    # 内部ユーティリティ
    # -----------------------------
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
