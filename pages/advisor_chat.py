"""Conversational financial advisor interface."""

from __future__ import annotations

from typing import List

import streamlit as st

from modules.chat_manager import ChatManager


def _init_session_defaults() -> None:
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("monthly_budget", 5000.0)
    st.session_state.setdefault("chat_cache", {})


def render() -> None:
    """Render chat UI backed by ChatManager and GPT-4o."""
    st.title("💬 对话式财务顾问")
    st.write("向AI提问预算、消费和理财相关问题，获得个性化建议。")

    _init_session_defaults()
    history: List[dict] = st.session_state["chat_history"]
    transactions = st.session_state.get("transactions", [])

    col_budget, col_hint = st.columns([1, 2])
    with col_budget:
        budget = st.number_input(
            "月度预算（元）",
            min_value=0.0,
            value=float(st.session_state["monthly_budget"]),
            step=500.0,
            help="用于计算本月剩余额度，建议结合实际每月可支配收入设置。",
        )
        st.session_state["monthly_budget"] = budget

    with col_hint:
        st.markdown(
            """
**示例问题：**
- 我这个月还能花多少？
- 我最近在哪方面花钱最多？
- 什么是ETF？
- 我该如何存钱买车？
""".strip()
        )

    chat_manager = ChatManager(
        history=history,
        transactions=transactions,
        monthly_budget=budget,
    )
    chat_manager.update_transactions(transactions)
    chat_manager.set_monthly_budget(budget)

    if history:
        for message in history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    else:
        st.info("聊天记录为空。开始提问以生成对话历史。")

    user_prompt = st.chat_input("请输入您的财务问题…")
    if not user_prompt:
        return

    history.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.write(user_prompt)

    cache: dict = st.session_state["chat_cache"]
    if user_prompt in cache:
        cached_reply = cache[user_prompt]
        history.append({"role": "assistant", "content": cached_reply})
        with st.chat_message("assistant"):
            st.write(cached_reply)
            st.caption("（命中缓存，响应更快⚡）")
        return

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            response = chat_manager.generate_response(user_prompt)
            cache[user_prompt] = response
            if len(cache) > 20:
                first_key = next(iter(cache))
                cache.pop(first_key, None)
            st.write(response)
