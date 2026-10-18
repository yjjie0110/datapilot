# 完整优先级（从高到低）
# ① 显式传入的初始化参数  指的是调用 Settings(...) 时显式传入的关键字参数
#         >
# ② 操作系统环境变量（DP_ 前缀）
#         >
# ③ 项目根目录下的 .env 文件
#         >
# ④ Settings 类里写的默认值

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 这三个字段名禁止从 .env 读取
_PINNED_FIELDS = {"db_dir", "dataset", "run_dir"}


class _DropFieldsSource(PydanticBaseSettingsSource):
    """包住一个内部 source，把它吐出的指定字段丢掉。"""

    def __init__(self, inner: PydanticBaseSettingsSource, blocked: set[str]):
        super().__init__(inner.settings_cls)
        self._inner = inner
        self._blocked = blocked

    def get_field_value(self, field, field_name):
        if field_name in self._blocked:
            return None, field_name, False
        return self._inner.get_field_value(field, field_name)

    def __call__(self) -> dict:
        return {k: v for k, v in self._inner().items() if k not in self._blocked}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DP_",
        env_file=PROJECT_ROOT / ".env",
        extra="ignore",
        protected_namespaces=(),
    )

    api_key: str = ""
    base_url: str = "https://ws-gyn12735a009oqcg.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.8-flash"
    temperature: float = 0.0

    db_dir: Path = PROJECT_ROOT / "data/dbs"
    dataset: Path = PROJECT_ROOT / "data/benchmarks/chinook_v0.jsonl"
    run_dir: Path = PROJECT_ROOT / "experiments/runs"

    max_rows: int = 200  # 单次 SQL 查询最多返回的行数，防止结果过大导致内存或输出爆炸
    sql_timeout_s: float = 10.0  # 单条 SQL 执行的超时时间，单位是秒。超过 10 秒可能被终止
    concurrency: int = 4

    price_in_per_m: float = 0.8
    price_out_per_m: float = 2.7

    # —— 关键：重排 source 顺序，并过滤 dotenv 层 ——
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,                                   # 最高
            env_settings,                                    # 环境变量仍然有效
            _DropFieldsSource(dotenv_settings, _PINNED_FIELDS),  # .env 里这三个 key 被忽略
            file_secret_settings,
        )


settings = Settings()