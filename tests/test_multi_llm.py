"""Unit tests for multi-provider AI model support (NVIDIA NIM free API, Groq, Gemini, Heuristics)."""

from urllib.parse import urlparse

from inboxgpt.agent.llm import get_llm, heuristic_classify_email
from inboxgpt.gmail.models import EmailCategory, EmailMessage


def test_nvidia_nim_provider_instantiation(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-dummy-key")
    monkeypatch.setenv("INBOXGPT_PROVIDER", "nvidia")

    llm = get_llm()
    assert llm is not None
    assert type(llm).__name__ == "ChatOpenAI"
    assert "integrate.api.nvidia.com" in str(llm.openai_api_base)


def test_groq_provider_instantiation(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-dummy-key")
    monkeypatch.setenv("INBOXGPT_PROVIDER", "groq")

    llm = get_llm()
    assert llm is not None
    assert type(llm).__name__ == "ChatOpenAI"
    base_url = str(llm.openai_api_base)
    assert urlparse(base_url).hostname == "api.groq.com"


def test_heuristic_fallback_when_no_llm_configured(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("INBOXGPT_PROVIDER", "heuristic")

    llm = get_llm()
    assert llm is None

    # Test heuristic classification still works flawlessly
    msg = EmailMessage(
        id="otp_test",
        thread_id="th_1",
        sender="auth@bank.com",
        subject="Your OTP verification code: 928103",
        snippet="Use this code to login",
    )
    decision = heuristic_classify_email(msg)
    assert decision.category == EmailCategory.IMPORTANT
