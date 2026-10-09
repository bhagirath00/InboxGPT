"""LLM provider abstraction with NVIDIA NIM, Groq, Google Gemini, and OpenAI support."""

import json
import os
import re
import warnings
from pydantic import BaseModel, Field

from inboxgpt.config import config
from inboxgpt.gmail.models import EmailCategory, EmailMessage

# Suppress fixed-sampling default notice from langchain_google_genai
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_google_genai")


class CategoryDecision(BaseModel):
    category: EmailCategory = Field(
        description="Category: important, newsletter, social, promotional, or unwanted"
    )
    reasoning: str = Field(description="Brief explanation of why this category was assigned")


def get_llm():
    """Return configured LLM instance (NVIDIA NIM free API, Groq, Gemini, or OpenAI) else None."""
    provider = config.get_active_provider()

    # 1. NVIDIA NIM (Free developer endpoints on build.nvidia.com)
    if provider == "nvidia":
        api_key = config.get_nvidia_api_key()
        if api_key:
            try:
                from langchain_openai import ChatOpenAI
                model_name = config.get_model_name()
                if not model_name or "gemini" in model_name or "glm" in model_name:
                    model_name = "meta/llama-3.2-11b-vision-instruct"
                return ChatOpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=api_key,
                    model=model_name,
                    temperature=0.1,
                    request_timeout=25,
                    max_retries=1,
                )
            except Exception:
                pass

    # 2. Groq (Free high-speed cloud inference)
    if provider == "groq":
        api_key = config.get_groq_api_key()
        if api_key:
            try:
                from langchain_openai import ChatOpenAI
                model_name = config.get_model_name()
                if not model_name or "gemini" in model_name:
                    model_name = "llama-3.3-70b-versatile"
                return ChatOpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=api_key,
                    model=model_name,
                    temperature=0.1,
                )
            except Exception:
                pass

    # 3. Google Gemini (Native API)
    if provider == "gemini":
        api_key = config.get_gemini_api_key()
        if api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                model_name = config.get_model_name()
                if not model_name or "glm" in model_name or "llama" in model_name or "2.5" in model_name or "3.5" in model_name:
                    model_name = "gemini-3.8-flash"
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=api_key,
                )
            except Exception:
                pass

    # 4. Standard OpenAI-compatible endpoint
    if provider == "openai":
        api_key = config.get_openai_api_key()
        if api_key:
            try:
                from langchain_openai import ChatOpenAI
                model_name = config.get_model_name()
                if not model_name or "gemini" in model_name:
                    model_name = "gpt-4o-mini"
                base_url = os.getenv("OPENAI_BASE_URL")
                return ChatOpenAI(
                    base_url=base_url,
                    api_key=api_key,
                    model=model_name,
                    temperature=0.1,
                )
            except Exception:
                pass

    # Fallbacks if provider wasn't explicitly selected
    if config.get_nvidia_api_key():
        try:
            from langchain_openai import ChatOpenAI
            model_name = config.get_model_name()
            if not model_name or "glm" in model_name:
                model_name = "meta/llama-3.2-11b-vision-instruct"
            return ChatOpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=config.get_nvidia_api_key(),
                model=model_name,
                temperature=0.1,
                request_timeout=25,
                max_retries=1,
            )
        except Exception:
            pass

    if config.get_gemini_api_key():
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-3.8-flash",
                google_api_key=config.get_gemini_api_key(),
            )
        except Exception:
            pass

    return None


