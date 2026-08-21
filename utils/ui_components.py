"""
可复用的UI组件，用于在各个页面之间保持一致的视觉体验

使用新的设计系统(design_system.py)进行样式定义
"""

from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any, Callable, Dict, List

import streamlit as st

from models.entities import Transaction
from utils.design_system import (
    COLORS,
    FONTS,
    RADIUS,
    SPACING,
    render_progress_ring,
    render_status_badge,
)
from utils.session import get_i18n, get_monthly_budget


def responsive_width_kwargs(
    component: Callable[..., Any], stretch: bool = True
) -> Dict[str, object]:
    """统一兼容Streamlit旧use_container_width与新width参数"""

    param = _resolve_width_param(component)
    if not param:
        return {}

    if param == "use_container_width":
        return {"use_container_width": stretch}
    return {"width": "stretch" if stretch else "content"}


@lru_cache(maxsize=32)
def _resolve_width_param(component: Callable[..., Any]) -> str | None:
    """缓存组件可用的宽度参数，避免多次反射

    优先使用 use_container_width：部分组件（如某些 Streamlit 版本的
    st.dataframe）会同时保留旧的整型 width 参数（像素宽度）与
    use_container_width，此时 width 并不是新的 "stretch"/"content"
    字符串枚举，误用会直接抛 TypeError。只有当 use_container_width
    已从签名中移除时，才说明该组件真正迁移到了新的 width 字符串 API。
    """

    try:
        signature = inspect.signature(component)
    except (TypeError, ValueError):
        return None

    if "use_container_width" in signature.parameters:
        return "use_container_width"
    if "width" in signature.parameters:
        return "width"
    return None


def render_financial_health_card(transactions: List[Transaction]) -> None:
    """
    渲染财务健康卡片（顶部状态栏）- 新设计

    采用玻璃态设计 + 环形进度条 + 流光边框效果

    显示：
    - 月度预算
    - 本月支出
    - 剩余预算
    - 预算使用率（环形进度条）

    Args:
        transactions: 交易记录列表
    """
    i18n = get_i18n()
    budget = get_monthly_budget()
    is_zh = i18n.locale == "zh_CN"

    # 计算支出总额
    total_spent = sum(tx.amount for tx in transactions)
    remaining = budget - total_spent
    usage_rate = (total_spent / budget * 100) if budget > 0 else 0

    # 健康状态判断
    if usage_rate < 60:
        status = "健康" if is_zh else "Healthy"
        status_type = "healthy"
    elif usage_rate < 85:
        status = "良好" if is_zh else "Good"
        status_type = "healthy"
    elif usage_rate < 100:
        status = "注意" if is_zh else "Caution"
        status_type = "warning"
    else:
        status = "超支" if is_zh else "Overspent"
        status_type = "danger"

    # 生成环形进度条
    progress_ring = render_progress_ring(min(usage_rate, 100), size=90, stroke_width=8)

    # 生成状态徽章
    status_badge = render_status_badge(status, status_type)

    # 多语言标签
    labels = {
        "title": "财务健康" if is_zh else "Financial Health",
        "budget": "月度预算" if is_zh else "Budget",
        "spent": "已支出" if is_zh else "Spent",
        "remaining": "剩余" if is_zh else "Remaining",
        "usage": "使用率" if is_zh else "Usage",
    }

    # 渲染卡片
    # 注意：st.markdown 底层走 CommonMark HTML block 规则，字符串内任何空行都会
    # 提前终止 HTML block、导致后续标签被当作纯文本转义显示——构造多行 HTML 时
    # 禁止在字符串内留空行（这里用 join 兜底剔除，防止未来改动时再引入空行）。
    html = f"""
    <div class="wf-health-card">
        <div style="display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 1;">
            <!-- 左侧：状态信息 -->
            <div style="flex: 0 0 auto;">
                <div style="
                    font-size: {FONTS["size_sm"]};
                    color: {COLORS["text_secondary"]};
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: {SPACING["xs"]};
                ">{labels["title"]}</div>
                <div style="margin-bottom: {SPACING["sm"]};">
                    {status_badge}
                </div>
            </div>

            <!-- 中间：指标数据 -->
            <div style="
                flex: 1;
                display: flex;
                gap: {SPACING["xl"]};
                justify-content: center;
                padding: 0 {SPACING["lg"]};
            ">
                <!-- 预算 -->
                <div style="text-align: center;">
                    <div style="
                        font-size: {FONTS["size_xs"]};
                        color: {COLORS["text_muted"]};
                        text-transform: uppercase;
                        letter-spacing: 0.05em;
                        margin-bottom: {SPACING["xs"]};
                    ">{labels["budget"]}</div>
                    <div style="
                        font-family: {FONTS["mono"]};
                        font-size: {FONTS["size_xl"]};
                        font-weight: 600;
                        color: {COLORS["text_primary"]};
                    ">{i18n.currency_symbol}{budget:,.0f}</div>
                </div>

                <!-- 已支出 -->
                <div style="text-align: center;">
                    <div style="
                        font-size: {FONTS["size_xs"]};
                        color: {COLORS["text_muted"]};
                        text-transform: uppercase;
                        letter-spacing: 0.05em;
                        margin-bottom: {SPACING["xs"]};
                    ">{labels["spent"]}</div>
                    <div style="
                        font-family: {FONTS["mono"]};
                        font-size: {FONTS["size_xl"]};
                        font-weight: 600;
                        color: {COLORS["accent"]};
                    ">{i18n.currency_symbol}{total_spent:,.0f}</div>
                </div>

                <!-- 剩余 -->
                <div style="text-align: center;">
                    <div style="
                        font-size: {FONTS["size_xs"]};
                        color: {COLORS["text_muted"]};
                        text-transform: uppercase;
                        letter-spacing: 0.05em;
                        margin-bottom: {SPACING["xs"]};
                    ">{labels["remaining"]}</div>
                    <div style="
                        font-family: {FONTS["mono"]};
                        font-size: {FONTS["size_xl"]};
                        font-weight: 600;
                        color: {COLORS["success"] if remaining >= 0 else COLORS["error"]};
                    ">{i18n.currency_symbol}{remaining:,.0f}</div>
                </div>
            </div>

            <!-- 右侧：环形进度条 -->
            <div style="flex: 0 0 auto; text-align: center;">
                <div style="
                    font-size: {FONTS["size_xs"]};
                    color: {COLORS["text_muted"]};
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: {SPACING["xs"]};
                ">{labels["usage"]}</div>
                {progress_ring}
            </div>
        </div>
    </div>
    """
    html = "\n".join(line for line in html.split("\n") if line.strip())
    st.markdown(html, unsafe_allow_html=True)


