import json
from typing import Any, Dict

from . import storage, tool_loop

SYSTEM_PROMPT = """You are a knowledgeable personal investment advisor. You help users:
- Understand their risk tolerance and build an appropriate investment profile
- Learn about investment vehicles: index funds, ETFs, stocks, bonds, Roth IRA, 401(k), HSA
- Get personalized portfolio allocation recommendations
- Project long-term wealth growth with compound interest
- Understand concepts like diversification, dollar-cost averaging, and rebalancing

IMPORTANT DISCLAIMERS you must include when making recommendations:
- You provide educational guidance, not licensed financial advice
- Past performance doesn't guarantee future results
- Always recommend consulting a licensed financial advisor for major decisions

Be specific: give real ETF tickers (VTI, VXUS, BND, etc.), explain the why behind every recommendation,
and show concrete numbers. Tailor advice to the user's actual risk profile from the tools."""

PORTFOLIO_TEMPLATES = {
    "conservative": {
        "description": "Capital preservation focus, lower volatility",
        "allocation": {
            "US Bonds (BND)": 50,
            "US Total Market (VTI)": 25,
            "International Stocks (VXUS)": 10,
            "TIPS / Inflation Protection (VTIP)": 10,
            "Cash / Money Market": 5,
        },
        "expected_annual_return": 0.05,
        "expected_volatility": "Low",
    },
    "moderate": {
        "description": "Balanced growth and stability",
        "allocation": {
            "US Total Market (VTI)": 45,
            "International Stocks (VXUS)": 20,
            "US Bonds (BND)": 25,
            "REITs (VNQ)": 5,
            "Short-Term Bonds (VGSH)": 5,
        },
        "expected_annual_return": 0.07,
        "expected_volatility": "Medium",
    },
    "aggressive": {
        "description": "Maximum long-term growth, higher short-term swings",
        "allocation": {
            "US Total Market (VTI)": 55,
            "International Stocks (VXUS)": 25,
            "Emerging Markets (VWO)": 10,
            "Small-Cap Value (VBR)": 5,
            "REITs (VNQ)": 5,
        },
        "expected_annual_return": 0.09,
        "expected_volatility": "High",
    },
}

TOOLS = [
    {"type": "function", "function": {
        "name": "set_risk_profile",
        "description": "Save the user's investment risk profile for personalized recommendations",
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
                "annual_income": {"type": "number"},
                "risk_tolerance": {"type": "string", "enum": ["conservative", "moderate", "aggressive"]},
                "investment_horizon_years": {"type": "integer", "description": "How many years until you need the money"},
                "monthly_investment_capacity": {"type": "number", "description": "How much you can invest per month"},
                "has_emergency_fund": {"type": "boolean"},
                "existing_investments": {"type": "number", "description": "Current portfolio value"},
            },
            "required": ["age", "risk_tolerance", "investment_horizon_years"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_risk_profile",
        "description": "Retrieve the user's saved risk profile",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_investment_recommendations",
        "description": "Get a personalized portfolio allocation based on the user's risk profile",
        "parameters": {
            "type": "object",
            "properties": {
                "lump_sum_amount": {"type": "number", "description": "One-time amount to invest (optional)"},
                "risk_override": {
                    "type": "string",
                    "enum": ["conservative", "moderate", "aggressive"],
                    "description": "Override risk profile for this recommendation only",
                },
            },
        },
    }},
    {"type": "function", "function": {
        "name": "calculate_compound_growth",
        "description": "Project how an investment grows over time with compound returns",
        "parameters": {
            "type": "object",
            "properties": {
                "principal": {"type": "number", "description": "Initial lump sum investment"},
                "annual_rate": {"type": "number", "description": "Expected annual return as decimal (e.g. 0.07 for 7%)"},
                "years": {"type": "integer"},
                "monthly_contribution": {"type": "number", "description": "Additional amount invested each month (default 0)"},
            },
            "required": ["principal", "annual_rate", "years"],
        },
    }},
    {"type": "function", "function": {
        "name": "compare_investment_scenarios",
        "description": "Compare multiple investment scenarios side by side",
        "parameters": {
            "type": "object",
            "properties": {
                "monthly_amount": {"type": "number"},
                "years": {"type": "integer"},
                "initial_investment": {"type": "number", "description": "Starting amount (default 0)"},
            },
            "required": ["monthly_amount", "years"],
        },
    }},
]


