FROM python:3.14-slim

ARG API_KEY=sk-1234567890abcdef1234567890abcdef # gitleaks:allow
ENV DATABASE_PASSWORD=SuperSecretPassw0rd! # gitleaks:allow

USER 1000

CMD ["python", "app.py"]
