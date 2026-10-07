"""Persistent cross-session memory for InboxGPT agent."""

import json
from pathlib import Path
from typing import List
from inboxgpt.config import config


class AgentMemory:
    """Stores and retrieves user-defined rules and learned preferences across sessions."""

    def __init__(self, memory_file: Path = None):
        self.memory_file = memory_file or (config.config_dir / "agent_memory.json")

    def _load(self) -> List[str]:
        if not self.memory_file.exists():
            # Initial default smart rules
            return [
                "Never delete or trash emails marked as Starred or Important.",
                "Never delete authentication codes, OTPs, or password resets.",
                "Invoices and payment receipts must be archived, never deleted.",
            ]
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, rules: List[str]) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2)
        except Exception:
            pass

    def get_rules(self) -> List[str]:
        return self._load()

    def add_rule(self, rule: str) -> None:
        clean = rule.strip()
        if not clean:
            return
        rules = self._load()
        if clean not in rules:
            rules.append(clean)
            self._save(rules)

    def remove_rule(self, rule_or_index) -> bool:
        rules = self._load()
        if isinstance(rule_or_index, int) and 0 <= rule_or_index < len(rules):
            rules.pop(rule_or_index)
            self._save(rules)
            return True
        elif isinstance(rule_or_index, str) and rule_or_index in rules:
            rules.remove(rule_or_index)
            self._save(rules)
            return True
        return False

    def get_context_prompt(self) -> str:
        rules = self.get_rules()
        if not rules:
            return "No custom preferences saved."
        return "\n".join(f"- {r}" for r in rules)


memory = AgentMemory()
