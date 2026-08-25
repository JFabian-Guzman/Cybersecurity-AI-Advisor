FROM python:3.14-slim

RUN apt-get update && apt-get install -y curl
RUN pip install requests

USER 1000

CMD ["python", "app.py"]
