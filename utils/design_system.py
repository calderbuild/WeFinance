"""
WeFinance Design System
=======================

统一的设计系统，定义颜色、字体、间距、动画和可复用的UI组件。
采用 "Modern Finance Luxury" 美学设计：
- 深青绿色作为主色调（信任、增长、财富）
- 金色点缀（高端质感）
- 玻璃态效果和流畅动画

使用方法:
    from utils.design_system import inject_global_styles, COLORS

    # 在app.py顶部注入全局样式
    inject_global_styles()
"""

from __future__ import annotations

import streamlit as st

# =============================================================================
# COLOR PALETTE (配色方案)
# =============================================================================

COLORS = {
    # Primary colors - Deep Teal/Emerald
    "primary": "#0d9488",           # 主色调：青绿色
    "primary_dark": "#0f766e",      # 深色变体
    "primary_light": "#14b8a6",     # 浅色变体
    "primary_muted": "rgba(13, 148, 136, 0.15)",  # 半透明背景

    # Accent - Warm Gold
    "accent": "#d4af37",            # 金色点缀
    "accent_light": "#f4d03f",      # 亮金色
    "accent_muted": "rgba(212, 175, 55, 0.2)",

    # Semantic colors
    "success": "#10b981",           # 成功/健康
    "warning": "#f59e0b",           # 警告
    "error": "#ef4444",             # 错误/超支
    "info": "#3b82f6",              # 信息

    # Neutrals
    "bg_dark": "#0f172a",           # 深色背景
    "bg_card": "#1e293b",           # 卡片背景
    "bg_glass": "rgba(30, 41, 59, 0.8)",  # 玻璃态背景
    "text_primary": "#f8fafc",      # 主文字
    "text_secondary": "#94a3b8",    # 次要文字
    "text_muted": "#64748b",        # 淡化文字
    "border": "rgba(148, 163, 184, 0.2)",  # 边框

    # Gradients
    "gradient_primary": "linear-gradient(135deg, #0d9488 0%, #0891b2 50%, #0d9488 100%)",
    "gradient_gold": "linear-gradient(135deg, #d4af37 0%, #f4d03f 50%, #d4af37 100%)",
    "gradient_dark": "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
    "gradient_card": "linear-gradient(145deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%)",
}

# =============================================================================
# TYPOGRAPHY (字体系统)
# =============================================================================

FONTS = {
    # 使用 Google Fonts 的 DM 字体家族
    # DM Serif Display - 优雅的衬线字体用于标题
    # DM Sans - 现代无衬线字体用于正文
    "heading": "'DM Serif Display', Georgia, serif",
    "body": "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
    "mono": "'JetBrains Mono', 'Fira Code', monospace",

    # Font sizes (rem)
    "size_xs": "0.75rem",
    "size_sm": "0.875rem",
    "size_base": "1rem",
    "size_lg": "1.125rem",
    "size_xl": "1.25rem",
    "size_2xl": "1.5rem",
    "size_3xl": "1.875rem",
    "size_4xl": "2.25rem",
    "size_5xl": "3rem",
}

# =============================================================================
# SPACING (间距系统)
# =============================================================================

SPACING = {
    "xs": "0.25rem",
    "sm": "0.5rem",
    "md": "1rem",
    "lg": "1.5rem",
    "xl": "2rem",
    "2xl": "3rem",
    "3xl": "4rem",
}

# =============================================================================
# SHADOWS (阴影系统)
# =============================================================================

SHADOWS = {
    "sm": "0 1px 2px rgba(0, 0, 0, 0.3)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)",
    "glow_primary": "0 0 20px rgba(13, 148, 136, 0.4), 0 0 40px rgba(13, 148, 136, 0.2)",
    "glow_gold": "0 0 20px rgba(212, 175, 55, 0.4), 0 0 40px rgba(212, 175, 55, 0.2)",
    "inner": "inset 0 2px 4px 0 rgba(0, 0, 0, 0.3)",
}

# =============================================================================
# BORDER RADIUS (圆角)
# =============================================================================

