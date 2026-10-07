"""LLM provider abstraction with Google Gemini support and heuristic fallback."""

import json
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from inboxgpt.config import config
from inboxgpt.gmail.models import EmailCategory, EmailMessage


class CategoryDecision(BaseModel):
    category: EmailCategory = Field(
        description="Category: important, newsletter, social, promotional, or unwanted"
    )
    reasoning: str = Field(description="Brief explanation of why this category was assigned")


def get_llm():
    """Return configured ChatGoogleGenerativeAI instance if Gemini API key exists, else None."""
    api_key = config.get_gemini_api_key()
    if not api_key:
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        model_name = config.get_model_name()
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.1,
        )
    except Exception:
        return None


def heuristic_classify_email(email: EmailMessage) -> CategoryDecision:
    """Accurate offline heuristic classifier when no Gemini API key is provided."""
    sub = (email.subject or "").lower()
    snd = (email.sender or "").lower()
    s_name = (email.sender_name or "").lower()
    body = (email.body or "").lower()

    # 1. Important / High Priority (OTPs, Security, Exams, Critical Services)
    if any(w in sub for w in [
        "your code", "otp", "verification", "urgent", "security audit", "invoice",
        "receipt", "withdrawal closes", "roadmap", "critical", "action required"
    ]) or any(w in snd for w in ["telegram", "godaddy", "icpc", "stripe", "aws"]):
        return CategoryDecision(
            category=EmailCategory.IMPORTANT,
            reasoning="Critical security code, verification alert, or time-sensitive notice.",
        )
    if "IMPORTANT" in email.labels:
        return CategoryDecision(
            category=EmailCategory.IMPORTANT,
            reasoning="Flagged important by Gmail priority labels.",
        )

    # 2. Promotional discounts & marketing offers
    if any(w in sub for w in [
        "lowest price", "bootcamp", "50% off", "flash deal", "lightning deals",
        "promo code", "discount", "% off", "deals", "credit added", "1 month free"
    ]) or any(w in snd for w in ["flipkart", "classpass", "uber", "amazon", "booking"]):
        return CategoryDecision(
            category=EmailCategory.PROMOTIONAL,
            reasoning="Commercial discount, sale announcement, or marketing campaign.",
        )

    # 3. Social & Professional Networking / Job alerts
    if any(w in snd for w in [
        "linkedin", "naukri", "wellfound", "github", "reddit", "twitter", "x.com", "intch"
    ]) or any(w in sub for w in ["job alert", "job recommendation", "new jobs", "connection request"]):
        return CategoryDecision(
            category=EmailCategory.SOCIAL,
            reasoning="Social network connection, job alert, or developer activity.",
        )

    # 4. Newsletters, Developer Publications & Tech Digests
    if any(w in snd for w in [
        "medium", "gitbook", "educative", "tldr", "substack", "pragmaticengineer",
        "codeforces", "neo kim", "javier canales", "alex xu"
    ]) or any(w in sub for w in ["digest", "newsletter", "weekly", "edition", "daily"]):
        return CategoryDecision(
            category=EmailCategory.NEWSLETTER,
            reasoning="Curated developer newsletter, tech digest, or editorial update.",
        )

    # 5. Unwanted / Cold outbound pitches
    if any(w in sub for w in ["airdrop", "5,000 usdt", "crypto", "randomly selected", "b2b leads"]):
        return CategoryDecision(
            category=EmailCategory.UNWANTED,
            reasoning="Unsolicited sales pitch or suspicious message.",
        )

    return CategoryDecision(
        category=EmailCategory.IMPORTANT if email.is_unread else EmailCategory.UNCATEGORIZED,
        reasoning="Standard personal correspondence.",
    )


def classify_email(email: EmailMessage) -> CategoryDecision:
    """Classify an email message using Gemini if available, falling back to heuristic."""
    llm = get_llm()
    if llm is None:
        return heuristic_classify_email(email)

    try:
        from langchain_core.messages import SystemMessage, HumanMessage

        prompt = (
            "You are an AI email classifier. Classify the following email into exactly ONE category:\n"
            "- important: direct work emails, invoices, critical notices, executive decisions\n"
            "- newsletter: curated newsletters, digests, articles\n"
            "- social: notifications from github, linkedin, twitter, slack\n"
            "- promotional: retail discounts, sales, marketing coupons\n"
            "- unwanted: spam, cold outbound sales, suspicious phishing\n\n"
            f"From: {email.sender_name} <{email.sender}>\n"
            f"Subject: {email.subject}\n"
            f"Snippet: {email.snippet}\n\n"
            "Respond in JSON format: {\"category\": \"...\", \"reasoning\": \"...\"}"
        )

        response = llm.invoke([
            SystemMessage(content="You are a strict JSON email classification agent."),
            HumanMessage(content=prompt)
        ])
        content = response.content
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            cat_str = data.get("category", "").lower().strip()
            for cat in EmailCategory:
                if cat.value == cat_str:
                    return CategoryDecision(
                        category=cat,
                        reasoning=data.get("reasoning", "Classified by Gemini"),
                    )

        return heuristic_classify_email(email)
    except Exception:
        return heuristic_classify_email(email)
