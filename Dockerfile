FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project specification files first for caching
COPY pyproject.toml README.md ./

# Install InboxGPT and its dependencies
COPY inboxgpt ./inboxgpt
RUN pip install --upgrade pip && \
    pip install -e .

# Volume mount point for persistent auth tokens
VOLUME ["/root/.inboxgpt"]

ENTRYPOINT ["inboxgpt"]
CMD ["--help"]
