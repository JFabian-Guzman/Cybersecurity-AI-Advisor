FROM python:3.12-slim

RUN useradd --no-create-home --shell /usr/sbin/nologin sandbox

WORKDIR /sandbox
COPY . .

USER sandbox

ENTRYPOINT ["python", "-c", "print('sandbox skeleton: no detectors wired up yet')"]
