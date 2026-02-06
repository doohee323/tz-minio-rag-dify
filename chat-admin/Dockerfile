# TZ-Chat Gateway (FastAPI) - single service (tz-cointutor style)
# Multi-stage: build Vue frontend at root, then Python runtime
FROM node:18-alpine AS frontend
WORKDIR /build
COPY src ./src
COPY public ./public
COPY config ./config
COPY package*.json vue.config.js babel.config.js ./
COPY env-frontend .env
RUN CYPRESS_INSTALL_BINARY=0 npm install --no-audit --loglevel=info && npm run build:prod

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl && mv kubectl /usr/local/bin/

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY sample ./sample
COPY --from=frontend /build/dist ./static
# SPA fallback: StaticFiles html=True serves 404.html on 404
RUN cp ./static/index.html ./static/404.html 2>/dev/null || true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
