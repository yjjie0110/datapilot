# 这是一个 LLM 调用统一封装层，把对 OpenAI 兼容接口）的所有调用收敛到一个入口。核心职责：
#   统一调用入口——所有 LLM 请求都走这里；
#   成本记账——按 token 用量和单价实时计算每次调用的人民币成本；
#   可观测性——记录延迟、模型名、token 数；
#   容错重试——对限流/连接/超时类错误做指数退避重试；
#   可选 JSON 模式——强制模型返回合法 JSON。
# 一句话：它是整个项目里"唯一允许调用 LLM 的管道"，保证每一次调用都能被计量、被重试、被追踪。


from __future__ import annotations

import time
from dataclasses import dataclass

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from datapilot.config import settings

# 可重试异常白名单，分别是：429，触发限流；网络抖动、DNS、TLS 握手失败；请求超时；
RETRYABLE = (RateLimitError, APIConnectionError, APITimeoutError)


@dataclass
class LLMResult:
    text: str  # 模型输出文本
    model: str  # 实际请求的模型名，便于按模型拆分报表
    in_tokens: int
    out_tokens: int
    cost_cny: float  # 人民币成本，单位元
    latency_ms: int  # 端到端延迟（含网络 + 重试等待


class LLMClient:
    """所有 LLM 调用必须走这里——成本记账只能有一个入口。"""

    def __init__(self, s=settings):
        self.s = s
        self._client = OpenAI(api_key=s.api_key, base_url=s.base_url)

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,  # 默认开启，因为这项目是 Text-to-SQL，模型输出需要是 JSON（如 {"sql": "...", "reason": "..."}）
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMResult:
        # 用于基准测试的性能计数器。(高精度计时）
        t0 = time.perf_counter()
        kwargs = {
            "model": model or self.s.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.s.temperature if temperature is None else temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = self._call(kwargs)  # 通过带 tenacity 重试的 _call 发起请求
        u = resp.usage  # 取 token 用量
        # 成本公式：(输入 token / 1e6) × 输入单价 + (输出 token / 1e6) × 输出单价
        cost = (u.prompt_tokens / 1e6) * self.s.price_in_per_m + (
            u.completion_tokens / 1e6
        ) * self.s.price_out_per_m

        return LLMResult(
            # `resp.choices[0].message.content` → 模型生成的文本内容
            text=resp.choices[0].message.content or "",
            model=kwargs["model"],
            in_tokens=u.prompt_tokens,
            out_tokens=u.completion_tokens,
            cost_cny=round(cost, 8),
            latency_ms=round((time.perf_counter() - t0) * 1000),
        )

    # 带重试的底层调用
    @retry(
        retry=retry_if_exception_type(RETRYABLE),  # 只对白名单异常重试，其他异常直接抛出
        stop=stop_after_attempt(4),  # 最多 4 次尝试（1 次原始 + 3 次重试）
        wait=wait_exponential(multiplier=1, min=1, max=20),  # 等待时间 1, 2, 4, 8, 16, 20, 20...（上限 20s）（4 次尝试的总等待上限约 1 + 2 + 4 = 7s第 4 次失败后不再等待）
        reraise=True,  # 重试耗尽后抛出原始异常而不是 RetryError
    )
    def _call(self, kwargs):
        # 返回一个 `ChatCompletion` 对象，该对象包括choices(模型生成的候选回复列表)、usage(Token 用量，兼容接口可能为 `None`)等
        # choices 数组中的每个元素（Choice）包含`index`：该候选在列表中的序号；`message`：模型生成的消息对象（`content`、`role`、`tool_calls` 等）
        # usage 包含 `prompt_tokens`（输入 token 数）、`completion_tokens`（输出 token 数）、`total_tokens`
        return self._client.chat.completions.create(**kwargs)


if __name__ == "__main__":
    llm = LLMClient()
    SYSTEM = """你是一名资深的 SQLite 数据分析师，任务是把用户的问题翻译成一条可执行的 SQLite 查询。

    规则：
    1. 只允许使用下面 schema 中出现的表和列，禁止臆造表名或列名。
    2. 只生成一条查询语句，可以使用 CTE（WITH）。禁止任何写操作。
    3. 不要输出 SQL 之外的任何解释文字。
    4. 必须严格输出如下 JSON：
    {"sql": "...", "tables_used": ["表名"], "assumptions": ["你对题意做出的任何假设"]}
    """

    result = llm.chat_json(
        system=SYSTEM,
        user="每个国家的客户总消费额，取前 5 名。",
    )
    print(type(result))
    print(result)
