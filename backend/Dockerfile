FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY --chmod=644 requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chmod=644 app.py ./app.py

EXPOSE 8099
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