RADIUS = {
    "sm": "0.375rem",
    "md": "0.5rem",
    "lg": "0.75rem",
    "xl": "1rem",
    "2xl": "1.5rem",
    "full": "9999px",
}


def inject_global_styles() -> None:
    """
    注入全局CSS样式到Streamlit应用

    应该在app.py的最顶部调用一次
    """
    st.markdown(f"""
    <style>
    /* =================================================================
       GOOGLE FONTS IMPORT
       ================================================================= */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* =================================================================
       CSS VARIABLES (设计令牌)
       ================================================================= */
    :root {{
        /* Colors */
        --wf-primary: {COLORS['primary']};
        --wf-primary-dark: {COLORS['primary_dark']};
        --wf-primary-light: {COLORS['primary_light']};
        --wf-accent: {COLORS['accent']};
        --wf-accent-light: {COLORS['accent_light']};
        --wf-success: {COLORS['success']};
        --wf-warning: {COLORS['warning']};
        --wf-error: {COLORS['error']};
        --wf-bg-dark: {COLORS['bg_dark']};
        --wf-bg-card: {COLORS['bg_card']};
        --wf-text-primary: {COLORS['text_primary']};
        --wf-text-secondary: {COLORS['text_secondary']};
        --wf-border: {COLORS['border']};

        /* Typography */
        --wf-font-heading: {FONTS['heading']};
        --wf-font-body: {FONTS['body']};
        --wf-font-mono: {FONTS['mono']};

        /* Spacing */
        --wf-spacing-md: {SPACING['md']};
        --wf-spacing-lg: {SPACING['lg']};

        /* Shadows */
        --wf-shadow-md: {SHADOWS['md']};
        --wf-shadow-glow: {SHADOWS['glow_primary']};
    }}

    /* =================================================================
       GLOBAL STYLES
       ================================================================= */
    .stApp {{
        font-family: var(--wf-font-body);
    }}

    /* Headings with serif font */
    h1, h2, h3, .stTitle, [data-testid="stHeading"] {{
        font-family: var(--wf-font-heading) !important;
        letter-spacing: -0.02em;
    }}

    /* =================================================================
       ANIMATIONS (动画定义)
       ================================================================= */
    @keyframes wf-fade-in {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes wf-slide-up {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes wf-scale-in {{
        from {{ opacity: 0; transform: scale(0.95); }}
        to {{ opacity: 1; transform: scale(1); }}
    }}

    @keyframes wf-shimmer {{
        0% {{ background-position: -200% 0; }}
        100% {{ background-position: 200% 0; }}
    }}

    @keyframes wf-pulse-glow {{
        0%, 100% {{ box-shadow: 0 0 5px rgba(13, 148, 136, 0.3); }}
        50% {{ box-shadow: 0 0 20px rgba(13, 148, 136, 0.6), 0 0 40px rgba(13, 148, 136, 0.3); }}
    }}

    @keyframes wf-float {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-5px); }}
    }}

    @keyframes wf-count-up {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes wf-border-flow {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    @keyframes wf-glare {{
        0% {{ transform: translateX(-100%) rotate(-45deg); }}
        100% {{ transform: translateX(200%) rotate(-45deg); }}
    }}

    /* =================================================================
       UTILITY CLASSES
       ================================================================= */
    .wf-animate-fade-in {{
        animation: wf-fade-in 0.5s ease-out forwards;
    }}

    .wf-animate-slide-up {{
        animation: wf-slide-up 0.6s ease-out forwards;
    }}

    .wf-animate-scale {{
        animation: wf-scale-in 0.4s ease-out forwards;
    }}

    .wf-glass {{
        background: {COLORS['bg_glass']};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {COLORS['border']};
    }}

    .wf-glow {{
        box-shadow: {SHADOWS['glow_primary']};
    }}

    .wf-glow-gold {{
        box-shadow: {SHADOWS['glow_gold']};
    }}

    /* =================================================================
       CUSTOM COMPONENTS
       ================================================================= */

    /* Financial Health Card */
    .wf-health-card {{
        background: {COLORS['gradient_card']};
        border: 1px solid {COLORS['border']};
        border-radius: {RADIUS['xl']};
        padding: {SPACING['lg']};
        margin-bottom: {SPACING['lg']};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        position: relative;
        overflow: hidden;
        animation: wf-fade-in 0.6s ease-out;
    }}

    .wf-health-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 50%;
        height: 100%;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.05),
            transparent
        );
        animation: wf-glare 3s ease-in-out infinite;
    }}

    /* Metric Card */
    .wf-metric-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: {RADIUS['lg']};
        padding: {SPACING['md']};
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }}

    .wf-metric-card:hover {{
        transform: translateY(-2px);
        border-color: var(--wf-primary);
        box-shadow: {SHADOWS['glow_primary']};
    }}

    .wf-metric-card::after {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: {COLORS['gradient_primary']};
        opacity: 0;
        transition: opacity 0.3s ease;
    }}

    .wf-metric-card:hover::after {{
        opacity: 1;
    }}

    /* Status Badge */
    .wf-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.375rem 0.75rem;
        border-radius: {RADIUS['full']};
        font-size: {FONTS['size_sm']};
        font-weight: 600;
        letter-spacing: 0.025em;
    }}

    .wf-badge-healthy {{
        background: rgba(16, 185, 129, 0.15);
        color: {COLORS['success']};
        border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .wf-badge-warning {{
        background: rgba(245, 158, 11, 0.15);
        color: {COLORS['warning']};
        border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .wf-badge-danger {{
        background: rgba(239, 68, 68, 0.15);
        color: {COLORS['error']};
        border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    /* Hero Banner */
    .wf-hero {{
        background: {COLORS['gradient_card']};
        border: 1px solid {COLORS['border']};
        border-radius: {RADIUS['2xl']};
        padding: {SPACING['2xl']};
        position: relative;
        overflow: hidden;
        animation: wf-slide-up 0.7s ease-out;
    }}

    .wf-hero::before {{
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(13, 148, 136, 0.1) 0%, transparent 70%);
        animation: wf-float 6s ease-in-out infinite;
    }}

    .wf-hero-title {{
        font-family: var(--wf-font-heading);
        font-size: {FONTS['size_4xl']};
        color: {COLORS['text_primary']};
        margin: 0 0 0.5rem 0;
        position: relative;
        z-index: 1;
    }}

    .wf-hero-subtitle {{
        font-size: {FONTS['size_lg']};
        color: {COLORS['text_secondary']};
        margin: 0;
        position: relative;
        z-index: 1;
    }}

    .wf-hero-accent {{
        color: var(--wf-accent);
    }}

    /* Animated Number */
    .wf-number {{
        font-family: var(--wf-font-mono);
        font-size: {FONTS['size_2xl']};
        font-weight: 600;
        color: {COLORS['text_primary']};
        animation: wf-count-up 0.5s ease-out;
    }}

    .wf-number-label {{
        font-size: {FONTS['size_sm']};
        color: {COLORS['text_secondary']};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }}

    /* Progress Ring */
    .wf-progress-ring {{
        transform: rotate(-90deg);
    }}

    .wf-progress-ring-bg {{
        fill: none;
        stroke: {COLORS['border']};
    }}

    .wf-progress-ring-fill {{
        fill: none;
        stroke-linecap: round;
        transition: stroke-dashoffset 1s ease-out;
    }}

    /* Loading Shimmer */
    .wf-shimmer {{
        background: linear-gradient(
            90deg,
            {COLORS['bg_card']} 0%,
            {COLORS['bg_glass']} 50%,
            {COLORS['bg_card']} 100%
        );
        background-size: 200% 100%;
        animation: wf-shimmer 1.5s ease-in-out infinite;
        border-radius: {RADIUS['md']};
    }}

    /* Star Border Effect */
    .wf-star-border {{
        position: relative;
        overflow: hidden;
        border-radius: {RADIUS['xl']};
        padding: 2px;
        background: linear-gradient(
            90deg,
            {COLORS['primary']},
            {COLORS['accent']},
            {COLORS['primary']}
        );
        background-size: 200% 200%;
        animation: wf-border-flow 3s ease infinite;
    }}

    .wf-star-border-inner {{
        background: {COLORS['bg_card']};
        border-radius: calc({RADIUS['xl']} - 2px);
        padding: {SPACING['lg']};
    }}

    /* Chat Message Bubbles */
    .wf-chat-user {{
        background: {COLORS['primary_muted']};
        border: 1px solid rgba(13, 148, 136, 0.3);
        border-radius: {RADIUS['lg']} {RADIUS['lg']} {RADIUS['sm']} {RADIUS['lg']};
        padding: {SPACING['md']};
        margin-left: 2rem;
        animation: wf-slide-up 0.3s ease-out;
    }}

    .wf-chat-assistant {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: {RADIUS['lg']} {RADIUS['lg']} {RADIUS['lg']} {RADIUS['sm']};
        padding: {SPACING['md']};
        margin-right: 2rem;
        animation: wf-slide-up 0.3s ease-out;
    }}

    /* Streamlit Overrides */
    .stButton > button {{
        font-family: var(--wf-font-body);
        font-weight: 600;
        border-radius: {RADIUS['lg']};
        transition: all 0.2s ease;
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
    }}

    .stButton > button[data-baseweb="button"][kind="primary"] {{
        background: {COLORS['gradient_primary']};
        border: none;
    }}

    /* Metrics styling */
    [data-testid="stMetricValue"] {{
        font-family: var(--wf-font-mono);
    }}

    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: {COLORS['bg_dark']};
        border-right: 1px solid {COLORS['border']};
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
        color: {COLORS['text_secondary']};
    }}

    /* Expander styling */
    .streamlit-expanderHeader {{
        font-family: var(--wf-font-body);
        font-weight: 600;
        border-radius: {RADIUS['md']};
    }}

    /* DataFrames */
    [data-testid="stDataFrame"] {{
        border-radius: {RADIUS['lg']};
        overflow: hidden;
    }}

    /* Plotly charts background */
    .js-plotly-plot .plotly {{
        border-radius: {RADIUS['lg']};
    }}

    </style>
    """, unsafe_allow_html=True)


