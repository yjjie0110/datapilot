# 完整优先级（从高到低）
# ① 显式传入的初始化参数  指的是调用 Settings(...) 时显式传入的关键字参数
#         >
# ② 操作系统环境变量（DP_ 前缀）
#         >
# ③ 项目根目录下的 .env 文件
#         >
# ④ Settings 类里写的默认值

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DP_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    api_key: str = ""
    base_url: str = "https://ws-gyn12735a009oqcg.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.8-flash"
    temperature: float = 0.0

    db_dir: Path = Path("data/dbs")
    dataset: Path = Path("data/benchmarks/chinook_v0.jsonl")
    run_dir: Path = Path("experiments/runs")

    max_rows: int = 200
    sql_timeout_s: float = 10.0
    concurrency: int = 4

    # 元 / 百万 token，务必去官网核对后再用
    # 总成本 = 输入 tokens / 1_000_000 * DP_PRICE_IN_PER_M + 输出 tokens / 1_000_000 * DP_PRICE_OUT_PER_M
    price_in_per_m: float = 0.8
    price_out_per_m: float = 2.7


settings = Settings()