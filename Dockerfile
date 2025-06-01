FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y curl netcat-traditional && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Default: gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "dcrm.wsgi:application", "--log-level", "info"]
