FROM python:3.12-slim

WORKDIR /app/kyra

# Install dependencies first to take advantage of Docker layer caching
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-dev.txt \
    && pip install --no-cache-dir uvicorn

# Copy the actual application code
COPY . .

ENV PYTHONPATH=/app/kyra

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
