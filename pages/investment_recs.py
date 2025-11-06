"""Investment recommendation and explainability view."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from models.entities import Recommendation, Transaction
from services.recommendation_service import RecommendationService

RISK_QUESTIONS: List[Dict[str, object]] = [
    {
        "id": "q1",
        "prompt": "您能接受的最大亏损是多少？",
        "options": [
            ("5%以内，几乎不能亏损", 1),
            ("10%左右，可接受一定波动", 2),
            ("20%以上，只要长期有收益", 3),
        ],
    },
    {
        "id": "q2",
        "prompt": "您的投资期限是多久？",
        "options": [
            ("1年以内，需要资金的流动性", 1),
            ("1-3年，可以阶段性锁定资金", 2),
            ("3年以上，长期增值为主", 3),
        ],
    },
    {
        "id": "q3",
        "prompt": "您对投资波动的态度如何？",
        "options": [
            ("波动让我焦虑，尽量避免", 1),
            ("适度波动可以接受", 2),
            ("波动越大越有机会", 3),
        ],
    },
]


def _coerce_transactions(transactions_raw: Iterable[object]) -> List[Transaction]:
    normalized: List[Transaction] = []
    for entry in transactions_raw:
        if isinstance(entry, Transaction):
            normalized.append(entry)
        elif isinstance(entry, dict):
            normalized.append(Transaction(**entry))
    return normalized


@st.cache_data(show_spinner=False)
def _generate_cached_recommendation(
    transactions_dump: Tuple[Tuple[Tuple[str, object], ...], ...],
    responses_tuple: Tuple[Tuple[str, int], ...],
    goal: str,
) -> Dict[str, object]:
    """Cacheable wrapper producing recommendation payload."""
    service = RecommendationService()
    transactions = [Transaction(**dict(entry)) for entry in transactions_dump]
    responses = dict(responses_tuple)
    return service.generate(
        transactions=transactions,
        responses=responses,
        investment_goal=goal,
    )


def _collect_risk_answers() -> Tuple[Dict[str, int], str]:
    st.subheader("Step 1：风险偏好评估")
    answers: Dict[str, int] = {}
    for question in RISK_QUESTIONS:
        key = f"risk_{question['id']}"
        label = question["prompt"]
        options: List[Tuple[str, int]] = question["options"]  # type: ignore[assignment]
        labels = [opt[0] for opt in options]
        default_index = 0
        selected = st.radio(label, options=labels, index=default_index, key=key, horizontal=False)
        for opt_label, score in options:
            if opt_label == selected:
                answers[question["id"]] = score
                break

    st.subheader("Step 2：填写投资目标")
    goal = st.text_input(
        "请描述您的目标（示例：\"我想在3年内存20万买车\"）",
        placeholder="请输入投资目标、金额或期限",
        key="investment_goal",
    )
    return answers, goal


def _render_allocation_chart(allocation: Dict[str, float]) -> None:
    allocation_df = pd.DataFrame(
        {"资产类型": list(allocation.keys()), "占比": [value * 100 for value in allocation.values()]}
    )
    fig = px.pie(
        allocation_df,
        names="资产类型",
        values="占比",
        title="资产配置比例",
        hole=0.35,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)


def _render_results(results: Dict[str, object]) -> None:
    recommendation: Recommendation = results["recommendation"]  # type: ignore[assignment]
    explanation: str = results["explanation"]  # type: ignore[assignment]
    metrics: Dict[str, float] = results["metrics"]  # type: ignore[assignment]
    allocation: Dict[str, float] = results["allocation"]  # type: ignore[assignment]
    risk_level: str = results["risk_level"]  # type: ignore[assignment]

    st.success(f"风险偏好评估结果：**{risk_level}**")
    st.markdown(f"**核心建议**：{recommendation.summary}")

    st.subheader("资产配置方案")
    _render_allocation_chart(allocation)

    st.subheader("预期收益与风险指标")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("预期年化收益", f"{metrics['expected_return']:.1f}%")
    with col2:
        st.metric("最大回撤（历史模拟）", f"{metrics['max_drawdown']:.1f}%")

    st.subheader("执行建议与行动步骤")
    for idx, step in enumerate(recommendation.rationale_steps, start=1):
        st.write(f"{idx}. {step}")

    with st.expander("为什么推荐这个组合？（XAI解释）", expanded=False):
        st.markdown(explanation.replace("\n", "  \n"))


def render() -> None:
    """Render investment recommendation workflow with XAI explanation."""
    st.title("💡 理财建议与可解释性")
    st.write("通过风险评估与目标设定，为您生成个性化的资产配置方案，并给出决策解释。")

    transactions_raw = st.session_state.get("transactions", [])
    transactions = _coerce_transactions(transactions_raw)

    answers, goal = _collect_risk_answers()
    responses_tuple = tuple(sorted(answers.items()))
    transactions_dump = tuple(
        tuple(sorted(tx.model_dump().items(), key=lambda item: item[0]))
        for tx in transactions
    )

    st.subheader("Step 3：生成资产配置建议")
    if st.button("生成理财建议", type="primary"):
        try:
            with st.spinner("正在生成个性化配置，请稍候..."):
                results = _generate_cached_recommendation(
                    transactions_dump,
                    responses_tuple,
                    goal,
                )
        except Exception as exc:  # pylint: disable=broad-except
            st.error(f"生成推荐失败：{exc}")
            return

        _render_results(results)
        # Persist to session for downstream usage or export.
        st.session_state["product_recommendations"] = [
            results["recommendation"].model_dump()  # type: ignore[attr-defined]
        ]
        st.session_state["recommendation_explanation"] = results
    else:
        cached = st.session_state.get("recommendation_explanation")
        if cached:
            st.info("已加载上次生成的理财方案。调整参数后可再次生成新方案。")
            _render_results(cached)
        else:
            st.info("填写问卷并点击按钮后将生成个性化资产配置建议。")
