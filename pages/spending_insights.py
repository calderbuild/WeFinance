"""Streamlit page for spending analytics and visualisations."""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from models.entities import SpendingInsight, Transaction
from modules.analysis import (
    calculate_category_totals,
    calculate_spending_trend,
    compute_anomaly_report,
    generate_insights,
)
from utils import session as session_utils


@st.cache_data(show_spinner=False)
def _prepare_dashboard_data(
    transactions_dump: Tuple[Tuple[Tuple[str, object], ...], ...],
    whitelist: Tuple[str, ...],
    base_threshold: float,
) -> dict:
    """Pre-compute analytics outputs for the dashboard."""
    transactions = [Transaction(**dict(entry)) for entry in transactions_dump]

    category_totals = calculate_category_totals(transactions)
    trend_daily = calculate_spending_trend(transactions, frequency="D")
    trend_monthly = calculate_spending_trend(transactions, frequency="M")
    anomaly_report = compute_anomaly_report(
        transactions,
        base_threshold=base_threshold,
        whitelist_merchants=whitelist,
    )
    insights = generate_insights(transactions)

    return {
        "category_totals": category_totals,
        "trend_daily": trend_daily,
        "trend_monthly": trend_monthly,
        "anomaly_report": anomaly_report,
        "insights": [ins.model_dump() for ins in insights],
    }


def _render_active_anomalies(anomalies: List[dict], threshold_used: float) -> None:
    """Display active anomalies with action buttons."""
    if anomalies:
        st.subheader("⚠️ 待确认的异常支出")
        st.caption(f"当前检测阈值：±{threshold_used:.1f} σ")
    for anomaly in anomalies:
        date_str = anomaly.get("date") or "-"
        merchant = anomaly.get("merchant", "未知商户")
        amount = anomaly.get("amount", 0.0)
        reason = anomaly.get("reason", "异常支出")
        status = anomaly.get("status", "new")

        box = st.warning if status == "new" else st.info
        with box(f"{date_str} | {merchant} | ¥{amount:.2f} | {reason}"):
            cols = st.columns(2)
            confirm_key = f"confirm_{anomaly['transaction_id']}"
            fraud_key = f"fraud_{anomaly['transaction_id']}"

            if cols[0].button("确认本人消费", key=confirm_key):
                session_utils.record_anomaly_feedback(anomaly, "confirmed")
                remaining = [
                    item
                    for item in session_utils.get_active_anomalies()
                    if item.get("transaction_id") != anomaly["transaction_id"]
                ]
                session_utils.update_anomaly_state(active=remaining)
                st.toast("已标记为本人消费 ✅")
                st.experimental_rerun()

            if cols[1].button("标记为疑似欺诈", key=fraud_key):
                session_utils.record_anomaly_feedback(anomaly, "fraud")
                remaining = [
                    item
                    for item in session_utils.get_active_anomalies()
                    if item.get("transaction_id") != anomaly["transaction_id"]
                ]
                session_utils.update_anomaly_state(active=remaining)
                st.toast("已标记为疑似欺诈 ⚠️")
                st.experimental_rerun()


def _render_sidebar_controls(trusted_merchants: List[str]) -> None:
    """Render merchant whitelist management and anomaly history in sidebar."""
    with st.sidebar.expander("✅ 信任商户管理", expanded=False):
        with st.form("trusted_merchants_form"):
            new_merchant = st.text_input("新增信任商户名称")
            added = st.form_submit_button("添加白名单商户")
            if added:
                session_utils.add_trusted_merchant(new_merchant)
                st.toast(f"已添加「{new_merchant}」至白名单")
                st.experimental_rerun()

        if trusted_merchants:
            st.caption("当前白名单：")
            for idx, merchant in enumerate(trusted_merchants, start=1):
                cols = st.columns([0.8, 0.2])
                cols[0].write(f"{idx}. {merchant}")
                if cols[1].button("移除", key=f"remove_whitelist_{idx}"):
                    session_utils.remove_trusted_merchant(merchant)
                    st.toast(f"已移除「{merchant}」")
                    st.experimental_rerun()
        else:
            st.info("暂无白名单商户，检测将覆盖所有交易。")

    history = session_utils.get_anomaly_history()
    with st.sidebar.expander("📚 异常反馈历史", expanded=False):
        if not history:
            st.write("暂无历史记录。")
        else:
            for record in history:
                merchant = record.get("merchant", "未知商户")
                amount = record.get("amount", 0.0)
                status = record.get("status", "confirmed")
                date_str = record.get("date", "-")
                label = "✅ 本人消费" if status == "confirmed" else "🚨 疑似欺诈"
                st.write(f"{date_str} | {merchant} | ¥{amount:.2f} | {label}")


