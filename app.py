"""Streamlit entry point for the WeFinance Copilot prototype."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Callable

import streamlit as st

from models.entities import Transaction
from pages import (
    advisor_chat,
    bill_upload,
    business_profile,
    investment_recs,
    spending_insights,
)
from modules.analysis import compute_anomaly_report
from utils import session as session_utils
from utils.session import (
    get_i18n,
    init_session_state,
    reset_session_state,
    switch_locale,
)
from utils.storage import clear_all_storage, load_from_storage
from utils.ui_components import responsive_width_kwargs
from utils.design_system import (
    inject_global_styles,
    render_hero_banner,
    COLORS,
    FONTS,
    SPACING,
    RADIUS,
)

logger = logging.getLogger(__name__)


def restore_data_from_storage() -> None:
    """Hydrate Streamlit session state from persisted storage."""
    if st.session_state.get("data_restored", False):
        return

    try:
        transactions_payload = load_from_storage("transactions", []) or []
        if transactions_payload:
            transactions: list[Transaction] = []
            for entry in transactions_payload:
                if isinstance(entry, Transaction):
                    transactions.append(entry)
                elif isinstance(entry, dict):
                    transactions.append(Transaction(**entry))
            st.session_state["transactions"] = [
                txn.model_dump(mode="json") for txn in transactions
            ]
            logger.info("Restored %d transactions from storage", len(transactions))

        budget = load_from_storage("monthly_budget", 5000.0)
        if budget is not None:
            st.session_state["monthly_budget"] = float(budget)

        chat_history = load_from_storage("chat_history", []) or []
        st.session_state["chat_history"] = list(chat_history)

        analysis_summary = load_from_storage("analysis_summary", None)
        if analysis_summary:
            st.session_state["analysis_summary"] = analysis_summary

        product_recommendations = load_from_storage("product_recommendations", None)
        if product_recommendations:
            st.session_state["product_recommendations"] = product_recommendations

        st.session_state["data_restored"] = True
        logger.info("Data restoration completed")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to restore data from storage: %s", exc)
        st.session_state["data_restored"] = True


restore_data_from_storage()

st.set_page_config(
    page_title="WeFinance Copilot",
    page_icon="💰",
    layout="wide",
    menu_items={
        "Get help": "mailto:team@wefinance.ai",
        "Report a bug": "https://github.com/wefinance/issues",
        "About": get_i18n().t("app.menu_about"),
    },
)

# Inject global design system styles
inject_global_styles()


@st.cache_data
def get_comparison_table(locale: str):
    """Cache comparison table data to avoid recreation on each render."""
    import pandas as pd
    from utils.i18n import I18n

    # 直接创建临时I18n实例用于翻译（函数已被缓存，仅执行一次）
    i18n = I18n(locale)
    comparison_data = {
        i18n.t("app.comparison_feature"): [
            i18n.t("app.comparison_ocr_rate"),
            i18n.t("app.comparison_processing"),
            i18n.t("app.comparison_multilingual"),
            i18n.t("app.comparison_ai_advisor"),
        ],
        i18n.t("app.comparison_wefinance"): [
            i18n.t("app.comparison_ocr_wefinance"),
            i18n.t("app.comparison_processing_wefinance"),
            i18n.t("app.comparison_multilingual_wefinance"),
            i18n.t("app.comparison_ai_wefinance"),
        ],
        i18n.t("app.comparison_traditional"): [
            i18n.t("app.comparison_ocr_traditional"),
            i18n.t("app.comparison_processing_traditional"),
            i18n.t("app.comparison_multilingual_traditional"),
            i18n.t("app.comparison_ai_traditional"),
        ],
    }
    return pd.DataFrame(comparison_data)


def _render_home() -> None:
    """Render the landing page with value proposition and card-based navigation."""
    i18n = get_i18n()

    # Modern Finance Luxury hero banner with glassmorphism
    st.markdown(
        f"""
        <div class="wf-hero" style="margin-bottom: {SPACING["xl"]};">
            <div style="position: relative; z-index: 1;">
                <div style="
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                    background: {COLORS["accent_muted"]};
                    padding: 0.375rem 0.75rem;
                    border-radius: 9999px;
                    font-size: {FONTS["size_xs"]};
                    color: {COLORS["accent"]};
                    font-weight: 600;
                    letter-spacing: 0.05em;
                    margin-bottom: {SPACING["md"]};
                ">
                    <span style="
                        width: 6px;
                        height: 6px;
                        background: {COLORS["accent"]};
                        border-radius: 50%;
                        animation: wf-pulse-glow 2s ease-in-out infinite;
                    "></span>
                    {i18n.t("app.badge_ai_powered")}
                </div>
                <h1 style="
                    font-family: {FONTS["heading"]};
                    font-size: {FONTS["size_4xl"]};
                    font-weight: 400;
                    color: {COLORS["text_primary"]};
                    margin: 0 0 {SPACING["sm"]} 0;
                    letter-spacing: -0.02em;
                    line-height: 1.2;
                ">
                    {i18n.t("app.value_banner_title")}
                </h1>
                <p style="
                    font-size: {FONTS["size_lg"]};
                    color: {COLORS["text_secondary"]};
                    margin: 0;
                    max-width: 600px;
                    line-height: 1.6;
                ">
                    {i18n.t("app.value_banner_subtitle")}
                </p>
                <div style="
                    display: flex;
                    gap: {SPACING["md"]};
                    margin-top: {SPACING["lg"]};
                    flex-wrap: wrap;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                        font-size: {FONTS["size_sm"]};
                        color: {COLORS["text_secondary"]};
                    ">
                        <span style="color: {COLORS["success"]};">●</span>
                        {i18n.t("app.feature_ocr_accuracy")}
                    </div>
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                        font-size: {FONTS["size_sm"]};
                        color: {COLORS["text_secondary"]};
                    ">
                        <span style="color: {COLORS["primary"]};">●</span>
                        {i18n.t("app.feature_anomaly_detection")}
                    </div>
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                        font-size: {FONTS["size_sm"]};
                        color: {COLORS["text_secondary"]};
                    ">
                        <span style="color: {COLORS["accent"]};">●</span>
                        {i18n.t("app.feature_explainable_ai")}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Anomaly warnings (prioritized above metrics)
    active_anomalies = session_utils.get_active_anomalies()
    anomaly_message = st.session_state.get("anomaly_message", "")

    if active_anomalies:
        st.error(i18n.t("app.anomaly_warning"))
        for anomaly in active_anomalies[:3]:
            date_str = anomaly.get("date", "-")
            merchant = anomaly.get(
                "merchant",
                i18n.t("common.unknown_merchant"),
            )
            amount = anomaly.get("amount", 0.0)
            reason = anomaly.get("reason", "")
            with st.container():
                st.markdown(
                    f"**{i18n.t('app.anomaly_info', date=date_str, merchant=merchant, amount=float(amount), currency=i18n.currency_symbol)}**"
                )
                if reason:
                    st.caption(reason)
                cols = st.columns(2)
                confirm_key = f"home_confirm_{anomaly['transaction_id']}"
                fraud_key = f"home_fraud_{anomaly['transaction_id']}"

                if cols[0].button(i18n.t("common.btn_confirm"), key=confirm_key):
                    session_utils.record_anomaly_feedback(anomaly, "confirmed")
                    remaining = [
                        item
                        for item in session_utils.get_active_anomalies()
                        if item.get("transaction_id") != anomaly["transaction_id"]
                    ]
                    session_utils.update_anomaly_state(active=remaining)
                    st.toast(i18n.t("common.toast_confirmed"))
                    st.rerun()

                if cols[1].button(i18n.t("common.btn_mark_fraud"), key=fraud_key):
                    session_utils.record_anomaly_feedback(anomaly, "fraud")
                    remaining = [
                        item
                        for item in session_utils.get_active_anomalies()
                        if item.get("transaction_id") != anomaly["transaction_id"]
                    ]
                    session_utils.update_anomaly_state(active=remaining)
                    st.toast(i18n.t("common.toast_fraud"))
                    st.rerun()
        st.divider()
    elif anomaly_message:
        st.info(anomaly_message)

    # Calculate metrics
    transactions = session_utils.get_transactions()
    monthly_budget = session_utils.get_monthly_budget()
    chat_history = st.session_state.get("chat_history", [])

    total_spent = sum(txn.amount for txn in transactions)
    budget_remaining = monthly_budget - total_spent
    usage_rate = (total_spent / monthly_budget * 100) if monthly_budget > 0 else 0

    # 3-column metrics cards with new design
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
        <div class="wf-metric-card">
            <div style="
                font-size: {FONTS["size_xs"]};
                color: {COLORS["text_muted"]};
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: {SPACING["xs"]};
            ">{i18n.t("app.metric_transactions_label")}</div>
            <div style="
                font-family: {FONTS["mono"]};
                font-size: {FONTS["size_3xl"]};
                font-weight: 600;
                color: {COLORS["text_primary"]};
                margin-bottom: {SPACING["sm"]};
            ">{len(transactions)}<span style="font-size: {FONTS["size_lg"]}; color: {COLORS["text_secondary"]}; margin-left: 0.25rem;">{i18n.t("app.unit_suffix_transactions")}</span></div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button(
            i18n.t("app.btn_upload_bills"),
            key="home_upload_btn",
            type="primary",
            **responsive_width_kwargs(st.button),
        ):
            st.session_state["selected_page"] = "bill_upload"
            st.rerun()

    with col2:
        remaining_color = (
            COLORS["success"] if budget_remaining >= 0 else COLORS["error"]
        )
        st.markdown(
            f"""
        <div class="wf-metric-card">
            <div style="
                font-size: {FONTS["size_xs"]};
                color: {COLORS["text_muted"]};
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: {SPACING["xs"]};
            ">{i18n.t("app.metric_budget_label")}</div>
            <div style="
                font-family: {FONTS["mono"]};
                font-size: {FONTS["size_3xl"]};
                font-weight: 600;
                color: {remaining_color};
                margin-bottom: {SPACING["xs"]};
            ">{i18n.currency_symbol}{budget_remaining:,.0f}</div>
            <div style="
                font-size: {FONTS["size_sm"]};
                color: {COLORS["text_secondary"]};
            ">{i18n.t("app.label_spent")}: {i18n.currency_symbol}{total_spent:,.0f} ({usage_rate:.0f}%)</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button(
            i18n.t("app.btn_view_analysis"),
            key="home_analysis_btn",
            **responsive_width_kwargs(st.button),
        ):
            st.session_state["selected_page"] = "spending_insights"
            st.rerun()

    with col3:
        st.markdown(
            f"""
        <div class="wf-metric-card">
            <div style="
                font-size: {FONTS["size_xs"]};
                color: {COLORS["text_muted"]};
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: {SPACING["xs"]};
            ">{i18n.t("app.metric_chat_label")}</div>
            <div style="
                font-family: {FONTS["mono"]};
                font-size: {FONTS["size_3xl"]};
                font-weight: 600;
                color: {COLORS["primary"]};
                margin-bottom: {SPACING["sm"]};
            ">{len(chat_history)}<span style="font-size: {FONTS["size_lg"]}; color: {COLORS["text_secondary"]}; margin-left: 0.25rem;">{i18n.t("app.unit_suffix_chats")}</span></div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button(
            i18n.t("app.btn_start_chat"),
            key="home_chat_btn",
            **responsive_width_kwargs(st.button),
        ):
            st.session_state["selected_page"] = "advisor_chat"
            st.rerun()

    # Comparison table (cached)
    st.markdown("---")
    st.subheader(i18n.t("app.comparison_title"))

    current_locale = st.session_state.get("locale", "en_US")
    comparison_df = get_comparison_table(current_locale)
    st.dataframe(
        comparison_df, **responsive_width_kwargs(st.dataframe), hide_index=True
    )

    # Get recommendations button
    st.markdown("---")
    col_invest = st.columns([1, 2, 1])[1]
    with col_invest:
        if st.button(
            i18n.t("app.btn_get_recommendations"),
            key="home_invest_btn",
            type="secondary",
            **responsive_width_kwargs(st.button),
        ):
            st.session_state["selected_page"] = "investment_recs"
            st.rerun()

    # Project info footer
    st.markdown("---")
    st.info(i18n.t("app.info_note"))


