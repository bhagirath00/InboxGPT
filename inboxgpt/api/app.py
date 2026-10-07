"""FastAPI backend application for InboxGPT API and future hosted server deployment."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from inboxgpt.api.routes import router


def create_app() -> FastAPI:
    application = FastAPI(
        title="InboxGPT Agent API",
        description="REST API interface for InboxGPT email analysis, categorization, and human-in-the-loop actions.",
        version="0.1.0",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(router, prefix="/api/v1")

    @application.get("/health")
    def health_check():
        return {"status": "ok", "service": "InboxGPT Backend"}

    return application


app = create_app()
