import copy
import json
import os
import sys
from typing import Any, Dict, List, Optional

# Make the agents package importable — works both locally and on Vercel
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
# Also try the directory containing this file (Vercel sometimes flattens structure)
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from groq import Groq
from pydantic import BaseModel

from agents import budget_agent, debt_agent, goal_agent, investment_agent, storage

app = FastAPI(title="Personal Finance Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

ROUTER_SYSTEM = """You are a finance request router. Analyze the user's message and output ONLY valid JSON.

Available agents: "budget", "goal", "investment", "debt"

- budget: add/view income or expenses, set spending limits, spending analysis
- goal: savings goals, progress tracking, savings plans, deadlines
- investment: risk profiles, portfolio recommendations, compound growth, ETFs, Roth IRA, 401k
- debt: track debts, payoff plans, snowball/avalanche strategy, interest calculations

Output format (JSON only, no other text):
{"agents": ["budget"], "task": "rephrase the request for the agent(s) with all key numbers and context"}

Include all relevant agents. Multiple agents allowed."""

ORCHESTRATOR_SYSTEM = """You are a personal finance orchestrator. You synthesize responses from multiple
specialist agents into one clear, helpful answer. Be warm, encouraging, and specific with numbers.
Use markdown formatting for clarity."""

AGENT_MAP: Dict[str, Any] = {
    "budget": (budget_agent.run, "Budget"),
    "goal": (goal_agent.run, "Goal"),
    "investment": (investment_agent.run, "Investment"),
    "debt": (debt_agent.run, "Debt"),
}


class ChatRequest(BaseModel):
    message: str
    session_data: Optional[Dict[str, Any]] = None
    history: List[Dict[str, str]] = []


class ChatResponse(BaseModel):
    reply: str
    session_data: Dict[str, Any]
    history: List[Dict[str, str]]


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    storage.init_session(req.session_data)
    client = Groq()
    history = list(req.history)

    # Step 1: Route to agent(s)
    router_resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM},
            {"role": "user", "content": req.message},
        ],
        response_format={"type": "json_object"},
        max_tokens=200,
        temperature=0,
    )
    try:
        routing = json.loads(router_resp.choices[0].message.content)
    except Exception:
        routing = {"agents": ["budget"], "task": req.message}

    agents_to_call = routing.get("agents", ["budget"])
    task = routing.get("task", req.message)

    # Step 2: Call each specialist agent
    results: Dict[str, str] = {}
    for key in agents_to_call:
        if key in AGENT_MAP:
            fn, label = AGENT_MAP[key]
            results[label] = fn(task)

    if not results:
        reply = "I'm not sure how to help with that. Try asking about budgeting, goals, investing, or debt."
    elif len(results) == 1:
        reply = next(iter(results.values()))
    else:
        combined = "\n\n".join(f"**{label}:**\n{resp}" for label, resp in results.items())
        synth = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": req.message},
                {"role": "assistant", "content": combined},
                {"role": "user", "content": "Synthesize into one clear, helpful response."},
            ],
            max_tokens=1024,
        )
        reply = synth.choices[0].message.content or combined

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})

    return ChatResponse(
        reply=reply,
        session_data=storage.get_session() or {},
        history=history[-30:],
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve static files locally only (Vercel handles this via CDN in production)
if not os.getenv("VERCEL"):
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    if os.path.isdir(public_dir):
        app.mount("/", StaticFiles(directory=public_dir, html=True), name="static")
