"""Generate readable PlusCal/TLA+ artifacts for finance safety checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from safety.models import FinanceAction, SafetyPolicy


@dataclass(frozen=True)
class GeneratedTla:
    module_name: str
    tla_text: str
    cfg_text: str


def generate_tla(actions: list[FinanceAction], policy: SafetyPolicy, module_name: str) -> GeneratedTla:
    module_name = sanitize_module_name(module_name)
    cfg_text = _generate_cfg()
    tla_text = f"""---- MODULE {module_name} ----
EXTENDS Integers, Sequences, FiniteSets

\\* Generated finance safety model.
\\* Style note: this file intentionally keeps the transition system in
\\* PlusCal C-style syntax. The CLI runs:
\\*   java -cp "$TLAPLUS_JAR" pcal.trans -nocfg {module_name}.tla
\\* before running TLC, matching the workflow used by the local Platypus models.

Budget == {policy.budget}

MaxActionAmount == {policy.max_individual_action_amount}

InitialBalances == {_tla_function(policy.account_balances)}

AllowedDestinations == {_tla_set(sorted(policy.allowed_destination_accounts))}

AllowedActionKinds == {_tla_set(sorted(policy.allowed_action_types))}

Actions == {_tla_sequence([_tla_action(action) for action in actions])}

DebitKinds == {{"buy", "swap", "transfer", "withdraw"}}

CreditKinds == {{"buy", "sell", "swap", "deposit", "transfer", "withdraw"}}

ActionCount == Len(Actions)

OutflowAmount(a) ==
  IF a.kind \\in DebitKinds THEN a.amount ELSE 0

DebitedBalances(a, currentBalances) ==
  IF a.kind \\in DebitKinds /\\ a.src \\in DOMAIN currentBalances
  THEN [currentBalances EXCEPT ![a.src] = @ - a.amount]
  ELSE currentBalances

ActionViolations(a, currentSpent, currentBalances) ==
  (IF ~(a.kind \\in AllowedActionKinds)
   THEN {{"disallowed_action_kind"}} ELSE {{}})
  \\cup (IF ~(a.amount > 0)
   THEN {{"non_positive_amount"}} ELSE {{}})
  \\cup (IF a.amount > MaxActionAmount
   THEN {{"individual_action_limit_exceeded"}} ELSE {{}})
  \\cup (IF ~(a.dst \\in AllowedDestinations)
   THEN {{"disallowed_destination"}} ELSE {{}})
  \\cup (IF a.kind \\in DebitKinds /\\ ~(a.src \\in DOMAIN currentBalances)
   THEN {{"unknown_source_account"}} ELSE {{}})
  \\cup (IF currentSpent + OutflowAmount(a) > Budget
   THEN {{"budget_exceeded"}} ELSE {{}})
  \\cup (IF a.kind \\in DebitKinds /\\ a.src \\in DOMAIN currentBalances /\\ DebitedBalances(a, currentBalances)[a.src] < 0
   THEN {{"negative_source_balance"}} ELSE {{}})

BalancesAfter(a, currentBalances) ==
  LET afterDebit == DebitedBalances(a, currentBalances) IN
    IF a.kind \\in CreditKinds /\\ a.dst \\in DOMAIN afterDebit
    THEN [afterDebit EXCEPT ![a.dst] = @ + a.amount]
    ELSE afterDebit

(*
--algorithm FinanceSafety {{
variables
  idx = 1,
  balances = InitialBalances,
  spent = 0,
  violations = {{}};
{{
  while (idx <= Len(Actions)) {{
    with (a = Actions[idx]) {{
      violations := violations \\cup ActionViolations(a, spent, balances);
      spent := spent + OutflowAmount(a);
      balances := BalancesAfter(a, balances);
      idx := idx + 1;
    }};
  }};
}}
}}
*)

NoBudgetOverspend == spent <= Budget

NoNegativeBalances ==
  \\A acct \\in DOMAIN balances : balances[acct] >= 0

OnlyAllowedDestinations ==
  \\A i \\in 1..Len(Actions) : Actions[i].dst \\in AllowedDestinations

OnlyAllowedActionKinds ==
  \\A i \\in 1..Len(Actions) : Actions[i].kind \\in AllowedActionKinds

PositiveAmounts ==
  \\A i \\in 1..Len(Actions) : Actions[i].amount > 0

NoActionAboveIndividualLimit ==
  \\A i \\in 1..Len(Actions) : Actions[i].amount <= MaxActionAmount

KnownSourceAccounts ==
  \\A i \\in 1..Len(Actions) :
    Actions[i].kind \\in DebitKinds => Actions[i].src \\in DOMAIN InitialBalances

NoDetectedViolations == violations = {{}}

====
"""
    return GeneratedTla(module_name=module_name, tla_text=tla_text, cfg_text=cfg_text)


def write_tla_artifacts(generated: GeneratedTla, artifact_dir: Path) -> tuple[Path, Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    tla_path = artifact_dir / f"{generated.module_name}.tla"
    cfg_path = artifact_dir / f"{generated.module_name}.cfg"
    tla_path.write_text(generated.tla_text, encoding="utf-8")
    cfg_path.write_text(generated.cfg_text, encoding="utf-8")
    return tla_path, cfg_path


def sanitize_module_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"FinanceSafety_{cleaned}"
    return cleaned


def _generate_cfg() -> str:
    return f"""SPECIFICATION Spec

INVARIANTS
  NoBudgetOverspend
  NoNegativeBalances
  OnlyAllowedDestinations
  OnlyAllowedActionKinds
  PositiveAmounts
  NoActionAboveIndividualLimit
  KnownSourceAccounts
  NoDetectedViolations
"""


def _tla_action(action: FinanceAction) -> str:
    return (
        "[kind |-> "
        f"{_tla_string(action.action)}, "
        f"amount |-> {action.amount}, "
        f"src |-> {_tla_string(action.source)}, "
        f"dst |-> {_tla_string(action.destination)}]"
    )


def _tla_function(mapping: dict[str, int]) -> str:
    items = sorted(mapping.items())
    domain = _tla_set([key for key, _ in items])
    cases = [f"acct = {_tla_string(key)} -> {value}" for key, value in items]
    return f"[acct \\in {domain} |-> CASE {' [] '.join(cases)}]"


def _tla_sequence(items: list[str]) -> str:
    return "<<" + ", ".join(items) + ">>"


def _tla_set(items: list[str]) -> str:
    return "{" + ", ".join(_tla_string(item) for item in items) + "}"


def _tla_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
