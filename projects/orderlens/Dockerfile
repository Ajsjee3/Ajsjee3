FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock
COPY --chown=10001:10001 . /app
USER 10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "orderlens.main:app", "--host", "0.0.0.0", "--port", "8000"]
