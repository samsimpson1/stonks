FROM ghcr.io/astral-sh/uv:0.8.11-alpine

WORKDIR /app

COPY * .

RUN adduser -u 568 -D app && chown -R app /app

USER app

RUN uv sync --locked

EXPOSE 9100

CMD ["uv", "run", "scrape.py"]