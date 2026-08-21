"""Investment recommendation and explainability view."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from models.entities import Recommendation, Transaction
from services.recommendation_service import RecommendationService
from utils import session as session_utils
from utils.session import get_i18n, get_monthly_budget, set_product_recommendations
from utils.ui_components import (
    render_financial_health_card,
    responsive_width_kwargs,
)

# 高级问卷选项数量常量，便于统一维护
QUESTION_OPTION_COUNT = 3


def _normalize_question_options(raw_options: Iterable[Any]) -> List[Tuple[str, int]]:
    """将不同格式的选项统一为(label, score)结构，避免LLM输出差异导致崩溃"""

    normalized: List[Tuple[str, int]] = []
    for option in raw_options or []:
        label: str | None = None
        score_value: Any = None

        if isinstance(option, dict):
            label = option.get("label") or option.get("text") or option.get("option")
            score_value = option.get("score") or option.get("value")
        elif isinstance(option, (list, tuple)) and len(option) >= 2:
            label = str(option[0])
            score_value = option[1]
        else:
            continue

        if not label:
            continue

        try:
            score_int = int(score_value)
        except (TypeError, ValueError):
            continue

        normalized.append((str(label), score_int))

    if len(normalized) < QUESTION_OPTION_COUNT:
        return []
    return normalized[:QUESTION_OPTION_COUNT]


def _get_fallback_questions(i18n) -> List[Dict[str, object]]:
    """简化版风险问题（LLM生成失败时的后备方案），随当前语言切换。"""
    return [
        {
            "id": "q1",
            "prompt": i18n.t("recommendation.fallback_q1_prompt"),
            "options": [
                (i18n.t("recommendation.fallback_q1_option1"), 1),
                (i18n.t("recommendation.fallback_q1_option2"), 2),
                (i18n.t("recommendation.fallback_q1_option3"), 3),
            ],
        },
        {
            "id": "q2",
            "prompt": i18n.t("recommendation.fallback_q2_prompt"),
            "options": [
                (i18n.t("recommendation.fallback_q2_option1"), 1),
                (i18n.t("recommendation.fallback_q2_option2"), 2),
                (i18n.t("recommendation.fallback_q2_option3"), 3),
            ],
        },
    ]


@st.cache_data(show_spinner=False)
def _generate_cached_recommendation(
    transactions_dump: Tuple[Tuple[Tuple[str, object], ...], ...],
    responses_tuple: Tuple[Tuple[str, int], ...],
    goal: str,
    locale: str,
) -> Dict[str, object]:
    """Cacheable wrapper producing recommendation payload."""
    service = RecommendationService()
    transactions = [Transaction(**dict(entry)) for entry in transactions_dump]
    responses = dict(responses_tuple)
    result = service.generate(
        transactions=transactions,
        responses=responses,
        investment_goal=goal,
        locale=locale,
    )
    recs = result.get("recommendations", [])
    serialized = []
    for rec in recs:
        if isinstance(rec, Recommendation):
            serialized.append(rec.model_dump())
        elif isinstance(rec, dict):
            serialized.append(rec)
    result["recommendations"] = serialized
    return result


def _collect_risk_answers(
    questions: List[Dict[str, object]],
    guidance_header: str,
    goal_guidance: str,
) -> Tuple[Dict[str, int], str]:
    """收集风险评估问卷答案（问题由LLM动态生成）"""
    i18n = get_i18n()

    # 显示LLM生成的引导文案
    st.markdown(f"#### {guidance_header}")

    answers: Dict[str, int] = {}
    for idx, question in enumerate(questions):
        question_id = question.get("id") or f"advanced_{idx}"
        key = f"risk_advanced_{question_id}_{idx}"  # 确保key唯一
        prompt = (
            question.get("prompt")
            or question.get("question")
            or question.get("title")
            or f"问题 {idx + 1}"
        )

        normalized_options = _normalize_question_options(question.get("options", []))
        if not normalized_options:
            st.warning(i18n.t("recommendation.option_load_error", prompt=prompt))
            continue

        option_labels = [opt_label for opt_label, _ in normalized_options]
        selected = st.radio(
            prompt,
            options=option_labels,
            index=0,
            key=key,
            horizontal=False,
        )

        for opt_label, score in normalized_options:
            if opt_label == selected:
                answers[str(question_id)] = score
                break

    # 显示LLM生成的目标引导文案
    st.markdown(f"#### {goal_guidance}")
    goal = st.text_input(
        i18n.t("recommendation.prompt_goal"),
        placeholder=i18n.t("recommendation.goal_placeholder"),
        key="investment_goal_advanced",  # 区别于快速模式的key
    )
    return answers, goal


@st.cache_data(show_spinner=False)
def _generate_guidance_text(
    locale: str,
    monthly_avg: float,
    budget: float,
    investable: float,
) -> Tuple[str, str]:
    """生成引导文案（LLM动态生成）"""
    from utils.error_handling import UserFacingError, safe_call
    from openai import OpenAI
    from utils.i18n import I18n
    import os
    import json

    currency_symbol = I18n(locale).currency_symbol

    @safe_call(timeout=15, fallback=None, error_message="引导文案生成失败")
    def _call_llm():
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        prompt = f"""你是一位专业的理财顾问，正在引导用户进行风险评估和投资规划。

