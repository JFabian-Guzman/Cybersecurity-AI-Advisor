FROM python:3.12-slim

RUN useradd --no-create-home --shell /usr/sbin/nologin sandbox

RUN pip install --no-cache-dir pyyaml==6.0.3

WORKDIR /sandbox
COPY analysis ./analysis
COPY sandbox/entrypoint.py .

USER sandbox

ENTRYPOINT ["python", "entrypoint.py"]
