# The report plus the server that rebuilds it from automation_web_2.0 @ main
# whenever a visitor opens it. Deploy on Coolify with:
#   Build pack: Dockerfile    Port: 8080    Health check: /healthz
#   Env (secret): AUTOMATION_REPO_TOKEN = classic PAT, `repo` scope
#   Optional volume at /data keeps the clone across restarts (else ~30s to re-clone)
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY *.py *.json index.html ./
ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 CMD python3 -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz')"
CMD ["python3", "server.py"]