用户财务状况：
- 月均支出：{currency_symbol}{monthly_avg:.0f}
- 月度预算：{currency_symbol}{budget:.0f}
- 可投资金额：{currency_symbol}{investable:.0f}

请生成两段引导文案：
1. 风险评估引导（10-15字）：引导用户了解自己的风险承受能力
2. 投资目标引导（10-15字）：引导用户明确投资目标

要求：
- 语言自然、亲切、专业
- 不使用"步骤1"、"步骤2"这种机械化表述
- 根据用户财务状况提供针对性引导

返回JSON格式：
{{
  "risk_guidance": "风险评估引导文案",
  "goal_guidance": "投资目标引导文案"
}}
"""

        if locale == "en_US":
            prompt = f"""You are a professional financial advisor guiding users through risk assessment and investment planning.

User's financial situation:
- Monthly spending: {currency_symbol}{monthly_avg:.0f}
- Monthly budget: {currency_symbol}{budget:.0f}
- Investable amount: {currency_symbol}{investable:.0f}

Generate two guidance texts:
1. Risk assessment guidance (10-15 words): Guide users to understand their risk tolerance
2. Investment goal guidance (10-15 words): Guide users to clarify investment goals

Requirements:
- Natural, friendly, professional language
- Don't use mechanical phrases like "Step 1", "Step 2"
- Provide targeted guidance based on user's financial situation