def render() -> None:
    """Render enhanced analytics dashboard with Plotly visualisations."""
    st.title("📊 消费分析仪表盘")
    st.write("查看分类占比、时间趋势、异常支出以及AI生成的关键洞察。")

    transactions = session_utils.get_transactions()
    if not transactions:
        st.warning("请先上传账单，再回到该页面查看自动生成的分析报告。")
        return

    trusted_merchants = session_utils.get_trusted_merchants()
    _render_sidebar_controls(trusted_merchants)

    serialized = tuple(
        tuple(sorted(tx.model_dump().items(), key=lambda item: item[0]))
        for tx in transactions
    )
    whitelist_tuple = tuple(sorted(trusted_merchants))
    results = _prepare_dashboard_data(serialized, whitelist_tuple, base_threshold=2.5)

    totals = results["category_totals"]
    trend_daily: pd.DataFrame = results["trend_daily"]
    trend_monthly: pd.DataFrame = results["trend_monthly"]
    anomaly_report = results["anomaly_report"]
    insights_payload = results["insights"]
    insights = [SpendingInsight(**ins) for ins in insights_payload]

    active_anomalies = session_utils.sync_anomaly_state(anomaly_report)

    anomaly_message = anomaly_report.get("message")
    if anomaly_message:
        st.info(anomaly_message)

    _render_active_anomalies(active_anomalies, anomaly_report.get("threshold_used", 2.5))

    if totals:
        with st.expander("📈 分类支出占比与柱状图", expanded=False):
            pie_df = pd.DataFrame(
                [{"category": cat, "amount": amt} for cat, amt in totals.items()]
            )
            fig_pie = px.pie(
                pie_df,
                names="category",
                values="amount",
                title="分类占比",
                hole=0.4,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

            bar_df = pie_df.sort_values("amount", ascending=False)
            fig_bar = px.bar(
                bar_df,
                x="category",
                y="amount",
                text="amount",
                title="各分类总支出",
                labels={"category": "分类", "amount": "金额（元）"},
            )
            fig_bar.update_traces(texttemplate="¥%{text:.2f}", textposition="outside")
            fig_bar.update_layout(yaxis_title="金额（元）")
            st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("📅 支出趋势图", expanded=False):
        if not trend_daily.empty:
            fig_line = px.line(
                trend_daily,
                x="period",
                y="amount",
                markers=True,
                title="每日支出趋势",
                labels={"period": "日期", "amount": "金额（元）"},
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("每日趋势数据不足，待有更多交易后展示。")

        if not trend_monthly.empty and len(trend_monthly) > 1:
            fig_month = px.line(
                trend_monthly,
                x="period",
                y="amount",
                markers=True,
                title="月度支出趋势",
                labels={"period": "月份", "amount": "金额（元）"},
            )
            st.plotly_chart(fig_month, use_container_width=True)

    with st.expander("🤖 AI消费洞察", expanded=False):
        if insights:
            for insight in insights:
                st.success(f"**{insight.title}**：{insight.detail}")
        else:
            st.info("暂无洞察。敬请期待下一版本的深入分析能力。")
