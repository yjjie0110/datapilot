# 评测配置加载与指纹。指纹必须覆盖配置内容——否则同 run_id 换了 top_k 会静默续跑，
# 把两次不同配置的实验结果混进同一个 results.jsonl，消融直接报废。

import hashlib
from pathlib import Path

import yaml


def load_eval_config(name: str) -> dict:
    p = Path("eval/configs") / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"缺少配置文件：{p}")
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    cfg["name"] = name
    return cfg


# 配置文件指纹
def config_fingerprint(cfg: dict) -> str:
    blob = yaml.safe_dump({k: v for k, v in cfg.items() if k != "name"}, sort_keys=True)
    return hashlib.md5(blob.encode()).hexdigest()[:12]