Return JSON format:
{{
  "risk_guidance": "Risk assessment guidance text",
  "goal_guidance": "Investment goal guidance text"
}}
"""

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": "你是专业的理财顾问，擅长用简洁亲切的语言引导用户。",
                },
                {"role": "user", "content": prompt},
            ],
            timeout=15,
        )

        content = response.choices[0].message.content or ""
        # 清理markdown代码块
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        return data.get("risk_guidance", ""), data.get("goal_guidance", "")

    try:
        result = _call_llm()
    except UserFacingError:
        result = None
    if result and result[0] and result[1]:
        return result

    # 后备方案
    i18n = get_i18n()
    return (
        i18n.t("recommendation.guidance_fallback_risk"),
        i18n.t("recommendation.guidance_fallback_goal"),
    )


def _render_results(results: Dict[str, object]) -> None:
    i18n = get_i18n()
    recommendations_raw = results.get("recommendations", [])
    recommendations = [
        rec if isinstance(rec, Recommendation) else Recommendation(**rec)
        for rec in recommendations_raw
    ]
    profile: Dict[str, object] = results.get("financial_profile", {})  # type: ignore[assignment]
    risk_level: str = results.get("risk_level", "")  # type: ignore[assignment]

    st.success(i18n.t("recommendation.risk_result", risk=risk_level))

    st.subheader(i18n.t("recommendation.financial_profile_title"))
    col1, col2, col3 = st.columns(3)
    monthly_avg = float(profile.get("monthly_average", 0.0) or 0.0)
    volatility = float(profile.get("spending_volatility", 0.0) or 0.0)
    investable = float(profile.get("investable_amount", 0.0) or 0.0)
    with col1:
        st.metric(
            i18n.t("recommendation.metric_monthly_avg"),
            f"{i18n.currency_symbol}{monthly_avg:,.0f}",
        )
    with col2:
        st.metric(
            i18n.t("recommendation.metric_investable"),
            f"{i18n.currency_symbol}{investable:,.0f}",
        )
    with col3:
        st.metric(
            i18n.t("recommendation.metric_volatility"), f"{volatility * 100:.1f}%"
        )

    breakdown: Dict[str, float] = profile.get("category_breakdown", {})  # type: ignore[assignment]
    if breakdown:
        st.subheader(i18n.t("recommendation.category_breakdown_title"))
        df = pd.DataFrame(
            [
                {"category": cat, "share": share * 100}
                for cat, share in breakdown.items()
            ]
        )
        fig = px.bar(
            df,
            x="category",
            y="share",
            text="share",
            labels={
                "category": i18n.t("spending.label_category"),
                "share": i18n.t("recommendation.label_ratio"),
            },
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(yaxis_title=i18n.t("recommendation.label_ratio"))
        st.plotly_chart(fig, **responsive_width_kwargs(st.plotly_chart))

    st.subheader(i18n.t("recommendation.recommendation_list_title"))
    for rec in recommendations:
        st.markdown(f"### {rec.title}")
        # Escape literal "$" before rendering: with two-or-more dollar
        # amounts in one sentence (en_US locale), Streamlit's markdown
        # renderer treats the pair as a LaTeX math span and mangles the text.
        st.write(rec.summary.replace("$", "\\$"))
        for idx, step in enumerate(rec.rationale_steps, start=1):
            escaped_step = step.replace("$", "\\$")
            st.write(f"{idx}. {escaped_step}")

    # 详细报告生成部分
    st.markdown("---")
    st.subheader(i18n.t("recommendation.detailed_report_header"))
    st.caption(i18n.t("recommendation.detailed_report_caption"))

    if st.button(
        i18n.t("recommendation.btn_generate_detailed"),
        type="primary",
        key="generate_detailed_report",
    ):
        # 从session_state获取必要数据
        transactions = session_utils.get_transactions()
        responses = st.session_state.get("risk_responses", {})
        investment_goal = st.session_state.get("investment_goal", "")
        risk_profile_key = st.session_state.get("risk_profile_key", "balanced")

        with st.spinner(i18n.t("recommendation.spinner_detailed_report")):
            service = RecommendationService()
            detailed_report = service.generate_detailed_report(
                transactions=transactions,
                responses=responses,
                investment_goal=investment_goal,
                risk_profile=risk_profile_key,
                metrics=profile,  # type: ignore[arg-type]
                locale=st.session_state.get("locale", "en_US"),
            )

            if detailed_report:
                st.session_state["detailed_financial_report"] = detailed_report
                st.success(i18n.t("recommendation.detailed_report_success"))
            else:
                st.error(i18n.t("recommendation.detailed_report_error"))

    # 显示已生成的详细报告
    if (
        "detailed_financial_report" in st.session_state
        and st.session_state["detailed_financial_report"]
    ):
        st.markdown("---")
        st.markdown(i18n.t("recommendation.detailed_report_title"))

        # 提供下载按钮
        report_content = st.session_state["detailed_financial_report"]
        st.download_button(
            label=i18n.t("recommendation.btn_download_full"),
            data=report_content,
            file_name=f"financial_report_{pd.Timestamp.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            key="download_report",
        )

        # 渲染Markdown报告
        st.markdown(report_content)


def render() -> None:
    """Render investment recommendation workflow with XAI explanation."""
    i18n = get_i18n()
    st.title(i18n.t("recommendation.title"))
    st.write(i18n.t("recommendation.subtitle"))

    transactions = session_utils.get_transactions()
    if not transactions:
        st.warning(i18n.t("recommendation.require_upload"))
        return

    # 显示财务健康卡片（整合预算与支出）
    render_financial_health_card(transactions)

    # 获取用户预算和财务状况
    budget = get_monthly_budget()
    locale = st.session_state.get("locale", "en_US")

    # === 简化流程：单步输入模式 ===
    st.markdown("---")
    st.markdown(i18n.t("recommendation.quick_mode_title"))
    st.caption(i18n.t("recommendation.quick_mode_caption"))

    # 智能目标输入（带示例）
    goal_input = st.text_area(
        i18n.t("recommendation.goal_input_label"),
        placeholder=i18n.t("recommendation.goal_input_placeholder"),
        height=120,
        key="quick_goal_input",
    )

    # 风险偏好选择（简化为单选）
    risk_preference = st.radio(
        i18n.t("recommendation.risk_preference_label"),
        options=[
            i18n.t("recommendation.risk_option_conservative"),
            i18n.t("recommendation.risk_option_balanced"),
            i18n.t("recommendation.risk_option_aggressive"),
        ],
        index=1,
        key="quick_risk_preference",
        horizontal=True,
    )

    # 一键生成详细报告
    if st.button(
        i18n.t("recommendation.btn_generate_professional"),
        type="primary",
        disabled=not goal_input.strip(),
        key="generate_quick_report",
    ):
        # 映射风险偏好到profile key
        if "保守" in risk_preference or "Conservative" in risk_preference:
            risk_profile_key = "conservative"
        elif "进取" in risk_preference or "Aggressive" in risk_preference:
            risk_profile_key = "aggressive"
        else:
            risk_profile_key = "balanced"

        with st.spinner(i18n.t("recommendation.spinner_quick_report")):
            try:
                service = RecommendationService()

                # 先分析财务指标
                metrics = service.analyze_transactions(transactions)

                # 直接生成详细报告（跳过问卷流程）
                detailed_report = service.generate_detailed_report(
                    transactions=transactions,
                    responses={},  # 无需问卷数据
                    investment_goal=goal_input.strip(),
                    risk_profile=risk_profile_key,
                    metrics=metrics,
                    locale=locale,
                )

                if detailed_report:
                    st.session_state["detailed_financial_report"] = detailed_report
                    st.session_state["investment_goal"] = goal_input.strip()
                    st.session_state["risk_profile_key"] = risk_profile_key
                    st.success(i18n.t("recommendation.report_generated_short"))
                    st.rerun()
                else:
                    st.error(i18n.t("recommendation.report_failed_network"))
            except Exception as exc:
                st.error(i18n.t("recommendation.generation_exception", error=str(exc)))

    # 显示已生成的详细报告（仅当尚未有资产配置结果时避免重复展示）
    if (
        "detailed_financial_report" in st.session_state
        and st.session_state["detailed_financial_report"]
        and not st.session_state.get("recommendation_explanation")
    ):
        st.markdown("---")
        st.markdown(i18n.t("recommendation.detailed_report_title_short"))

        # 提供下载按钮
        report_content = st.session_state["detailed_financial_report"]
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(
                i18n.t(
                    "recommendation.goal_summary_caption",
                    goal=st.session_state.get("investment_goal", ""),
                    risk=st.session_state.get("risk_profile_key", ""),
                )
            )
        with col2:
            st.download_button(
                label=i18n.t("recommendation.btn_download_short"),
                data=report_content,
                file_name=f"financial_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                key="download_report",
                **responsive_width_kwargs(st.download_button),
            )

        # 渲染Markdown报告
        st.markdown(report_content)

    # 已存在的资产配置结果（来自高级模式）
    persisted_results = st.session_state.get("recommendation_explanation")
    if persisted_results:
        st.markdown("---")
        _render_results(persisted_results)

    # === 高级模式：保留完整问卷流程（折叠） ===
    with st.expander(
        i18n.t("recommendation.advanced_mode_label"),
        expanded=False,
    ):
        st.caption(i18n.t("recommendation.advanced_mode_caption"))

        # 生成个性化问题（LLM动态生成）
        with st.spinner(i18n.t("common.loading")):
            service = RecommendationService()
            questions = service.generate_personalized_questions(
                transactions=transactions,
                budget=budget,
                locale=locale,
            )

        # 如果LLM生成失败，使用后备问题
        if not questions:
            st.info(i18n.t("recommendation.fallback_questionnaire_notice"))
            questions = _get_fallback_questions(i18n)

        # 计算财务指标用于生成引导文案
        metrics = service.analyze_transactions(transactions)
        monthly_avg = float(metrics.get("monthly_average", 0.0) or 0.0)
        investable = float(metrics.get("investable_amount", 0.0) or 0.0)

        # 生成引导文案
        risk_guidance, goal_guidance = _generate_guidance_text(
            locale=locale,
            monthly_avg=monthly_avg,
            budget=budget,
            investable=investable,
        )

        # 收集用户答案
        answers, goal = _collect_risk_answers(questions, risk_guidance, goal_guidance)
        responses_tuple = tuple(sorted(answers.items()))
        transactions_dump = tuple(
            tuple(sorted(tx.model_dump().items(), key=lambda item: item[0]))
            for tx in transactions
        )

        st.subheader(i18n.t("recommendation.step3"))
        if st.button(
            i18n.t("recommendation.button_generate"),
            type="secondary",
            key="advanced_generate",
        ):
            try:
                with st.spinner(i18n.t("common.loading_recommendation")):
                    results = _generate_cached_recommendation(
                        transactions_dump,
                        responses_tuple,
                        goal,
                        locale,
                    )
            except Exception as exc:
                st.error(f"{i18n.t('errors.structuring_fail')} ({exc})")
                return

            # 保存数据到session
            st.session_state["risk_responses"] = answers
            st.session_state["investment_goal"] = goal
            risk_level_str = results.get("risk_level", "")
            if "保守" in risk_level_str or "conservative" in risk_level_str.lower():
                st.session_state["risk_profile_key"] = "conservative"
            elif "进取" in risk_level_str or "aggressive" in risk_level_str.lower():
                st.session_state["risk_profile_key"] = "aggressive"
            else:
                st.session_state["risk_profile_key"] = "balanced"

            recommendation_payload = [dict(item) for item in results["recommendations"]]
            set_product_recommendations(recommendation_payload)
            st.session_state["recommendation_explanation"] = results
            st.rerun()


if __name__ == "__main__":  # pragma: no cover - streamlit entry point
    render()
