import json
import os
import shutil
from pathlib import Path
from typing import Any, Optional, Union


class LocalStorageService:
    def __init__(self, root: Optional[Union[str, Path]] = None):
        self.root = Path(root or Path(__file__).resolve().parents[3] / "storage")
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def ensure_dir(self, *parts: str) -> Path:
        target = self._resolve(*parts)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def put_bytes(self, relative_path: str, data: bytes) -> str:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as destination:
            destination.write(data)
        return str(path)

    def put_json(self, relative_path: str, payload: Any) -> str:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as destination:
            json.dump(payload, destination, ensure_ascii=False, indent=2)
        return str(path)

    def atomic_write_json(self, relative_path: str, payload: Any) -> str:
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target.with_suffix(f"{target.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as destination:
            json.dump(payload, destination, ensure_ascii=False, indent=2)
        os.replace(tmp_path, target)
        return str(target)

    def read_json(self, relative_path: str, default: Any = None) -> Any:
        path = self._resolve(relative_path)
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as source:
            return json.load(source)

    def read_bytes(self, relative_path: str) -> Optional[bytes]:
        path = self._resolve(relative_path)
        if not path.exists():
            return None
        return path.read_bytes()

    def delete(self, relative_path: str) -> None:
        path = self._resolve(relative_path)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


storage_service = LocalStorageService()
