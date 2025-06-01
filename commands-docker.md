# Stop current containers
docker-compose down

# Rebuild and start containers
docker-compose up --build -d

# Rebuild everything fresh
sudo docker compose build --no-cache

# Bring everything up detached
sudo docker compose up -d

# View logs if needed
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f nginx

# However, for just Python code changes, you can often just restart the web container:
docker-compose restart web

# managemnt commands
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic

# enter the container shell
docker-compose exec web bash
docker-compose exec celery bash
docker-compose exec nginx ash  # (if Alpine) or bash (if Ubuntu-based)


# stop containers
docker-compose down

# rebuild and start containers
docker-compose up --build -d

# run Docker Compose on production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

