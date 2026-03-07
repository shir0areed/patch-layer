# session_folder.py
import subprocess
from pathlib import Path


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

        # ----------------------------------------
        # セッション開始（RAII: forward path）
        # ----------------------------------------

        # 1. detached HEAD に移行
        self._git("checkout", "--detach", "HEAD")

        # 2. dirty があれば snapshot commit を作る（A）
        if self._has_dirty():
            self._git("add", "-A")
            self._git("commit", "-m", "session-snapshot")
            self.return_point = self._git("rev-parse", "HEAD").stdout.strip()
        else:
            # dirty がなければ original_commit が戻り先
            self.return_point = self.original_commit

        # 3. レイヤー適用（P1, P2, …, Pn）
        self.layer_commits: list[str] = []
        abs_layers = [(self.catalog_dir / p).resolve() for p in layer_relpaths]

        for abs_layer in abs_layers:
            r = self._git("apply", str(abs_layer))
            if r.returncode != 0:
                raise RuntimeError(f"Failed to apply layer: {abs_layer}\n{r.stderr}")

            self._git("add", "-A")
            self._git("commit", "-m", f"apply {abs_layer.name}")

            commit_hash = self._git("rev-parse", "HEAD").stdout.strip()
            self.layer_commits.append(commit_hash)

        # 4. Pn−1 を base_commit として保持
        if len(self.layer_commits) >= 2:
            self.base_commit = self.layer_commits[-2]
        else:
            self.base_commit = self.return_point

    # ----------------------------------------
    # 公開 API
    # ----------------------------------------
    @property
    def path(self) -> Path:
        return self.repo_root
    
    def diff_from_last_layer(self) -> str:
        r = self._git("diff", self.base_commit)
        return r.stdout

    # ----------------------------------------
    # セッション終了（RAII: reverse path）
    # ----------------------------------------
    def destroy(self):
        # 1. レイヤー破棄 → return_point へ戻す
        self._git("reset", "--hard", self.return_point)

        # 2. dirty の破棄 → original_commit に mixed reset
        #    （working tree は return_point のまま → dirty が復元される）
        self._git("reset", "--mixed", self.original_commit)

        # 3. detached HEAD の破棄 → 元のブランチへ戻る
        self._git("checkout", self.original_ref)

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
