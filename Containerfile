FROM docker.io/library/python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY examples /app/examples

EXPOSE 8080

ENTRYPOINT ["python", "-m", "sysml_v2_qvt.api_server"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
