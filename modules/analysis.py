"""Financial analysis helpers turning transactions into insights."""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from typing import Dict, Iterable, List, Sequence, Set

import numpy as np
import pandas as pd
from openai import OpenAI

from models.entities import SpendingInsight, Transaction
from utils.error_handling import safe_call

logger = logging.getLogger(__name__)


@safe_call(timeout=30, fallback=None, error_message="LLM建议生成失败")
def _generate_personalized_actions_llm(
    category: str,
    delta_amount: float,
    delta_pct: float,
    context: Dict[str, float],
    locale: str = "zh_CN",
) -> List[str] | None:
    """
    使用LLM生成个性化消费建议

    Args:
        category: 消费类别
        delta_amount: 增加的金额
        delta_pct: 增加的百分比
        context: 用户财务上下文（monthly_total, category_ratio等）
        locale: 语言区域

    Returns:
        建议列表，失败返回None（触发fallback）
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY未配置，跳过LLM建议生成")
        return None

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))

    # 根据语言选择提示词
    if locale == "en_US":
        prompt = f"""You are a professional financial advisor. The user's spending in "{category}" category increased by {delta_pct:.1f}% (extra ¥{delta_amount:.0f}) compared to last month.

User financial background:
- Monthly total spending: ¥{context.get("monthly_total", 0):.2f}
- This category ratio: {context.get("category_ratio", 0):.1f}%

Generate 2-3 actionable saving tips:
1. Specific and feasible (not generic "reduce XX")
2. Quantify potential savings (estimate based on ¥{delta_amount}, max 80%)
3. Consider user's quality of life

Return JSON format:
[
  {{"action": "specific tip", "potential_save": estimated_amount}},
  {{"action": "...", "potential_save": ...}}
]

Requirements:
- Tips must be actionable
- Savings must be realistic
- Focus on quality over quantity
"""
    else:
        prompt = f"""你是专业的理财顾问。用户在「{category}」类别的支出比上月增加了{delta_pct:.1f}%（多花¥{delta_amount:.0f}）。

用户财务背景：
- 月总支出: ¥{context.get("monthly_total", 0):.2f}
- 该类别占比: {context.get("category_ratio", 0):.1f}%

请生成2-3条可操作的节约建议：
1. 具体可行（不要"减少XX"这种废话）
2. 量化节约金额（基于¥{delta_amount}推算合理比例，不超过80%）
3. 考虑用户实际生活质量（不要过度节省）

返回JSON格式：
[
  {{"action": "具体建议文本", "potential_save": 预计节省金额}},
  {{"action": "...", "potential_save": ...}}
]

要求：
- 建议必须具体可执行
- 节省金额要符合实际
- 关注生活质量，不建议过度节省
"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,  # 允许一定创造性
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial advisor expert at giving practical advice based on real data."
                        if locale == "en_US"
                        else "你是理财建议专家，擅长根据真实数据给出可行建议。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            return None

        # 清理markdown代码块
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        if not isinstance(data, list) or len(data) == 0:
            logger.warning(f"LLM返回格式错误: {data}")
            return None

        # 构建建议文本
        actions = []
        for item in data:
            action_text = item.get("action", "")
            save_amount = float(item.get("potential_save", 0))
            if action_text and save_amount > 0:
                if locale == "en_US":
                    actions.append(
                        f"{action_text}, potential save ¥{save_amount:.0f}/month"
                    )
                else:
                    actions.append(f"{action_text}，预计月省¥{save_amount:.0f}")

        if actions:
            logger.info(f"LLM成功生成{len(actions)}条建议（{category}类别）")
            return actions

        return None

    except json.JSONDecodeError as e:
        logger.warning(f"LLM响应JSON解析失败: {e}")
        return None
    except Exception as e:
        logger.warning(f"LLM建议生成异常: {e}")
        return None


def _to_dataframe(transactions: Sequence[Transaction]) -> pd.DataFrame:
    """Convert transactions into a pandas DataFrame for numerical work."""
    if not transactions:
        return pd.DataFrame(columns=["date", "category", "amount"])

    data = [
        {
            "date": pd.to_datetime(txn.date),
            "category": txn.category,
            "amount": float(txn.amount),
            "merchant": txn.merchant,
            "id": txn.id,
        }
        for txn in transactions
    ]
    df = pd.DataFrame(data)
    df.sort_values("date", inplace=True)
    return df


def calculate_category_totals(transactions: Iterable[Transaction]) -> Dict[str, float]:
    """Aggregate spending totals per category."""
    totals: Dict[str, float] = defaultdict(float)
    for txn in transactions:
        totals[txn.category] += float(txn.amount)
    return dict(totals)