PAGES: dict[str, Callable[[], None]] = {
    "home": _render_home,
    "bill_upload": bill_upload.render,
    "spending_insights": spending_insights.render,
    "business_profile": business_profile.render,
    "advisor_chat": advisor_chat.render,
    "investment_recs": investment_recs.render,
}


def _refresh_anomaly_state() -> None:
    """Recompute anomaly detection results only when transaction data changes."""
    i18n = get_i18n()
    transactions = session_utils.get_transactions()
    if not transactions:
        session_utils.update_anomaly_state(
            active=[],
            message=i18n.t("app.no_transaction_data"),
        )
        return

    # Performance optimization: Only recompute if data or locale changed
    current_hash = hash(
        (i18n.locale, tuple((t.id, t.amount, t.date) for t in transactions))
    )
    last_hash = st.session_state.get("anomaly_last_hash")

    if current_hash == last_hash:
        # Data unchanged, skip expensive computation
        return

    report = compute_anomaly_report(
        transactions,
        whitelist_merchants=session_utils.get_trusted_merchants(),
        locale=i18n.locale,
    )
    session_utils.sync_anomaly_state(report)
    st.session_state["anomaly_last_hash"] = current_hash


def main() -> None:
    """Application bootstrap."""
    init_session_state()
    _refresh_anomaly_state()
    i18n = get_i18n()

    with st.sidebar:
        # Sidebar header with brand styling
        st.markdown(
            f"""
        <div style="
            padding: {SPACING["md"]} 0;
            border-bottom: 1px solid {COLORS["border"]};
            margin-bottom: {SPACING["md"]};
        ">
            <h2 style="
                font-family: {FONTS["heading"]};
                font-size: {FONTS["size_xl"]};
                color: {COLORS["text_primary"]};
                margin: 0;
                display: flex;
                align-items: center;
                gap: {SPACING["sm"]};
            ">
                <span style="
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 32px;
                    height: 32px;
                    background: {COLORS["gradient_primary"]};
                    border-radius: {RADIUS["md"]};
                    font-size: 1rem;
                ">💰</span>
                WeFinance
            </h2>
            <p style="
                font-size: {FONTS["size_xs"]};
                color: {COLORS["text_muted"]};
                margin: {SPACING["xs"]} 0 0 0;
                letter-spacing: 0.05em;
            ">AI-Powered Financial Copilot</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 语言切换（紧凑）
        locale_labels = {"zh_CN": "中文", "en_US": "English"}
        current_locale = st.session_state.get("locale", "en_US")
        locale_display = locale_labels.get(current_locale, "English")
        selected_display = st.selectbox(
            i18n.t("app.language_selector_label"),
            options=list(locale_labels.values()),
            index=list(locale_labels.values()).index(locale_display),
        )
        selected_locale = next(
            key for key, value in locale_labels.items() if value == selected_display
        )
        if selected_locale != current_locale:
            switch_locale(selected_locale)
            st.rerun()

        # ============ 智能导航引导 (紧凑版) ============
        st.markdown("---")
        transactions = session_utils.get_transactions()
        has_transactions = len(transactions) > 0
        has_chat_history = len(st.session_state.get("chat_history", [])) > 0
        has_analysis = len(st.session_state.get("analysis_summary", [])) > 0
        has_recommendations = (
            len(st.session_state.get("product_recommendations", [])) > 0
        )

        steps_completed = sum(
            [has_transactions, has_analysis, has_chat_history, has_recommendations]
        )
        total_steps = 4
        progress_percentage = steps_completed / total_steps

        # 紧凑进度显示
        st.markdown(
            f"**{i18n.t('app.progress_label_short')}** {steps_completed}/{total_steps}"
        )
        st.progress(progress_percentage)

        # 智能建议下一步（精简）
        if not has_transactions:
            next_step = i18n.t("app.next_step_upload")
            next_page_key = "bill_upload"
        elif not has_analysis:
            next_step = i18n.t("app.next_step_insights")
            next_page_key = "spending_insights"
        elif not has_chat_history:
            next_step = i18n.t("app.next_step_chat")
            next_page_key = "advisor_chat"
        elif not has_recommendations:
            next_step = i18n.t("app.next_step_invest")
            next_page_key = "investment_recs"
        else:
            next_step = i18n.t("app.next_step_done")
            next_page_key = None

        if next_page_key and st.button(
            next_step,
            key="smart_nav_button",
            **responsive_width_kwargs(st.button),
            type="primary",
        ):
            st.session_state["selected_page"] = next_page_key
            st.rerun()

        st.markdown("---")

        # 精简导航（移除首页，保留4个核心步骤 + 1个补充视角）
        nav_labels = {
            "bill_upload": f"{'✅' if has_transactions else '1️⃣'} "
            + i18n.t("app.nav_short_upload"),
            "spending_insights": f"{'✅' if has_analysis else '2️⃣'} "
            + i18n.t("app.nav_short_analysis"),
            "business_profile": "📈 " + i18n.t("app.nav_short_business"),
            "advisor_chat": f"{'✅' if has_chat_history else '3️⃣'} "
            + i18n.t("app.nav_short_chat"),
            "investment_recs": f"{'✅' if has_recommendations else '4️⃣'} "
            + i18n.t("app.nav_short_invest"),
        }
        radio_options = list(nav_labels.values())
        selected_page = st.session_state.get("selected_page", "home")
        if selected_page not in nav_labels:
            selected_page = "bill_upload"  # 默认第一步
        default_index = radio_options.index(nav_labels[selected_page])
        selection_label = st.radio(
            "📍 " + i18n.t("app.nav_label_short"),
            radio_options,
            index=default_index,
            label_visibility="collapsed",  # 隐藏标签，进一步节省空间
        )
        selection = next(
            key for key, value in nav_labels.items() if value == selection_label
        )
        st.session_state["selected_page"] = selection

        # ============ 紧凑Budget设置 ============
        st.markdown("---")
        current_budget = session_utils.get_monthly_budget()
        new_budget = st.number_input(
            "💰 " + i18n.t("app.budget_label_short"),
            min_value=0.0,
            max_value=1000000.0,
            value=float(current_budget),
            step=500.0,
            format="%.0f",
            key="global_budget_sidebar",
        )
        if new_budget != current_budget:
            session_utils.set_monthly_budget(new_budget)

        # ============ 紧凑数据管理 ============
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "📥",
                help=i18n.t("app.export_help_short"),
                key="export_data_btn",
                **responsive_width_kwargs(st.button),
            ):
                export_data = {
                    "transactions": load_from_storage("transactions", []),
                    "monthly_budget": load_from_storage("monthly_budget", 5000.0),
                    "chat_history": load_from_storage("chat_history", []),
                    "analysis_summary": load_from_storage("analysis_summary", []),
                    "product_recommendations": load_from_storage(
                        "product_recommendations", []
                    ),
                    "export_time": datetime.now().isoformat(),
                }
                json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️",
                    data=json_data,
                    file_name=f"wefinance_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="download_json_btn",
                    **responsive_width_kwargs(st.download_button),
                )

        with col2:
            if st.button(
                "🗑️",
                help=i18n.t("app.clear_help_short"),
                key="clear_data_btn",
                **responsive_width_kwargs(st.button),
            ):
                if st.session_state.get("confirm_clear", False):
                    clear_all_storage()
                    protected_keys = {"selected_page", "locale", "data_restored"}
                    for state_key in list(st.session_state.keys()):
                        if state_key not in protected_keys:
                            del st.session_state[state_key]
                    st.session_state["confirm_clear"] = False
                    st.session_state["data_restored"] = False
                    st.rerun()
                else:
                    st.session_state["confirm_clear"] = True

        if st.session_state.get("confirm_clear"):
            st.caption("⚠️ " + i18n.t("app.confirm_clear_short"))

    render = PAGES.get(selection)
    if render is None:
        st.error(i18n.t("errors.page_missing"))
        return

    try:
        # Add loading indicator for better UX
        with st.spinner(i18n.t("app.loading_spinner")):
            render()
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("页面渲染失败：%s", exc)
        st.error(f"😥 {i18n.t('errors.render_failed')}")
        st.stop()


if __name__ == "__main__":
    main()