def heuristic_classify_email(email: EmailMessage) -> CategoryDecision:
    sub = (email.subject or '').lower()
    snd = (email.sender or '').lower()
    s_name = (email.sender_name or '').lower()
    body = (email.body or '').lower()

    # 1. Unwanted / Scams / Phishing / Fraud
    unwanted_kws = [
        'airdrop', 'crypto', 'eth airdrop', 'usdt', 'randomly selected',
        'won ', 'you won', 'lottery', 'euro millions', 'inheritance', 'barrister',
        'unclaimed estate', 'no credit check', 'personal loan', 'fast cash',
        'miracle cure', 'diet pills', 'lose 30 pounds', 'singles in your city',
        'dating', 'matches in your zip', 'mailbox is full', 'quarantined',
        'paypa1', 'trading system', 'trading bot', 'passive income', 'backlinks',
        'b2b leads', 'unsolicited'
    ]
    if any(k in sub or k in body for k in unwanted_kws) or any(s in snd for s in ['giveaway', 'lottery', 'paypa1', 'fastcash', 'miracle']):
        return CategoryDecision(
            category=EmailCategory.UNWANTED,
            reasoning='Detected spam keywords, unsolicited lottery, or phishing pattern.',
        )

    # 2. Critical Security, Auth, Invoices, Work Tasks (Important)
    important_kws = [
        'your code', 'otp', 'verification', 'security alert', 'security warning',
        'security audit', 'invoice', 'receipt', 'paystub', 'payroll', '1099',
        'tax document', 'e-ticket', 'signoff required', 'action required',
        'incident', 'post-mortem', 'failover', 'candidate interview', 'scorecard',
        'hvac inspection', 'maintenance notice', 'open enrollment', 'contract agreement',
        'notes from our 1:1', 'pr #', 'code review', 'password reset', 'debit card activity'
    ]
    if any(k in sub for k in important_kws) or any(s in snd for s in ['auth0', 'chase', 'stripe', 'gusto', 'turbotax', 'united.com']):
        return CategoryDecision(
            category=EmailCategory.IMPORTANT,
            reasoning='Critical security code, financial statement, or direct work priority.',
        )
    if 'IMPORTANT' in email.labels or 'STARRED' in email.labels or 'STAR' in email.labels:
        return CategoryDecision(
            category=EmailCategory.IMPORTANT,
            reasoning='Flagged important by user star or Gmail priority labels.',
        )

    # 3. Newsletters & Editorial Publications
    newsletter_kws = [
        'tldr', 'morning brew', 'weekly', 'digest', 'newsletter', 'issue ',
        'bytebytego', 'hacker newsletter', 'system design', 'this week in',
        'changelog', 'import ai', 'deno', 'deno weekly', 'roundup', 'daily digest'
    ]
    if any(s in snd for s in ['deno', 'tldr', 'morningbrew', 'pythonweekly', 'substack', 'hackernewsletter', 'medium', 'importai', 'changelog', 'rust-lang']) or any(k in sub for k in newsletter_kws):
        return CategoryDecision(
            category=EmailCategory.NEWSLETTER,
            reasoning='Curated developer newsletter, tech digest, or editorial update.',
        )

    # 4. Promotional Marketing, Sales, Discounts & Coupons
    promo_kws = [
        '% off', 'deal', 'deals', 'coupon', 'coupons', 'sale', 'flash sale',
        'lightning deals', 'save big', 'zero dollar delivery', 'free delivery',
        'double star', 'discount', 'coursera plus', 'webinar', 'free webinar',
        'promo code', 'limited time', 'order online', 'cashback', 'special offer'
    ]
    if any(s in snd for s in ['amazon deals', 'ubereats', 'target', 'coursera', 'nordvpn', 'udemy', 'doordash', 'starbucks', 'dominos']) or any(k in sub for k in promo_kws):
        return CategoryDecision(
            category=EmailCategory.PROMOTIONAL,
            reasoning='Commercial discount, sale announcement, or marketing campaign.',
        )

    # 5. Social & Personal Networking
    social_kws = [
        'dinner plans', 'catch up', 'coffee', 'meetup', 'reunion', 'drinks',
        'family', 'sunday around', 'lunch together', 'connection request'
    ]
    if any(s in snd for s in ['linkedin', 'reddit', 'twitter', 'x.com', 'meetup']) or any(k in sub for k in social_kws):
        return CategoryDecision(
            category=EmailCategory.SOCIAL,
            reasoning='Social network connection, community event, or personal plan.',
        )

    return CategoryDecision(
        category=EmailCategory.IMPORTANT if email.is_unread else EmailCategory.UNCATEGORIZED,
        reasoning='Standard direct correspondence.',
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
