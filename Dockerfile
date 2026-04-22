FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir ".[web]"

EXPOSE 8766

CMD ["agent-learner", "dashboard", "--project-root", "/app", "--host", "0.0.0.0", "--port", "8766", "--no-build"]
