# D-11: Microsoft Playwright image (pre-installed Chromium + system deps)
# Pin version to match playwright Python package exactly (Pitfall 2)
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies (no dev deps in production)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# Playwright browsers already installed in base image
# No need for: RUN playwright install chromium

# Run as non-root for security
# (Playwright base image runs as root by default for browser access;
#  --no-sandbox flag in CHROMIUM_ARGS handles this)

CMD ["uv", "run", "python", "-m", "price_spy"]
