"""把一次评测/一次 ask 的完整调用链落成 JSONL trace。
每条 trace 记录：时间戳、节点名、输入摘要、输出摘要、token、耗时、错误。
"""
import json
import threading
import time
from pathlib import Path


class Tracer:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()  # runner 多线程共享一个 trace 文件，写必须串行

    def log(self, event: str, **fields) -> None:
        rec = {"ts": time.time(), "event": event, **fields}
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            self._f.write(line)
            self._f.flush()

    def close(self) -> None:
        with self._lock:
            self._f.close()