def calculate_merchant_totals(transactions: Iterable[Transaction]) -> Dict[str, float]:
    """Aggregate spending totals per merchant (counterparty concentration)."""
    totals: Dict[str, float] = defaultdict(float)
    for txn in transactions:
        totals[txn.merchant] += float(txn.amount)
    return dict(totals)


def calculate_spending_trend(
    transactions: Iterable[Transaction],
    frequency: str = "M",
) -> pd.DataFrame:
    """
    Calculate spending trend at a given frequency (D=日, W=周, M=月).

    Returns a DataFrame with columns ['period', 'amount'].
    """
    transactions = list(transactions)
    df = _to_dataframe(transactions)
    if df.empty:
        return pd.DataFrame(columns=["period", "amount"])

    df.set_index("date", inplace=True)
    resampled = df["amount"].resample(frequency).sum().reset_index()
    resampled.rename(columns={"date": "period", "amount": "amount"}, inplace=True)
    return resampled


@safe_call(timeout=30, fallback=None, error_message="预测解释生成失败")
def _generate_forecast_narrative_llm(
    decision_log: Dict[str, object],
    locale: str = "zh_CN",
) -> str | None:
    """
    Convert the rule-engine forecast decision log into a natural-language
    explanation, mirroring the hybrid rule-engine + LLM pattern used by
    _generate_personalized_actions_llm above: the rule engine computes the
    numbers, the LLM only explains them (it is not allowed to invent numbers).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY未配置，跳过预测解释生成")
        return None

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))

    risk_flag = str(decision_log.get("risk_flag", "flat"))
    slope_ratio_pct = float(decision_log.get("slope_ratio", 0.0) or 0.0) * 100
    r_squared = float(decision_log.get("r_squared", 0.0) or 0.0)
    volatility = float(decision_log.get("volatility", 0.0) or 0.0)
    periods_ahead = int(decision_log.get("periods_ahead", 3) or 3)
    first_forecast = float(decision_log.get("first_forecast", 0.0) or 0.0)
    last_actual = float(decision_log.get("last_actual", 0.0) or 0.0)
    history_points = int(decision_log.get("history_points", 0) or 0)

    if locale == "en_US":
        prompt = f"""You are a financial analyst explaining a spending forecast to a small-business owner or freelancer with no finance background.

Forecast facts (already computed by a rule engine -- do not invent new numbers, only explain these):
- Method: linear trend extrapolation over {history_points} historical periods
- Trend direction: {risk_flag} ({slope_ratio_pct:.1f}% change per period relative to average spending)
- Fit quality (R-squared): {r_squared:.2f} (closer to 1.0 = more reliable trend)
- Historical volatility (residual std dev): {volatility:.0f}
- Last actual period spending: {last_actual:.0f}
- Next period forecast: {first_forecast:.0f}
- Forecasting {periods_ahead} period(s) ahead

Write a 2-3 sentence explanation using a "Because... therefore..." causal structure, plain language, no jargon. If R-squared is below 0.3, explicitly say the trend is not very reliable. End with one concrete, actionable suggestion. Frame the forecast as a projection based on historical trend only, never as a guaranteed outcome."""
    else:
        prompt = f"""你是一名财务分析师，正在向没有专业财务背景的个体户/自由职业者解释一份支出预测。

预测事实（已由规则引擎计算好，不要编造新数字，只负责解释）：
- 方法：基于最近 {history_points} 期历史数据的线性趋势外推
- 趋势方向：{risk_flag}（相对历史均值每期变化 {slope_ratio_pct:.1f}%）
- 拟合优度（R²）：{r_squared:.2f}（越接近1趋势越可信）
- 历史波动（残差标准差）：{volatility:.0f}
- 最近一期实际支出：{last_actual:.0f}
- 下一期预测支出：{first_forecast:.0f}
- 本次预测未来 {periods_ahead} 期

用"因为…所以…"的因果句式写2-3句解释，语言通俗、不要术语堆砌。如果R²低于0.3，要明确指出这个趋势不太可靠。结尾给一条具体可执行的建议。把预测表述为基于历史趋势的推算，不要说成一定会发生的结果。"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst who explains forecasts transparently and never overstates certainty."
                        if locale == "en_US"
                        else "你是财务分析师，解释预测时保持透明，不夸大确定性。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            return None
        return content.strip()
    except Exception as e:  # noqa: BLE001 - mirrors existing LLM helper's catch-all
        logger.warning(f"预测解释生成异常: {e}")
        return None


