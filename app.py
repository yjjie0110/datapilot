"""DataPilot 网页 Demo：Streamlit 单页。
跑法：streamlit run app.py
"""
import time

import streamlit as st

from src.datapilot.eval.eval_config import load_eval_config
from src.datapilot.pipelines.a3 import graph_answer_a3

st.set_page_config(page_title="DataPilot", layout="wide")
st.title("DataPilot — 数据分析 Agent")

# 三个库可切换，默认 chinook（评测集里最经典、表少好讲）
db = st.sidebar.selectbox("数据库", ["chinook", "sakila", "ecommerce"])
q = st.text_input("问点什么：", "每个国家客户总消费额前 5 名")

# ★ 用 session_state 缓存 config，避免每次 rerun 重新 load（load 会读 yaml + 算指纹）
if "cfg" not in st.session_state:
    st.session_state.cfg = load_eval_config("a3")

if st.button("执行", type="primary") and q:
    t0 = time.perf_counter()
    with st.spinner("Agent 思考中…"):
        # graph_answer_a3(q, client=None, cfg=None) → dict（含 answer_text/sql/rows/columns/...）
        out = graph_answer_a3(
            {"question": q, "db_id": db, "difficulty": 3, "id": "demo"},
            cfg=st.session_state.cfg,
        )
    elapsed = (time.perf_counter() - t0) * 1000

    # ① 结论（Day 6 刚补的自然语言结论，这是 Demo 的灵魂）
    st.markdown("### 结论")
    st.markdown(f"> {out.get('answer_text') or '（无结论）'}")

    # ② SQL
    st.markdown("### SQL")
    st.code(out.get("sql") or "", language="sql")

    # ③ 结果表（有 rows/columns 才渲染）
    rows = out.get("rows")
    cols = out.get("columns")
    st.markdown("### 结果")
    if rows and cols:
        import pandas as pd
        st.dataframe(pd.DataFrame(rows, columns=cols))
    elif rows is None:
        st.info(f"未返回结果集（status={out.get('status')}，behavior={out.get('behavior')}）")

    # ④ 成本/调用次数（可观测，面试能讲"每次问答花了多少钱"）
    st.caption(
        f"status={out.get('status')} · llm_calls={out.get('llm_calls')} · "
        f"cost=¥{out.get('cost_cny', 0):.5f} · 总耗时 {elapsed:.0f}ms"
    )
