"""Streamlit page for uploading and parsing financial documents."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from models.entities import OCRParseResult, Transaction
from modules.analysis import generate_insights
from services.ocr_service import OCRService
from utils.session import get_i18n, set_transactions


def render() -> None:
    """Render the bill upload workflow."""
    i18n = get_i18n()
    st.title(i18n.t("bill_upload.title"))
    st.write(i18n.t("bill_upload.subtitle"))

    uploaded_files = st.file_uploader(
        i18n.t("bill_upload.uploader_help"),
        type=["png", "jpg", "jpeg", "pdf"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info(i18n.t("bill_upload.empty"))
        return

    ocr_service = OCRService()
    try:
        with st.spinner(i18n.t("bill_upload.spinner")):
            results = ocr_service.process_files(uploaded_files)
    except Exception as exc:  # pylint: disable=broad-except
        st.error(i18n.t("bill_upload.error", error=exc))
        return

    if not results:
        st.warning(i18n.t("bill_upload.warning_no_txn"))
        return

    transactions: list[Transaction] = []
    raw_texts: list[str] = []
    serialized_results: list[dict] = []

    for result in results:
        if isinstance(result, OCRParseResult):
            serialized_results.append(result.model_dump())
            raw_texts.append(result.text)
            transactions.extend(result.transactions)
        elif isinstance(result, dict):
            serialized_results.append(result)
            raw_texts.append(result.get("text", ""))
            items = result.get("transactions", [])
            for item in items:
                if isinstance(item, Transaction):
                    transactions.append(item)
                elif isinstance(item, dict):
                    transactions.append(Transaction(**item))

    set_transactions(transactions)
    st.session_state["ocr_raw_text"] = "\n\n".join(raw_texts)
    st.session_state["ocr_results"] = serialized_results
    st.session_state["uploaded_files_count"] = len(serialized_results)
    insights = generate_insights(transactions)
    st.session_state["analysis_summary"] = [ins.model_dump() for ins in insights]

    if transactions:
        st.success(i18n.t("bill_upload.success", count=len(transactions)))
    else:
        st.warning(i18n.t("bill_upload.warning_no_txn"))

    st.subheader(i18n.t("bill_upload.summary_header"))
    table_rows = [txn.model_dump() for txn in transactions]
    if table_rows:
        df = pd.DataFrame(table_rows)
        st.dataframe(df, use_container_width=True)

    if insights:
        st.subheader(i18n.t("bill_upload.insight_header"))
        for insight in insights:
            st.success(f"{insight.title}：{insight.detail}")

    st.subheader(i18n.t("bill_upload.ocr_header"))
    for result in serialized_results:
        filename = result.get("filename", i18n.t("bill_upload.default_filename"))
        text = result.get("text", "")
        with st.expander(filename):
            st.text(text or i18n.t("bill_upload.no_text"))
