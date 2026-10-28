"""LLM 精确缓存：key = sha256(model + system + user + temperature)。
temperature=0 时命中即逐字节一致——缓存不改变 EX，只改变成本与延迟。

诚实声明（面试别吹错）：单次全量评测首轮全 miss，缓存的价值在
① 开发循环（调 prompt 后重跑，未受影响的问题白嫖）；
② 崩溃续跑；③ demo 现场。单次消融 run 的成本削减来自路由，不是缓存。
"""


from __future__ import annotations

import hashlib
import sqlite3
import threading
from pathlib import Path


_LOCK = threading.Lock()  # runner 4 线程共享一个缓存文件，写必须串行


class LLMCache:
    def __init__(self, path: str | Path):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT)"
        )
        self._conn.commit()
        self.hits = 0
        self.misses = 0

        @staticmethod
        def key(model: str, system: str, user: str, temperature: float) -> str:
            raw = f"{model}{temperature}{system}{user}"
            return hashlib.sha256(raw.encode("utf-8")).hexdigest()

        def get(self, k: str) -> str | None:
            row = self._conn.execute("SELECT v FROM cache WHERE k = ?", (k,)).fetchone()