def _compound_fv(principal: float, annual_rate: float, years: int, monthly: float = 0) -> float:
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return principal + monthly * n
    fv_lump = principal * (1 + r) ** n
    fv_monthly = monthly * ((1 + r) ** n - 1) / r
    return fv_lump + fv_monthly


def _handle_tool(name: str, inp: Dict[str, Any]) -> str:
    inp = inp or {}
    data = storage.load()

    if name == "set_risk_profile":
        data["risk_profile"] = inp
        storage.save(data)
        return json.dumps({"status": "saved", "profile": inp})

    if name == "get_risk_profile":
        return json.dumps({"profile": data.get("risk_profile")})

    if name == "get_investment_recommendations":
        profile = data.get("risk_profile") or {}
        risk = inp.get("risk_override") or profile.get("risk_tolerance", "moderate")
        template = PORTFOLIO_TEMPLATES[risk]
        lump = inp.get("lump_sum_amount") or 0
        monthly = profile.get("monthly_investment_capacity") or 0
        existing = profile.get("existing_investments") or 0
        horizon = profile.get("investment_horizon_years") or 10

        allocation_dollars = {}
        if lump:
            for asset, pct in template["allocation"].items():
                allocation_dollars[asset] = round(lump * pct / 100, 2)

        projected_10yr = _compound_fv(
            lump + existing,
            template["expected_annual_return"],
            min(horizon, 10),
            monthly,
        )

        return json.dumps({
            "risk_level": risk,
            "description": template["description"],
            "allocation_percent": template["allocation"],
            "allocation_dollars": allocation_dollars if lump else "provide lump_sum_amount for dollar breakdown",
            "expected_annual_return": f"{template['expected_annual_return']*100:.0f}%",
            "volatility": template["expected_volatility"],
            "projected_value_in_10_years": round(projected_10yr, 2),
            "assumptions": {
                "starting_amount": (lump or 0) + existing,
                "monthly_contribution": monthly,
                "return_rate": f"{template['expected_annual_return']*100:.0f}% annually",
            },
            "key_accounts_to_use": [
                "Max 401(k) match first (free money)",
                "Then Roth IRA ($7,000/yr limit for 2024)",
                "Then taxable brokerage for remainder",
            ],
        })

    if name == "calculate_compound_growth":
        p = inp.get("principal") or 0
        r = inp.get("annual_rate") or 0
        y = inp.get("years") or 0
        m = inp.get("monthly_contribution") or 0
        fv = _compound_fv(p, r, y, m)
        total_contributed = p + m * y * 12
        growth = fv - total_contributed
        milestones = {}
        for yr in [5, 10, 20, 30]:
            if yr <= y:
                milestones[f"year_{yr}"] = round(_compound_fv(p, r, yr, m), 2)
        return json.dumps({
            "initial_investment": p,
            "monthly_contribution": m,
            "annual_return": f"{r*100:.1f}%",
            "years": y,
            "final_value": round(fv, 2),
            "total_contributed": round(total_contributed, 2),
            "total_growth_from_returns": round(growth, 2),
            "return_multiplier": f"{fv/total_contributed:.2f}x" if total_contributed else "N/A",
            "milestones": milestones,
        })

    if name == "compare_investment_scenarios":
        m = inp.get("monthly_amount") or 0
        y = inp.get("years") or 0
        start = inp.get("initial_investment") or 0
        scenarios = {
            "Conservative (5% return)": _compound_fv(start, 0.05, y, m),
            "Moderate (7% return)": _compound_fv(start, 0.07, y, m),
            "Aggressive (9% return)": _compound_fv(start, 0.09, y, m),
            "Savings Account (4.5% HYSA)": _compound_fv(start, 0.045, y, m),
            "No Investment (0%)": start + m * y * 12,
        }
        total_in = start + m * y * 12
        return json.dumps({
            "monthly_amount": m,
            "years": y,
            "total_contributed": round(total_in, 2),
            "scenarios": {k: {"final_value": round(v, 2), "gain": round(v - total_in, 2)} for k, v in scenarios.items()},
        })

    return json.dumps({"error": f"Unknown tool: {name}"})


def run(task: str) -> str:
    return tool_loop.run(SYSTEM_PROMPT, task, TOOLS, _handle_tool)
