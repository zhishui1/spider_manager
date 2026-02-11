# Spider Manager Backend

This is the backend part of the Spider Manager Platform.

## Requirements

- Python 3.8+
- Django 4.0+
- Django REST Framework
- Channels (for WebSocket support)
- Redis

## Installation

1. Install dependencies:
```bash
pip install django djangorestframework channels channels_redis redis
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Start the server:
```bash
python manage.py runserver
```

## Project Structure

- `api/` - REST API endpoints
- `spiders/` - Spider management and execution
- `models/` - Database models