def forecast_spending_trend(
    transactions: Iterable[Transaction],
    frequency: str = "M",
    periods_ahead: int = 3,
    locale: str = "zh_CN",
) -> Dict[str, object]:
    """
    Forecast future spending by linearly extrapolating the same aggregated
    trend used by calculate_spending_trend.

    WeFinance currently only ingests outflow transactions (bills/receipts),
    with no income data source, so this is a spending forecast rather than a
    full income-minus-expense cash-flow forecast -- callers/UI copy should
    say "支出预测/spending forecast", not claim net cash flow.

    Returns a dict with:
    - history: DataFrame ['period', 'amount'] actual aggregated spending
    - forecast: DataFrame ['period', 'amount'] projected future spending
    - decision_log: dict of the rule engine's reasoning (auditable, no LLM
      involved in computing these numbers)
    - narrative: Optional[str] LLM explanation of decision_log, or None if
      unavailable (caller should render a decision_log-based fallback line)
    - insufficient_data: bool
    """
    history = calculate_spending_trend(transactions, frequency=frequency)
    min_points = 3
    if len(history) < min_points:
        return {
            "history": history,
            "forecast": pd.DataFrame(columns=["period", "amount"]),
            "decision_log": {
                "insufficient_data": True,
                "history_points": len(history),
                "min_points_required": min_points,
            },
            "narrative": None,
            "insufficient_data": True,
        }

    x = np.arange(len(history))
    y = history["amount"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    predicted_hist = slope * x + intercept
    residuals = y - predicted_hist
    volatility = float(np.std(residuals, ddof=0))
    y_mean = float(np.mean(y))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    ss_res = float(np.sum(residuals**2))
    r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    future_x = np.arange(len(history), len(history) + periods_ahead)
    future_y = np.clip(slope * future_x + intercept, a_min=0.0, a_max=None)
    future_periods = pd.date_range(
        start=history["period"].iloc[-1], periods=periods_ahead + 1, freq=frequency
    )[1:]
    forecast_df = pd.DataFrame({"period": future_periods, "amount": future_y})

    slope_ratio = float(slope / y_mean) if y_mean else 0.0
    if slope_ratio > 0.05:
        risk_flag = "up"
    elif slope_ratio < -0.05:
        risk_flag = "down"
    else:
        risk_flag = "flat"

    decision_log: Dict[str, object] = {
        "insufficient_data": False,
        "method": "linear_trend_extrapolation",
        "history_points": len(history),
        "periods_ahead": periods_ahead,
        "slope_per_period": float(slope),
        "slope_ratio": slope_ratio,
        "r_squared": r_squared,
        "volatility": volatility,
        "risk_flag": risk_flag,
        "last_actual": float(y[-1]),
        "first_forecast": float(future_y[0]) if len(future_y) else 0.0,
    }

    narrative = _generate_forecast_narrative_llm(decision_log, locale=locale)

    return {
        "history": history,
        "forecast": forecast_df,
        "decision_log": decision_log,
        "narrative": narrative,
        "insufficient_data": False,
    }


def _compute_zscore_anomalies(
    transactions: Sequence[Transaction],
    threshold: float,
) -> List[dict]:
    """Internal helper computing z-score anomalies for a given threshold."""
    df = _to_dataframe(transactions)
    if df.empty:
        return []

    amounts = df["amount"]
    mean = amounts.mean()
    std = amounts.std(ddof=0)
    if std == 0:
        return []

    df["z_score"] = (amounts - mean) / std
    anomalies = df[np.abs(df["z_score"]) >= threshold]
    results: List[dict] = []
    for _, row in anomalies.iterrows():
        z_val = float(row["z_score"])
        results.append(
            {
                "transaction_id": row["id"],
                "date": row["date"].date(),
                "category": row["category"],
                "merchant": row["merchant"],
                "amount": float(row["amount"]),
                "z_score": z_val,
                "reason": f"高于平均值 {abs(z_val):.1f}σ",
                "status": "new",
            }
        )
    return results


def compute_anomaly_report(
    transactions: Iterable[Transaction],
    *,
    base_threshold: float = 2.5,
    whitelist_merchants: Iterable[str] | None = None,
) -> Dict[str, object]:
    """
    Generate anomaly detection results along with contextual metadata.

    Returns a dictionary containing:
    - items: List[dict] 异常记录
    - threshold_used: float 实际使用的阈值
    - adaptive: bool 是否动态调整过阈值
    - sample_size: int 用于检测的交易数
    - sensitivity: str 检测灵敏度（normal / reduced）
    - message: Optional[str] 提示文案
    """
    transactions = list(transactions)
    merchant_whitelist: Set[str] = {
        m.strip() for m in whitelist_merchants or [] if m.strip()
    }
    filtered = [txn for txn in transactions if txn.merchant not in merchant_whitelist]
    sample_size = len(filtered)

    report: Dict[str, object] = {
        "items": [],
        "threshold_used": base_threshold,
        "adaptive": False,
        "sample_size": sample_size,
        "sensitivity": "normal",
    }

    if sample_size < 3:
        report["message"] = "spending.message_insufficient_data"
        return report

    applied_threshold = base_threshold
    if sample_size < 10:
        applied_threshold = max(base_threshold, 3.0)
        report["sensitivity"] = "reduced"
        report["message"] = "spending.message_reduced_sensitivity"

    anomalies = _compute_zscore_anomalies(filtered, applied_threshold)

    if not anomalies and sample_size >= 10:
        for candidate in (2.0, 1.5):
            if candidate >= applied_threshold:
                continue
            candidate_anomalies = _compute_zscore_anomalies(filtered, candidate)
            if candidate_anomalies:
                anomalies = candidate_anomalies
                applied_threshold = candidate
                report["adaptive"] = True
                break

    if anomalies:
        for item in anomalies:
            item["threshold_used"] = applied_threshold
        report["items"] = anomalies
        report["threshold_used"] = applied_threshold
    else:
        report.setdefault("message", "spending.anomaly_no_detect")

    return report


def detect_anomalies(
    transactions: Iterable[Transaction],
    *,
    threshold: float = 2.5,
    whitelist_merchants: Iterable[str] | None = None,
) -> List[dict]:
    """Backward compatible wrapper returning仅异常列表."""
    report = compute_anomaly_report(
        transactions,
        base_threshold=threshold,
        whitelist_merchants=whitelist_merchants,
    )
    return list(report["items"])


def _month_over_month_insight(
    df: pd.DataFrame, locale: str = "zh_CN"
) -> SpendingInsight | None:
    """Compose insight comparing latest month to previous."""
    if df.empty:
        return None

    monthly = df.copy()
    monthly["year_month"] = monthly["date"].dt.to_period("M")
    month_totals = (
        monthly.groupby(["year_month", "category"])["amount"].sum().reset_index()
    )
    if month_totals["year_month"].nunique() < 2:
        return None

    month_totals.sort_values("year_month", inplace=True)
    latest_period = month_totals["year_month"].iloc[-1]
    previous_period = month_totals["year_month"].iloc[-2]

    latest = month_totals[month_totals["year_month"] == latest_period]
    prev = month_totals[month_totals["year_month"] == previous_period]

    merged = latest.merge(
        prev,
        on="category",
        how="left",
        suffixes=("_latest", "_prev"),
    )
    merged.fillna(0, inplace=True)
    if merged.empty:
        return None

    merged["delta_pct"] = np.where(
        merged["amount_prev"] == 0,
        np.inf,
        (merged["amount_latest"] - merged["amount_prev"]) / merged["amount_prev"] * 100,
    )
    top = merged.loc[merged["delta_pct"].idxmax()]
    if not np.isfinite(top["delta_pct"]):
        return None

    category = top["category"]
    delta_pct = top["delta_pct"]
    delta_amount = top["amount_latest"] - top["amount_prev"]

    # 计算月总支出和类别占比（用于LLM上下文）
    monthly_total = df["amount"].sum()
    category_ratio = (
        (top["amount_latest"] / monthly_total * 100) if monthly_total > 0 else 0
    )

    # 尝试使用LLM生成个性化建议
    llm_context = {
        "monthly_total": monthly_total,
        "category_ratio": category_ratio,
    }
    actions = _generate_personalized_actions_llm(
        category=category,
        delta_amount=delta_amount,
        delta_pct=delta_pct,
        context=llm_context,
        locale=locale,
    )

    # Fallback到硬编码规则（LLM失败时）
    if not actions:
        logger.info(f"LLM建议生成失败，使用fallback规则（{category}类别）")
        if category == "餐饮":
            monthly_save_1 = delta_amount * 0.6  # 60% can be saved by meal prep
            monthly_save_2 = delta_amount * 0.3  # 30% by using delivery discounts
            actions = [
                f"每周自备午餐2-3次，月省约¥{monthly_save_1:.0f}",
                f"减少外卖订单，使用堂食优惠，月省约¥{monthly_save_2:.0f}",
            ]
        elif category == "交通":
            monthly_save = delta_amount * 0.4  # 40% by using monthly pass
            actions = [
                f"办理月卡或交通套餐，月省约¥{monthly_save:.0f}",
                "优化出行路线，合并近距离行程",
            ]
        elif category == "购物":
            monthly_save = delta_amount * 0.5  # 50% by reducing impulse purchases
            actions = [
                f"设置购物清单，减少冲动消费，月省约¥{monthly_save:.0f}",
                "等待促销活动，避免高峰期购买",
            ]
        elif category == "娱乐":
            monthly_save = delta_amount * 0.45  # 45% by using memberships
            actions = [
                f"使用年度会员或套餐优惠，月省约¥{monthly_save:.0f}",
                "选择性价比更高的娱乐活动",
            ]
        else:
            # Generic recommendations for other categories
            actions = [
                "分析具体支出明细，识别可优化项目",
                "设置该类别月度预算，控制增长趋势",
            ]

    return SpendingInsight(
        title="分类支出变化",
        detail=f"您本月在「{category}」上的支出比上月增加了 {delta_pct:.1f}%（多花¥{delta_amount:.0f}）",
        actions=actions,
        delta=delta_pct,
    )


def _recent_average_insight(df: pd.DataFrame, days: int = 3) -> SpendingInsight | None:
    """Generate insight on recent rolling average spending."""
    if df.empty:
        return None

    latest_date = df["date"].max()
    window_start = latest_date - pd.Timedelta(days=days - 1)

    recent = df[df["date"] >= window_start]
    if recent.empty:
        return None

    avg = recent["amount"].mean()
    monthly_projected = avg * 30

    # Generate actionable recommendations based on daily average
    actions = []
    if avg > 200:  # High daily spending
        potential_save = avg * 0.25 * 30  # 25% reduction
        actions = [
            f"设置每日消费目标¥{avg * 0.75:.0f}，月省¥{potential_save:.0f}",
            "使用消费记录App，实时追踪每日支出",
        ]
    elif avg > 100:  # Moderate daily spending
        actions = [
            "继续保持当前消费水平，关注异常大额支出",
            "设置每周预算提醒，避免后期超支",
        ]
    else:  # Low daily spending
        actions = [
            "消费控制良好，可考虑将结余用于投资理财",
            "建立应急基金，提升财务安全性",
        ]

    return SpendingInsight(
        title="近期开销趋势",
        detail=f"最近 {days} 天的平均日消费约为 ¥{avg:.2f}（按此速度月消费约¥{monthly_projected:.0f}）",
        actions=actions,
    )


def generate_insights(
    transactions: Iterable[Transaction], locale: str = "zh_CN"
) -> List[SpendingInsight]:
    """Produce high-level talking points for the dashboard."""
    transactions = list(transactions)
    if not transactions:
        return []

    df = _to_dataframe(transactions)
    if df.empty:
        return []

    insights: List[SpendingInsight] = []

    totals = calculate_category_totals(transactions)
    if totals:
        top_category = max(totals, key=totals.get)
        top_amount = totals[top_category]
        total_spending = sum(totals.values())
        concentration_pct = (
            (top_amount / total_spending * 100) if total_spending > 0 else 0
        )

        # Generate actionable recommendations based on top category
        actions = []
        if concentration_pct > 50:  # High concentration
            potential_save = top_amount * 0.2  # 20% reduction potential
            actions = [
                f"该类别占比{concentration_pct:.0f}%，考虑优化可月省¥{potential_save:.0f}",
                "制定该类别专项预算，分散消费风险",
            ]
        elif concentration_pct > 30:  # Moderate concentration
            actions = [
                f"该类别占比{concentration_pct:.0f}%，属于合理范围",
                "可关注其他类别支出，保持平衡",
            ]
        else:  # Low concentration - diversified spending
            actions = [
                "消费分布均衡，财务结构健康",
                "继续保持多元化消费，避免单一类别过度集中",
            ]

        insights.append(
            SpendingInsight(
                title="消费集中度提示",
                detail=f"目前「{top_category}」类别的支出最高，约为 ¥{top_amount:.2f}（占总支出{concentration_pct:.0f}%）",
                actions=actions,
            )
        )

    mom_insight = _month_over_month_insight(df, locale=locale)
    if mom_insight:
        insights.append(mom_insight)

    recent_insight = _recent_average_insight(df)
    if recent_insight:
        insights.append(recent_insight)

    return insights
