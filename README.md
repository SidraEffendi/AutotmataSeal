# AutomataSeal — Personal Finance Agent

A multi-agent AI assistant for personal finance powered by [Groq](https://groq.com). Chat with it to track budgets, set savings goals, get investment recommendations, and build debt payoff plans.

**Live demo:** https://automata-seal.vercel.app

---

## What it does

Four specialist AI agents work together behind a single chat interface:

| Agent | Capabilities |
|---|---|
| **Budget Tracker** | Log income & expenses, set monthly category limits, view spending breakdowns |
| **Goal Planner** | Create savings goals with deadlines, calculate required monthly savings, track progress |
| **Investment Guide** | Risk profiling, ETF/index fund portfolio allocations, compound growth projections |
| **Debt Eliminator** | Track debts, simulate snowball vs avalanche payoff plans, show interest saved |

---

## Architecture

```
AutomataSeal/
├── api/index.py            # FastAPI backend (works on Vercel + localhost)
├── agents/
│   ├── budget_agent.py     # Budget tracking specialist
│   ├── goal_agent.py       # Savings goal planning specialist
│   ├── investment_agent.py # Investment guide specialist
│   ├── debt_agent.py       # Debt payoff specialist
│   ├── tla_safety_agent.py # TLA+ safety wrapper for proposed actions
│   ├── tool_loop.py        # Shared JSON-mode agentic loop
│   └── storage.py          # Data persistence (file locally, in-memory on Vercel)
├── safety/                 # Action parser, policy checks, PlusCal/TLA generation, TLC runner
├── public/index.html       # Chat UI (dark theme, markdown rendering)
├── main.py                 # Optional CLI entry point
└── vercel.json             # Vercel deployment config
```

The orchestrator routes each user message to the right specialist agent(s) using a JSON-mode classifier. Each agent runs its own tool loop — reading/writing financial data — then returns a markdown response. Session data is stored in the browser via `localStorage`.

The `tla-integration` branch also includes a TLA+ safety gate. It can normalize concrete finance-agent actions, generate readable PlusCal/TLA+ specs, translate them with `pcal.trans`, and run TLC before any real-world action is approved.

---

## Running locally

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Add your Groq API key**
```bash
cp .env.example .env
# Add your key from https://console.groq.com
```

The app prefers `GROQ_API_KEY`. It also accepts `GROK_API_KEY` as an alias for
GitHub agent secrets or deployments that already use that spelling.

**3. Start the web app**
```bash
GROQ_API_KEY=your_key python3 -m uvicorn api.index:app --port 8000
```
Open **http://localhost:8000**

**Or use the terminal CLI**
```bash
python3 main.py
```

---

## Deploying to Vercel

```bash
npm install -g vercel
vercel                              # link project
vercel env add GROQ_API_KEY production  # add your Groq key
# or use GROK_API_KEY; the app maps it to GROQ_API_KEY at runtime
vercel --prod                       # deploy
```

---

## Example prompts

- `I spent $120 on groceries today`
- `I want to save $10,000 for an emergency fund by December 2026`
- `I'm 28, moderate risk, can invest $500/month for 25 years — what should I buy?`
- `I have a credit card with $5,000 at 22% APR — show me a payoff plan with $200 extra/month`

---

## Tech stack

- **LLM** — Groq `llama-3.1-8b-instant`
- **Backend** — FastAPI + Python
- **Frontend** — HTML/CSS/JS + [marked.js](https://marked.js.org)
- **Hosting** — Vercel
- **CLI** — [Rich](https://github.com/Textualize/rich)
