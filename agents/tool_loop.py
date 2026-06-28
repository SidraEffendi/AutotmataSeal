"""
JSON-mode agentic loop for Groq.
Avoids the raw <function=...> format bug in llama-3.3-70b-versatile by using
response_format=json_object instead of the tool_choice API.
"""
import json
from typing import Any, Callable, Dict, List

from groq import Groq

MODEL = "llama-3.3-70b-versatile"
MAX_STEPS = 8


def _tools_to_description(tools: List[Dict]) -> str:
    lines = []
    for t in tools:
        fn = t["function"]
        params = fn.get("parameters", {}).get("properties", {})
        required = fn.get("parameters", {}).get("required", [])
        param_desc = ", ".join(
            f"{k} ({'required' if k in required else 'optional'}): {v.get('description', v.get('type', ''))}"
            for k, v in params.items()
        )
        lines.append(f"  - {fn['name']}: {fn['description']}")
        if param_desc:
            lines.append(f"    Args: {param_desc}")
    return "\n".join(lines)


LOOP_SUFFIX = """

## Tool use instructions
You have tools available. Always call at least one tool before giving a final answer.
Output ONLY valid JSON each turn — no prose, no markdown.

To call a tool:
{{"action": "call_tool", "tool": "<tool_name>", "args": {{<arguments>}}}}

To give your final answer after you have the data you need:
{{"action": "answer", "text": "<your full helpful response in markdown>"}}

Available tools:
{tools_description}"""


def run(
    system_prompt: str,
    task: str,
    tools: List[Dict],
    handle_tool: Callable[[str, Dict[str, Any]], str],
) -> str:
    client = Groq()
    tools_description = _tools_to_description(tools)
    enhanced_system = system_prompt + LOOP_SUFFIX.format(tools_description=tools_description)

    messages = [
        {"role": "system", "content": enhanced_system},
        {"role": "user", "content": task},
    ]

    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=2048,
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        action = parsed.get("action", "")

        if action == "answer":
            return parsed.get("text", raw)

        if action == "call_tool":
            tool_name = parsed.get("tool", "")
            args = parsed.get("args") or {}
            tool_result = handle_tool(tool_name, args)
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": f"Tool result for {tool_name}:\n{tool_result}"})
        else:
            # Model output something unexpected — treat as final answer
            return parsed.get("text", raw)

    return "I was unable to complete the request within the allowed steps."
