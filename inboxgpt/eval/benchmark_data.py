"""Curated 50-email ground-truth evaluation benchmark loader for InboxGPT."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import List
from inboxgpt.gmail.models import EmailCategory, EmailMessage


@dataclass
class BenchmarkItem:
    email: EmailMessage
    expected_category: EmailCategory
    is_protected: bool
    allowed_actions: List[str]


def load_benchmark_dataset() -> List[BenchmarkItem]:
    json_path = Path(__file__).parent / "benchmark_data.json"
    with open(json_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    category_map = {
        "important": EmailCategory.IMPORTANT,
        "newsletter": EmailCategory.NEWSLETTER,
        "promotional": EmailCategory.PROMOTIONAL,
        "unwanted": EmailCategory.UNWANTED,
        "social": EmailCategory.SOCIAL,
    }

    benchmark_items = []
    for item in raw_items:
        (
            item_id,
            sender,
            sender_name,
            subject,
            body,
            date_str,
            labels,
            is_unread,
            cat_str,
            is_prot,
            allowed_acts,
        ) = item

        expected_cat = category_map[cat_str]
        email_msg = EmailMessage(
            id=item_id,
            thread_id=f"th_{item_id}",
            sender=sender,
            sender_name=sender_name,
            recipient="user@example.com",
            subject=subject,
            snippet=body[:80],
            body=body,
            date=date_str,
            labels=labels,
            is_unread=is_unread,
            category=expected_cat,
        )
        benchmark_items.append(
            BenchmarkItem(
                email=email_msg,
                expected_category=expected_cat,
                is_protected=is_prot,
                allowed_actions=allowed_acts,
            )
        )
    return benchmark_items
