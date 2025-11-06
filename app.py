"""Streamlit entry point for the WeFinance Copilot prototype."""

from __future__ import annotations

import logging
from typing import Callable

import streamlit as st

from pages import advisor_chat, bill_upload, investment_recs, spending_insights
from modules.analysis import compute_anomaly_report
from utils import session as session_utils
from utils.session import (
    get_i18n,
    init_session_state,
    reset_session_state,
    switch_locale,
)

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="WeFinance Copilot",
    page_icon="💰",
    layout="wide",
    menu_items={
        "Get help": "mailto:team@wefinance.ai",
        "Report a bug": "https://github.com/wefinance/issues",
        "About": "WeFinance Copilot — 让AI成为你的私人CFO。",
    },
)


def _render_home() -> None:
    """Render the landing page with quick project hints."""
    i18n = get_i18n()
    st.title("WeFinance Copilot")
    st.subheader(i18n.t("app.subtitle"))

    active_anomalies = session_utils.get_active_anomalies()
    anomaly_message = st.session_state.get("anomaly_message", "")

    if active_anomalies:
        st.error(i18n.t("app.anomaly_warning"))
        for anomaly in active_anomalies[:3]:
            date_str = anomaly.get("date", "-")
            merchant = anomaly.get("merchant", "未知商户")
            amount = anomaly.get("amount", 0.0)
            reason = anomaly.get("reason", "")
            with st.container():
                st.markdown(
                    f"**{i18n.t('app.anomaly_info', date=date_str, merchant=merchant, amount=float(amount))}**"
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
                    st.experimental_rerun()

                if cols[1].button(i18n.t("common.btn_mark_fraud"), key=fraud_key):
                    session_utils.record_anomaly_feedback(anomaly, "fraud")
                    remaining = [
                        item
                        for item in session_utils.get_active_anomalies()
                        if item.get("transaction_id") != anomaly["transaction_id"]
                    ]
                    session_utils.update_anomaly_state(active=remaining)
                    st.toast(i18n.t("common.toast_fraud"))
                    st.experimental_rerun()
        st.divider()
    elif anomaly_message:
        st.info(anomaly_message)

    st.markdown(
        "\n".join(
            [
                i18n.t("app.welcome"),
                "",
                i18n.t("app.feature_bill"),
                i18n.t("app.feature_analysis"),
                i18n.t("app.feature_chat"),
                i18n.t("app.feature_recs"),
            ]
        )
    )
    st.info(i18n.t("app.info_note"))


PAGES: dict[str, Callable[[], None]] = {
    "home": _render_home,
    "bill_upload": bill_upload.render,
    "spending_insights": spending_insights.render,
    "advisor_chat": advisor_chat.render,
    "investment_recs": investment_recs.render,
}


def _refresh_anomaly_state() -> None:
    """Recompute anomaly detection results to keep homepage提示最新。"""
    transactions = session_utils.get_transactions()
    if not transactions:
        session_utils.update_anomaly_state(
            active=[],
            message="暂无账单数据，上传后将自动开启异常检测。",
        )
        return

    report = compute_anomaly_report(
        transactions,
        whitelist_merchants=session_utils.get_trusted_merchants(),
    )
    session_utils.sync_anomaly_state(report)


def main() -> None:
    """Application bootstrap."""
    init_session_state()
    _refresh_anomaly_state()
    i18n = get_i18n()

    with st.sidebar:
        st.header(i18n.t("app.sidebar_header"))

        locale_labels = {
            "zh_CN": i18n.t("app.locale_zh"),
            "en_US": i18n.t("app.locale_en"),
        }
        current_locale = st.session_state.get("locale", "zh_CN")
        locale_display = locale_labels.get(current_locale, "中文")
        selected_display = st.selectbox(
            i18n.t("app.language_label"),
            options=list(locale_labels.values()),
            index=list(locale_labels.values()).index(locale_display),
        )
        selected_locale = next(
            key for key, value in locale_labels.items() if value == selected_display
        )
        if selected_locale != current_locale:
            switch_locale(selected_locale)
            st.experimental_rerun()

        nav_labels = {
            "home": i18n.t("navigation.home"),
            "bill_upload": i18n.t("navigation.bill_upload"),
            "spending_insights": i18n.t("navigation.spending_insights"),
            "advisor_chat": i18n.t("navigation.advisor_chat"),
            "investment_recs": i18n.t("navigation.investment_recs"),
        }
        selection_label = st.radio(
            i18n.t("navigation.label"),
            list(nav_labels.values()),
            index=0,
        )
        selection = next(
            key for key, value in nav_labels.items() if value == selection_label
        )

        if st.button(i18n.t("app.reset")):
            reset_session_state()
            st.success(i18n.t("app.reset_success"))
            st.rerun()

        st.divider()
        st.caption(
            f"{i18n.t('app.sidebar_version', version='0.1.0')}\n"
            f"{i18n.t('app.sidebar_competition')}\n"
            f"{i18n.t('app.sidebar_goal')}"
        )

    render = PAGES.get(selection)
    if render is None:
        st.error(i18n.t("errors.page_missing"))
        return

    try:
        render()
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("页面渲染失败：%s", exc)
        st.error(f"😥 {i18n.t('errors.render_failed')}")
        st.stop()


if __name__ == "__main__":
    main()
