---

# Django Attendance Management System - Agent Guidelines

## Project Overview

This is a Django-based attendance management system for Asiatech company. The system tracks employee attendance, manages work schedules, generates reports, and integrates with external Frappe/ERPNext API for real-time check-in data. It supports multiple work locations (Villas, 31pte, Nave, RioBlanco) and provides role-based access control for administrators and managers.

## Technology Stack

- **Backend**: Django 5.0.7 with Python 3.12
- **Database**: PostgreSQL 17
- **Frontend**: HTML templates with CSS/JavaScript (Spanish language)
- **Deployment**: Docker with Docker Compose (Nginx + Gunicorn)
- **External Integration**: Frappe/ERPNext API for attendance data
- **Key Dependencies**: pandas, openpyxl, requests, pytz, python-dotenv

## Project Structure

```
/home/felipillo/proyectos/g_asistencias/
├── src/                          # Main Django application
│   ├── asistencias/             # Django project settings
│   ├── core/                    # Main application (models, views, services)
│   ├── templates/               # HTML templates (Spanish)
│   ├── static/                  # CSS, JavaScript, images
│   ├── staticfiles/             # Collected static files
│   ├── media/                   # Uploaded files
│   ├── requirements.txt         # Python dependencies
│   ├── entrypoint.sh           # Docker container startup script
│   └── manage.py               # Django management
├── compose.yml                  # Docker Compose configuration
├── Dockerfile                   # Application container
├── nginx.conf                   # Reverse proxy configuration
└── .env.example                # Environment variables template
```

## Core Models

1. **Empleado**: Employee data with soft delete support
2. **Sucursal**: Work locations (Villas, 31pte, Nave, RioBlanco)
3. **Horario**: Work schedules with entry/exit times
4. **TipoTurno**: Shift types (full-time, part-time, etc.)
5. **DiaSemana**: Days of the week
6. **AsignacionHorario**: Employee schedule assignments

## Development Commands

### Local Development (with Docker)
```bash
# Start all services
docker compose up --build

# Run Django commands inside container
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py test

# View logs
docker compose logs -f web
```

### Without Docker (Development Only)
```bash
cd src
python manage.py runserver
python manage.py migrate
python manage.py test
python manage.py collectstatic --noinput
```

## Code Style Guidelines

### Python/Django Conventions
- Use Spanish for variable names, comments, and user-facing strings
- Follow Django model naming: use `db_column` for Spanish field names
- Model classes use PascalCase, variables use snake_case
- Always specify `db_column` in model fields to match database schema
- Use `related_name` for foreign key relationships

### Import Organization
```python
# Django imports first
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import render, redirect

# Third-party imports
import pandas as pd
import pytz

# Local imports
from .models import Empleado, AsignacionHorario
from .services import some_function
```

### Error Handling
- Use try-except blocks for database operations and API calls
- Return meaningful error messages in Spanish
- Use Django messages framework for user feedback
- Log errors with print statements for debugging (as seen in codebase)

### Database Patterns
- Use `get_object_or_404` for retrieving single objects
- Prefer `objects.filter()` over `objects.get()` when multiple results possible
- Use `select_related()` and `prefetch_related()` for query optimization
- Always handle database connection errors in production

### Security
- Use `@login_required` decorator for protected views
- Use `@require_http_methods` for HTTP method restrictions
- Never commit secrets; use environment variables
- Validate all user input before processing

## Testing

- Write tests in `core/tests.py`
- Use Django's TestCase class
- Test both success and error scenarios
- Mock external API calls when testing

## Configuration

### Environment Variables (Required)
```
# Database
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=asiatech
DB_HOST=db          # Use 'localhost' for local development
DB_PORT=5432        # Use 5433 for local development

# API Credentials (for Frappe integration)
ASIATECH_API_KEY=your_api_key
ASIATECH_API_SECRET=your_api_secret

# Email (SMTP)
EMAIL_HOST=smtp.purelymail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=asistencias@asiatech.com.mx
EMAIL_HOST_PASSWORD=your_email_password
```

### Django Settings
- Language: Spanish (Mexico) - `es-mx`
- Timezone: `America/Mexico_City`
- Static files: `/static/`
- Media files: `/media/`
- Database: PostgreSQL with environment-based configuration

## Key Features

1. **Employee Management**: CRUD operations with soft delete
2. **Schedule Assignment**: Complex scheduling with location and shift support
3. **Attendance Tracking**: Integration with Frappe API for real-time data
4. **Report Generation**: Excel and PDF exports with custom formatting
5. **Role-Based Access**: Admin and Manager roles with different permissions
6. **Multi-Location Support**: Villas, 31pte, Nave, RioBlanco branches
7. **Email Notifications**: SMTP integration for communications

## Business Rules

- **Tardiness**: 15-minute grace period before marking as late
- **Early Departure**: 15-minute tolerance for early exits
- **Absence**: 60-minute threshold for unjustified absence
- **Midnight Shifts**: Special handling for shifts crossing midnight
- **Leave Policies**: Different handling for paid vs unpaid leave

## Deployment Process

1. Build Docker images: `docker compose build`
2. Start services: `docker compose up -d`
3. Run migrations: `docker compose exec web python manage.py migrate`
4. Collect static files: `docker compose exec web python manage.py collectstatic --noinput`
5. Create superuser: `docker compose exec web python manage.py createsuperuser`
6. Configure Nginx for production domain

## External API Integration

The system integrates with Frappe/ERPNext API to fetch:
- Employee check-in/check-out records
- Leave applications and permissions
- Employee master data

API endpoints are configured in `core/config.py` and handled by `core/api_client.py`.

## Common Issues and Solutions

1. **Database Connection**: Check environment variables for DB_HOST and DB_PORT
2. **Static Files**: Ensure `collectstatic` is run after changes
3. **API Integration**: Verify ASIATECH_API_KEY and ASIATECH_API_SECRET in .env
4. **Email Sending**: Check SMTP credentials and SSL/TLS settings
5. **Docker Networking**: Use service names (db, web) for inter-container communication

---
