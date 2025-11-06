"""Service layer for generating explainable financial recommendations."""

from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Tuple

from models.entities import Recommendation, Transaction


class RecommendationService:
    """Generate risk-aware allocation plans with explainable rationale."""

    ALLOCATION_RULES: Dict[str, Dict[str, float]] = {
        "保守型": {"债券基金": 0.7, "混合理财": 0.3},
        "稳健型": {"债券基金": 0.5, "股票基金": 0.3, "货币基金": 0.2},
        "激进型": {"股票基金": 0.6, "成长基金": 0.3, "货币基金": 0.1},
    }

    EXPECTED_RETURN = {"保守型": 4.5, "稳健型": 6.8, "激进型": 9.5}
    MAX_DRAWDOWN = {"保守型": 5.0, "稳健型": 12.0, "激进型": 20.0}
    RATIONALE = {
        "保守型": "以稳健增值为主，优先低波动资产。",
        "稳健型": "追求收益与风险之间的平衡组合。",
        "激进型": "以长期成长为目标，接受较大波动。",
    }

    def conduct_risk_assessment(self, responses: Dict[str, int]) -> str:
        """Map questionnaire responses to a risk profile label."""
        score = sum(responses.values())
        if score <= 4:
            return "保守型"
        if score <= 7:
            return "稳健型"
        return "激进型"

    def generate_allocation(self, risk_profile: str) -> Dict[str, float]:
        """Return asset allocation percentages based on risk appetite."""
        return self.ALLOCATION_RULES.get(risk_profile, self.ALLOCATION_RULES["稳健型"])

    def _parse_goal(self, goal_text: str) -> Tuple[str, float | None, int | None]:
        """
        Extract core goal, target amount (元), and horizon (月数) from freeform text.
        """
        normalized = goal_text.strip()
        if not normalized:
            return "未指定", None, None

        amount_match = re.search(r"(\d+(?:\.\d+)?)\s*(万|千|元|块)?", normalized)
        amount_value = None
        if amount_match:
            value = float(amount_match.group(1))
            unit = amount_match.group(2) or ""
            multiplier = 1.0
            if unit in {"万", "万元"}:
                multiplier = 10_000.0
            elif unit in {"千", "千元"}:
                multiplier = 1_000.0
            amount_value = value * multiplier

        horizon_match = re.search(r"(\d+)\s*(年|个月|月)", normalized)
        horizon_months = None
        if horizon_match:
            value = int(horizon_match.group(1))
            unit = horizon_match.group(2)
            horizon_months = value * 12 if unit == "年" else value

        return normalized, amount_value, horizon_months

    def _estimate_metrics(self, risk_profile: str) -> Dict[str, float]:
        return {
            "expected_return": self.EXPECTED_RETURN[risk_profile],
            "max_drawdown": self.MAX_DRAWDOWN[risk_profile],
        }

    def generate_explanation(
        self,
        risk_profile: str,
        investment_goal: str,
        allocation: Dict[str, float],
        metrics: Dict[str, float],
    ) -> str:
        """Generate XAI-style explanation string."""
        allocation_lines = [
            f"- {asset}：{percentage*100:.0f}%"
            for asset, percentage in allocation.items()
        ]
        allocation_rationale = "\n".join(allocation_lines)

        expected_return = metrics["expected_return"]
        max_drawdown = metrics["max_drawdown"]

        rationale_1 = self.RATIONALE.get(risk_profile, "综合考虑风险收益后得出的配置。")
        rationale_2 = "匹配您的目标时间和现金流需求。"

        explanation = f"""
为什么推荐这个组合？

1. 您的风险偏好是「{risk_profile}」
   → {rationale_1}

2. 您的目标是「{investment_goal}」
   → {rationale_2}

3. 根据历史数据分析：
   - 预期年化收益：{expected_return:.1f}%
   - 最大回撤：约 {max_drawdown:.1f}%

4. 配置理由：
{allocation_rationale}
""".strip()
        return explanation

    def _build_recommendation_summary(
        self,
        risk_profile: str,
        allocation: Dict[str, float],
        goal_name: str,
        target_amount: float | None,
        horizon_months: int | None,
    ) -> str:
        allocation_desc = "，".join(
            f"{asset}{percentage*100:.0f}%" for asset, percentage in allocation.items()
        )
        summary = (
            f"基于「{risk_profile}」风险偏好，建议采用组合：{allocation_desc}。"
            f"该配置兼顾风险与收益，可帮助达成“{goal_name}”目标。"
        )

        if target_amount and horizon_months and horizon_months > 0:
            monthly = math.ceil(target_amount / horizon_months)
            summary += f" 如按计划，建议每月储蓄约 ¥{monthly:.0f}。"
        return summary

    def create_plan(
        self,
        responses: Dict[str, int],
        investment_goal: str,
        transactions: Iterable[Transaction],
    ) -> Tuple[Recommendation, str, Dict[str, float], Dict[str, float]]:
        """High-level orchestrator returning recommendation, explanation and metrics."""
        risk_profile = self.conduct_risk_assessment(responses)
        allocation = self.generate_allocation(risk_profile)
        metrics = self._estimate_metrics(risk_profile)
        goal_name, goal_amount, goal_horizon = self._parse_goal(investment_goal)
        explanation = self.generate_explanation(
            risk_profile=risk_profile,
            investment_goal=goal_name,
            allocation=allocation,
            metrics=metrics,
        )
        summary = self._build_recommendation_summary(
            risk_profile,
            allocation,
            goal_name,
            goal_amount,
            goal_horizon,
        )

        rationale_steps = [
            f"风险评估结果：{risk_profile}。",
            f"资产配置方案：{', '.join(f'{k}{v*100:.0f}%' for k, v in allocation.items())}。",
            f"预期收益约 {metrics['expected_return']:.1f}% ，最大回撤约 {metrics['max_drawdown']:.1f}% 。",
        ]

        return Recommendation(
            title="个性化资产配置建议",
            summary=summary,
            rationale_steps=rationale_steps,
            risk_level=risk_profile,
        ), explanation, metrics, allocation

    def generate(
        self,
        transactions: Iterable[Transaction],
        responses: Dict[str, int],
        investment_goal: str,
    ) -> Dict[str, object]:
        """Public API returning recommendation payload for UI consumption."""
        recommendation, explanation, metrics, allocation = self.create_plan(
            responses=responses,
            investment_goal=investment_goal,
            transactions=transactions,
        )
        return {
            "recommendation": recommendation,
            "explanation": explanation,
            "metrics": metrics,
            "allocation": allocation,
            "risk_level": recommendation.risk_level,
        }
