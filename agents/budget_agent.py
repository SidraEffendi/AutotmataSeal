import json
from datetime import datetime
from typing import Any, Dict

from . import storage, tool_loop

SYSTEM_PROMPT = """You are a personal budget tracking specialist. You help users:
- Track income and expenses across categories
- Set and monitor monthly budget limits
- Analyze spending patterns and identify overspending
- Provide actionable advice to improve financial habits

Always be encouraging, specific, and data-driven. When you spot overspending, suggest practical cuts.
Use the tools to read and write financial data, then synthesize clear summaries for the user.
When presenting numbers, always include context (e.g., % of income, vs budget limit)."""

TOOLS = [
    {"type": "function", "function": {
        "name": "add_transaction",
        "description": "Record an income or expense transaction",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Amount in dollars (positive)"},
                "type": {"type": "string", "enum": ["income", "expense"]},
                "category": {
                    "type": "string",
                    "description": "e.g. groceries, rent, salary, dining, transport, utilities, entertainment, healthcare, savings",
                },
                "description": {"type": "string", "description": "Brief description of the transaction"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format (defaults to today if omitted)"},
            },
            "required": ["amount", "type", "category", "description"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_budget_summary",
        "description": "Get income vs expense summary for a time period",
        "parameters": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["current_month", "last_month", "all_time"]},
            },
            "required": ["period"],
        },
    }},
    {"type": "function", "function": {
        "name": "set_budget_limit",
        "description": "Set a monthly spending limit for a category",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "limit": {"type": "number", "description": "Monthly limit in dollars"},
            },
            "required": ["category", "limit"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_spending_by_category",
        "description": "Get spending breakdown by category, with comparison to budget limits",
        "parameters": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Month in YYYY-MM format (defaults to current month)"},
            },
        },
    }},
    {"type": "function", "function": {
        "name": "list_transactions",
        "description": "List recent transactions, optionally filtered by category",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of transactions to return (default 20)"},
                "category": {"type": "string", "description": "Filter by category (optional)"},
            },
        },
    }},
]


def _handle_tool(name: str, inp: Dict[str, Any]) -> str:
    inp = inp or {}
    data = storage.load()
    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")

    if name == "add_transaction":
        tx = {
            "id": len(data["transactions"]) + 1,
            "amount": inp["amount"],
            "type": inp["type"],
            "category": inp["category"].lower(),
            "description": inp["description"],
            "date": inp.get("date", today),
        }
        data["transactions"].append(tx)
        storage.save(data)
        return json.dumps({"status": "added", "transaction": tx})

    if name == "get_budget_summary":
        period = inp["period"]
        txs = data["transactions"]
        now = datetime.now()

        def in_period(t: Dict) -> bool:
            d = t["date"][:7]
            if period == "current_month":
                return d == current_month
            if period == "last_month":
                m = now.month - 1 or 12
                y = now.year if now.month > 1 else now.year - 1
                return d == f"{y}-{m:02d}"
            return True

        filtered = [t for t in txs if in_period(t)]
        income = sum(t["amount"] for t in filtered if t["type"] == "income")
        expenses = sum(t["amount"] for t in filtered if t["type"] == "expense")
        return json.dumps({
            "period": period,
            "total_income": round(income, 2),
            "total_expenses": round(expenses, 2),
            "net_savings": round(income - expenses, 2),
            "savings_rate": f"{(income - expenses) / income * 100:.1f}%" if income else "N/A",
            "transaction_count": len(filtered),
        })

    if name == "set_budget_limit":
        cat = inp["category"].lower()
        data["budget_limits"][cat] = inp["limit"]
        storage.save(data)
        return json.dumps({"status": "set", "category": cat, "monthly_limit": inp["limit"]})

    if name == "get_spending_by_category":
        month = inp.get("month", current_month)
        txs = [t for t in data["transactions"] if t["date"][:7] == month and t["type"] == "expense"]
        by_cat: Dict[str, float] = {}
        for t in txs:
            by_cat[t["category"]] = round(by_cat.get(t["category"], 0) + t["amount"], 2)
        limits = data["budget_limits"]
        result = {}
        for cat, spent in sorted(by_cat.items(), key=lambda x: -x[1]):
            limit = limits.get(cat)
            result[cat] = {
                "spent": spent,
                "limit": limit,
                "remaining": round(limit - spent, 2) if limit else None,
                "over_budget": spent > limit if limit else False,
            }
        return json.dumps({"month": month, "categories": result})

    if name == "list_transactions":
        limit = inp.get("limit", 20)
        cat_filter = inp.get("category", "").lower()
        txs = data["transactions"]
        if cat_filter:
            txs = [t for t in txs if t["category"] == cat_filter]
        return json.dumps({"transactions": txs[-limit:][::-1]})

    return json.dumps({"error": f"Unknown tool: {name}"})


def run(task: str) -> str:
    return tool_loop.run(SYSTEM_PROMPT, task, TOOLS, _handle_tool)