def render_transaction_card(
    transaction: Transaction,
    show_actions: bool = False,
    on_edit_key: str | None = None,
    on_delete_key: str | None = None,
) -> None:
    """
    渲染单笔交易卡片

    Args:
        transaction: 交易对象
        show_actions: 是否显示操作按钮
        on_edit_key: 编辑按钮的session_state key
        on_delete_key: 删除按钮的session_state key
    """
    i18n = get_i18n()

    # 类别图标映射
    category_icons = {
        "餐饮": "🍜",
        "交通": "🚗",
        "购物": "🛍️",
        "娱乐": "🎮",
        "医疗": "🏥",
        "教育": "📚",
        "其他": "📦",
        "Food": "🍜",
        "Transport": "🚗",
        "Shopping": "🛍️",
        "Entertainment": "🎮",
        "Medical": "🏥",
        "Education": "📚",
        "Other": "📦",
    }

    icon = category_icons.get(transaction.category, "📦")
    category_label = i18n.translate_category(transaction.category)

    st.markdown(
        f"""
    <div class="wf-metric-card" style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: {SPACING["sm"]};
    ">
        <div style="display: flex; align-items: center; gap: {SPACING["md"]};">
            <div style="
                width: 48px;
                height: 48px;
                border-radius: {RADIUS["lg"]};
                background: {COLORS["primary_muted"]};
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
            ">{icon}</div>
            <div>
                <div style="
                    font-weight: 600;
                    color: {COLORS["text_primary"]};
                    font-size: {FONTS["size_base"]};
                ">{transaction.merchant}</div>
                <div style="
                    font-size: {FONTS["size_sm"]};
                    color: {COLORS["text_secondary"]};
                ">{transaction.date} · {category_label}</div>
            </div>
        </div>
        <div style="
            font-family: {FONTS["mono"]};
            font-size: {FONTS["size_lg"]};
            font-weight: 600;
            color: {COLORS["error"]};
        ">-{i18n.currency_symbol}{transaction.amount:,.2f}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_stat_grid(stats: List[Dict[str, Any]]) -> None:
    """
    渲染统计数据网格

    Args:
        stats: 统计数据列表，每项包含 label, value, icon, delta(可选), delta_color(可选)
    """
    cols = st.columns(len(stats))

    for col, stat in zip(cols, stats):
        with col:
            delta_html = ""
            if "delta" in stat:
                delta_color = stat.get("delta_color", "normal")
                color_map = {
                    "positive": COLORS["success"],
                    "negative": COLORS["error"],
                    "normal": COLORS["text_secondary"],
                }
                delta_html = f"""
                <div style="
                    font-size: {FONTS["size_sm"]};
                    color: {color_map.get(delta_color, COLORS["text_secondary"])};
                    margin-top: {SPACING["xs"]};
                ">{stat["delta"]}</div>
                """

            st.markdown(
                f"""
            <div class="wf-metric-card">
                <div style="
                    font-size: {FONTS["size_xs"]};
                    color: {COLORS["text_muted"]};
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: {SPACING["xs"]};
                ">{stat.get("icon", "")} {stat["label"]}</div>
                <div style="
                    font-family: {FONTS["mono"]};
                    font-size: {FONTS["size_2xl"]};
                    font-weight: 600;
                    color: {COLORS["text_primary"]};
                ">{stat["value"]}</div>
                {delta_html}
            </div>
            """,
                unsafe_allow_html=True,
            )


def render_anomaly_alert(
    merchant: str,
    amount: float,
    reason: str,
    severity: str = "warning",
) -> None:
    """
    渲染异常交易警报卡片

    Args:
        merchant: 商户名称
        amount: 金额
        reason: 异常原因
        severity: 严重程度 ("warning", "danger")
    """
    i18n = get_i18n()

    color = COLORS["warning"] if severity == "warning" else COLORS["error"]
    bg_color = (
        "rgba(245, 158, 11, 0.1)"
        if severity == "warning"
        else "rgba(239, 68, 68, 0.1)"
    )
    icon = "⚠️" if severity == "warning" else "🚨"

    st.markdown(
        f"""
    <div style="
        background: {bg_color};
        border: 1px solid {color}40;
        border-left: 4px solid {color};
        border-radius: {RADIUS["md"]};
        padding: {SPACING["md"]};
        margin-bottom: {SPACING["md"]};
        animation: wf-fade-in 0.4s ease-out;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="
                    font-size: {FONTS["size_base"]};
                    font-weight: 600;
                    color: {color};
                    margin-bottom: {SPACING["xs"]};
                ">{icon} {merchant}</div>
                <div style="
                    font-size: {FONTS["size_sm"]};
                    color: {COLORS["text_secondary"]};
                ">{reason}</div>
            </div>
            <div style="
                font-family: {FONTS["mono"]};
                font-size: {FONTS["size_lg"]};
                font-weight: 600;
                color: {color};
            ">{i18n.currency_symbol}{amount:,.2f}</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_chat_message(
    content: str, is_user: bool = False, avatar: str | None = None
) -> None:
    """
    渲染聊天消息气泡

    Args:
        content: 消息内容
        is_user: 是否是用户消息
        avatar: 头像（可选）
    """
    if is_user:
        css_class = "wf-chat-user"
        default_avatar = "👤"
        align = "flex-end"
    else:
        css_class = "wf-chat-assistant"
        default_avatar = "🤖"
        align = "flex-start"

    avatar_display = avatar or default_avatar

    st.markdown(
        f"""
    <div style="display: flex; justify-content: {align}; margin-bottom: {SPACING["md"]};">
        <div class="{css_class}" style="max-width: 80%;">
            <div style="display: flex; align-items: flex-start; gap: {SPACING["sm"]};">
                <span style="font-size: 1.25rem;">{avatar_display}</span>
                <div style="
                    font-size: {FONTS["size_base"]};
                    color: {COLORS["text_primary"]};
                    line-height: 1.6;
                ">{content}</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_loading_state(message: str = "加载中...") -> None:
    """
    渲染加载状态

    Args:
        message: 加载提示文字
    """
    st.markdown(
        f"""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: {SPACING["2xl"]};
        animation: wf-fade-in 0.3s ease-out;
    ">
        <div style="
            width: 40px;
            height: 40px;
            border: 3px solid {COLORS["border"]};
            border-top-color: {COLORS["primary"]};
            border-radius: 50%;
            animation: spin 1s linear infinite;
        "></div>
        <div style="
            margin-top: {SPACING["md"]};
            font-size: {FONTS["size_sm"]};
            color: {COLORS["text_secondary"]};
        ">{message}</div>
    </div>
    <style>
    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_insight_card(
    title: str,
    value: str,
    description: str,
    icon: str = "💡",
    color: str = "primary",
) -> None:
    """
    渲染洞察卡片

    Args:
        title: 标题
        value: 核心数值
        description: 描述文字
        icon: 图标
        color: 颜色主题 ("primary", "success", "warning", "error")
    """
    color_map = {
        "primary": COLORS["primary"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["error"],
    }
    accent_color = color_map.get(color, COLORS["primary"])

    st.markdown(
        f"""
    <div class="wf-metric-card" style="position: relative; overflow: hidden;">
        <div style="
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: {accent_color};
        "></div>
        <div style="display: flex; align-items: flex-start; gap: {SPACING["md"]}; padding-top: {SPACING["sm"]};">
            <div style="
                font-size: 2rem;
                opacity: 0.8;
            ">{icon}</div>
            <div style="flex: 1;">
                <div style="
                    font-size: {FONTS["size_sm"]};
                    color: {COLORS["text_secondary"]};
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: {SPACING["xs"]};
                ">{title}</div>
                <div style="
                    font-family: {FONTS["mono"]};
                    font-size: {FONTS["size_2xl"]};
                    font-weight: 600;
                    color: {accent_color};
                    margin-bottom: {SPACING["xs"]};
                ">{value}</div>
                <div style="
                    font-size: {FONTS["size_sm"]};
                    color: {COLORS["text_secondary"]};
                    line-height: 1.5;
                ">{description}</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
