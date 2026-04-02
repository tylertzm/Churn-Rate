FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers
RUN playwright install --with-deps

COPY . .

# Expose port
EXPOSE 8000

# Run the app
CMD ["python", "backend/backend_api.py"]