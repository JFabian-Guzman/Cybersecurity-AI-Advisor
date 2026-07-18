FROM python:3.12-slim

RUN useradd --no-create-home --shell /usr/sbin/nologin sandbox

WORKDIR /sandbox
COPY analysis ./analysis
COPY sandbox/entrypoint.py .

USER sandbox

ENTRYPOINT ["python", "entrypoint.py"]