def render_hero_banner(title: str, subtitle: str, accent_word: str | None = None) -> None:
    """
    渲染英雄横幅组件

    Args:
        title: 主标题
        subtitle: 副标题
        accent_word: 需要高亮的关键词（可选）
    """
    if accent_word and accent_word in title:
        title = title.replace(
            accent_word,
            f'<span class="wf-hero-accent">{accent_word}</span>'
        )

    st.markdown(f"""
    <div class="wf-hero">
        <h1 class="wf-hero-title">{title}</h1>
        <p class="wf-hero-subtitle">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, icon: str = "", delta: str | None = None, delta_color: str = "normal") -> str:
    """
    生成指标卡片HTML

    Args:
        label: 指标标签
        value: 指标值
        icon: 图标（可选）
        delta: 变化值（可选）
        delta_color: 变化颜色 ("positive", "negative", "normal")

    Returns:
        HTML字符串
    """
    delta_html = ""
    if delta:
        delta_cls = {
            "positive": f"color: {COLORS['success']};",
            "negative": f"color: {COLORS['error']};",
            "normal": f"color: {COLORS['text_secondary']};",
        }.get(delta_color, "")
        delta_html = f'<div style="{delta_cls} font-size: 0.875rem; margin-top: 0.25rem;">{delta}</div>'

    return f"""
    <div class="wf-metric-card">
        <div class="wf-number-label">{icon} {label}</div>
        <div class="wf-number">{value}</div>
        {delta_html}
    </div>
    """


def render_status_badge(status: str, status_type: str = "healthy") -> str:
    """
    生成状态徽章HTML

    Args:
        status: 状态文字
        status_type: "healthy", "warning", "danger"

    Returns:
        HTML字符串
    """
    badge_class = f"wf-badge wf-badge-{status_type}"
    icon = {
        "healthy": "●",
        "warning": "◐",
        "danger": "○",
    }.get(status_type, "●")

    return f'<span class="{badge_class}">{icon} {status}</span>'


def render_progress_ring(percentage: float, size: int = 80, stroke_width: int = 8) -> str:
    """
    生成环形进度条SVG

    Args:
        percentage: 百分比 (0-100)
        size: 尺寸（像素）
        stroke_width: 线条宽度

    Returns:
        SVG HTML字符串
    """
    radius = (size - stroke_width) / 2
    circumference = 2 * 3.14159 * radius
    offset = circumference - (percentage / 100) * circumference

    # 根据百分比选择颜色
    if percentage < 60:
        color = COLORS['success']
    elif percentage < 85:
        color = COLORS['warning']
    else:
        color = COLORS['error']

    return f"""
    <svg width="{size}" height="{size}" class="wf-progress-ring">
        <circle
            class="wf-progress-ring-bg"
            stroke-width="{stroke_width}"
            r="{radius}"
            cx="{size/2}"
            cy="{size/2}"
        />
        <circle
            class="wf-progress-ring-fill"
            stroke="{color}"
            stroke-width="{stroke_width}"
            stroke-dasharray="{circumference}"
            stroke-dashoffset="{offset}"
            r="{radius}"
            cx="{size/2}"
            cy="{size/2}"
        />
        <text
            x="50%"
            y="50%"
            text-anchor="middle"
            dominant-baseline="middle"
            fill="{COLORS['text_primary']}"
            font-family="{FONTS['mono']}"
            font-size="{size * 0.2}px"
            font-weight="600"
        >{percentage:.0f}%</text>
    </svg>
    """


def render_shimmer_loader(height: str = "100px", width: str = "100%") -> None:
    """
    渲染加载骨架屏

    Args:
        height: 高度
        width: 宽度
    """
    st.markdown(f"""
    <div class="wf-shimmer" style="height: {height}; width: {width};"></div>
    """, unsafe_allow_html=True)


def render_star_border_card(content: str) -> None:
    """
    渲染星星边框卡片（动画流光边框效果）

    Args:
        content: 卡片内容HTML
    """
    st.markdown(f"""
    <div class="wf-star-border">
        <div class="wf-star-border-inner">
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_empty_state(
    title: str,
    description: str,
    icon: str = "📊",
    cta_text: str | None = None,
) -> None:
    """
    渲染空状态组件

    Args:
        title: 标题
        description: 描述
        icon: 图标
        cta_text: 按钮文字（可选）
    """
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: {SPACING['3xl']} {SPACING['xl']};
        animation: wf-fade-in 0.5s ease-out;
    ">
        <div style="
            font-size: 4rem;
            margin-bottom: {SPACING['md']};
            opacity: 0.6;
        ">{icon}</div>
        <h3 style="
            font-family: {FONTS['heading']};
            font-size: {FONTS['size_xl']};
            color: {COLORS['text_primary']};
            margin: 0 0 {SPACING['sm']} 0;
        ">{title}</h3>
        <p style="
            font-size: {FONTS['size_base']};
            color: {COLORS['text_secondary']};
            margin: 0;
            max-width: 400px;
            margin: 0 auto;
        ">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, subtitle: str | None = None, icon: str = "") -> None:
    """
    渲染区块标题

    Args:
        title: 标题
        subtitle: 副标题（可选）
        icon: 图标（可选）
    """
    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""
        <p style="
            font-size: {FONTS['size_sm']};
            color: {COLORS['text_secondary']};
            margin: {SPACING['xs']} 0 0 0;
        ">{subtitle}</p>
        """

    st.markdown(f"""
    <div style="margin-bottom: {SPACING['lg']}; animation: wf-fade-in 0.4s ease-out;">
        <h2 style="
            font-family: {FONTS['heading']};
            font-size: {FONTS['size_2xl']};
            color: {COLORS['text_primary']};
            margin: 0;
            display: flex;
            align-items: center;
            gap: {SPACING['sm']};
        ">
            {f'<span>{icon}</span>' if icon else ''}
            {title}
        </h2>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)
