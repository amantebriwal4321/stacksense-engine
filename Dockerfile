FROM python:3.12-slim

WORKDIR /app
COPY stacksense ./stacksense
COPY web ./web
COPY scenarios ./scenarios
COPY README.md ./README.md

ENV STACKSENSE_LLM=off
ENV STACKSENSE_HOST=0.0.0.0
ENV STACKSENSE_PORT=8000
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
CMD ["python", "-m", "stacksense", "serve"]
