"""Conversational manager that orchestrates GPT responses with finance context."""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, Iterable, List, Optional

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from models.entities import Transaction
from modules.analysis import calculate_category_totals

try:  # Optional LangChain integration
    from services.langchain_agent import LangChainFinanceAgent
except Exception:  # pragma: no cover - optional dependency
    LangChainFinanceAgent = None  # type: ignore[assignment]

load_dotenv()

logger = logging.getLogger(__name__)


class ChatManager:
    """Manage chat history, budgeting context, and LLM responses."""

    def __init__(
        self,
        *,
        history: Optional[List[Dict[str, str]]] = None,
        transactions: Optional[Iterable[Transaction | dict]] = None,
        monthly_budget: float | None = None,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.history: List[Dict[str, str]] = history if history is not None else []
        self.transactions: List[Transaction] = self._normalize_transactions(transactions)
        self.monthly_budget = monthly_budget if monthly_budget is not None else 0.0
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._client: Optional[OpenAI] = None
        self._lc_agent: Optional[LangChainFinanceAgent] = None

        self.system_prompt_template = """
你是WeFinance Copilot，一个专业的个人财务助理。
你的任务是帮助用户理解他们的消费情况，提供理财建议。

用户的账单数据：
{transactions_summary}

用户的预算设置：
月度预算：{monthly_budget}元
已消费：{spent}元
剩余：{remaining}元

回答要求：
1. 用通俗易懂的语言，避免专业术语
2. 结合用户的真实数据回答
3. 提供具体的数字和建议
4. 保持简洁，1-3句话
""".strip()

    @staticmethod
    def _normalize_transactions(
        transactions: Optional[Iterable[Transaction | dict]]
    ) -> List[Transaction]:
        if not transactions:
            return []
        normalized: List[Transaction] = []
        for txn in transactions:
            if isinstance(txn, Transaction):
                normalized.append(txn)
            elif isinstance(txn, dict):
                normalized.append(Transaction(**txn))
        return normalized

    def update_transactions(self, transactions: Iterable[Transaction | dict]) -> None:
        """Replace stored transactions, keeping conversions consistent."""
        self.transactions = self._normalize_transactions(transactions)
        self._lc_agent = None

    def set_monthly_budget(self, amount: float) -> None:
        """Persist current monthly budget."""
        self.monthly_budget = max(0.0, float(amount))
        self._lc_agent = None

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the conversation history."""
        self.history.append({"role": role, "content": content})

    def get_context(self, limit: int = 10) -> List[Dict[str, str]]:
        """Return the last N messages to maintain conversational context."""
        return self.history[-limit:]

    # ------------------------------------------------------------------ #
    # Data-driven helpers
    # ------------------------------------------------------------------ #
    def _transactions_dataframe(self) -> pd.DataFrame:
        if not self.transactions:
            return pd.DataFrame(columns=["date", "category", "amount"])

        records = [
            {
                "date": pd.to_datetime(txn.date),
                "category": txn.category,
                "amount": float(txn.amount),
            }
            for txn in self.transactions
        ]
        df = pd.DataFrame(records)
        df.sort_values("date", inplace=True)
        return df

    def _current_month_spent(self) -> float:
        df = self._transactions_dataframe()
        if df.empty:
            return 0.0

        today = pd.Timestamp.today()
        mask = (df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)
        return float(df.loc[mask, "amount"].sum())

    def _transactions_summary_text(self) -> str:
        if not self.transactions:
            return "暂无账单数据。"

        totals = calculate_category_totals(self.transactions)
        top_categories = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:3]
        summary_lines = [f"- {category}：¥{amount:.2f}" for category, amount in top_categories]
        return "\n".join(summary_lines) if summary_lines else "暂无账单数据。"

    # ------------------------------------------------------------------ #
    # Query helpers
    # ------------------------------------------------------------------ #
    def query_transactions(self, question: str) -> Optional[str]:
        """
        Attempt to answer finance questions without hitting the LLM.

        Handles budget remaining and top spending category scenarios.
        """
        normalized = question.strip()
        if not normalized:
            return None

        lowered = normalized.lower()
        has_budget_hint = any(keyword in normalized for keyword in ("还能花", "剩多少", "剩余", "预算"))
        has_spend_max_hint = ("花钱最多" in normalized) or (
            "最多" in normalized and any(token in normalized for token in ("花", "支出"))
        )

        if has_budget_hint:
            spent = self._current_month_spent()
            if self.monthly_budget <= 0:
                return (
                    "暂未设置月度预算，您可以先设定一个目标金额，我再帮您计算剩余额度。"
                )
            remaining = self.monthly_budget - spent
            remaining = max(0.0, remaining)
            return (
                f"本月预算剩余约 ¥{remaining:.2f}，已消费 ¥{spent:.2f}，"
                f"建议把剩余额度分配到关键支出类别，避免集中爆发。"
            )

        if has_spend_max_hint:
            totals = calculate_category_totals(self.transactions)
            if not totals:
                return "暂未检测到消费记录，上传账单后我会告诉您花费最多的类别。"
            top_category = max(totals, key=totals.get)
            return f"最近花费最多的类别是「{top_category}」，总额约 ¥{totals[top_category]:.2f}。"

        if "平均" in normalized and any(token in normalized for token in ("近", "最近")):
            df = self._transactions_dataframe()
            if df.empty:
                return "暂未检测到消费记录，上传账单后我会给出平均支出。"
            window_start = df["date"].max() - pd.Timedelta(days=2)
            recent = df[df["date"] >= window_start]
            if recent.empty:
                return "最近几天没有新的消费记录。"
            avg = recent["amount"].mean()
            return f"最近3天的日均消费约 ¥{avg:.2f}。"

        if "etf" in lowered:
            return (
                "ETF是一篮子资产的指数基金，买一份就等于分散到多支股票或债券，费用通常较低，适合长期定投。"
            )

        return None

    # ------------------------------------------------------------------ #
    # LLM interactions
    # ------------------------------------------------------------------ #
    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY 未配置，无法生成AI回复。")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def generate_response(self, user_prompt: str) -> str:
        """
        Generate assistant response. Uses heuristics first, then falls back to GPT.
        """
        heuristic_answer = self.query_transactions(user_prompt)
        if heuristic_answer:
            self.add_message("assistant", heuristic_answer)
            return heuristic_answer

        agent_answer = self._maybe_run_langchain_agent(user_prompt)
        if agent_answer:
            self.add_message("assistant", agent_answer)
            return agent_answer

        spent = self._current_month_spent()
        remaining = max(0.0, self.monthly_budget - spent) if self.monthly_budget else 0.0
        system_prompt = self.system_prompt_template.format(
            transactions_summary=self._transactions_summary_text(),
            monthly_budget=f"{self.monthly_budget:.2f}",
            spent=f"{spent:.2f}",
            remaining=f"{remaining:.2f}",
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.get_context())
        messages.append({"role": "user", "content": user_prompt})

        client = self._ensure_client()
        errors: List[str] = []
        for attempt in range(3):
            try:
                completion = client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    messages=messages,
                )
                content = completion.choices[0].message.content
                if not content:
                    raise RuntimeError("模型未返回内容。")
                self.add_message("assistant", content)
                return content
            except (OpenAIError, RuntimeError) as exc:
                errors.append(str(exc))
                time.sleep(0.5 * (attempt + 1))

        fallback = "抱歉，暂时无法连接到AI服务，请稍后再试。"
        if errors:
            fallback += f"（错误信息：{errors[-1]}）"
        self.add_message("assistant", fallback)
        return fallback

    # ------------------------------------------------------------------ #
    # LangChain agent helper
    # ------------------------------------------------------------------ #
    def _maybe_run_langchain_agent(self, query: str) -> Optional[str]:
        if LangChainFinanceAgent is None:
            return None

        try:
            agent = self._ensure_langchain_agent()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("初始化LangChain Agent失败：%s", exc)
            self._lc_agent = None
            return None

        if agent is None:
            return None

        try:
            return agent.run(query)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LangChain Agent运行失败：%s", exc)
            self._lc_agent = None
            return None

    def _ensure_langchain_agent(self) -> Optional[LangChainFinanceAgent]:
        if LangChainFinanceAgent is None:
            return None

        if self._lc_agent is None:
            self._lc_agent = LangChainFinanceAgent(
                self.transactions,
                monthly_budget=self.monthly_budget,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._lc_agent
