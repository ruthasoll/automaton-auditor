# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install system dependencies (git is required for repo_tools)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv globally
RUN pip install --no-cache-dir uv

# Copy uv dependency files
COPY pyproject.toml uv.lock ./

# Install project dependencies securely
RUN uv sync --frozen --no-dev

# Copy the rest of the application code
COPY . .

# Ensure the output directory exists
RUN mkdir -p audit

# Inform Docker that the container runs the graph by default
# For usage: docker run --rm --env-file .env -v $(pwd)/audit:/app/audit automaton-auditor --repo <url> --pdf <path>
ENTRYPOINT ["uv", "run", "python", "src/graph.py"]
