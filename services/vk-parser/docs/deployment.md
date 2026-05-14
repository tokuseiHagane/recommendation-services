# Развёртывание

## Docker Compose

### Запуск всех сервисов

```bash
docker-compose up -d
```

### docker-compose.yml

```yaml
version: "3.9"

services:
  app:
    build: .
    container_name: vk-parser-service
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/porto_db
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=porto_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

## Production настройки

### Environment Variables

```env
# Production
APP_ENV=production
APP_DEBUG=false

# Security
JWT_SECRET_KEY=<strong-secret-key>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Logfire
LOGFIRE_TOKEN=<your-logfire-token>
LOGFIRE_ENVIRONMENT=production
```

### Nginx Reverse Proxy

```nginx
upstream vk_parser {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    location /api/v1/parse {
        proxy_pass http://vk_parser;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Масштабирование

### Горизонтальное масштабирование

```yaml
# docker-compose.yml
services:
  app:
    deploy:
      replicas: 3
```

### Load Balancer

Используйте nginx или traefik для балансировки между репликами.

## Мониторинг

### Logfire

```env
LOGFIRE_TOKEN=your-token
LOGFIRE_PROJECT_NAME=vk-parser-service
LOGFIRE_ENVIRONMENT=production
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## Backup

### PostgreSQL

База данных управляется AuthorizationService. Бэкапы делаются там.

### Redis

```bash
docker exec vkparser-redis redis-cli BGSAVE
```

