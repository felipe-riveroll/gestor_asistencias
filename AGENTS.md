# Django Attendance Management System - Agent Guidelines

## Development Commands
- **Run development server**: `cd src && python manage.py runserver`
- **Run tests**: `cd src && python manage.py test`
- **Run single test**: `cd src && python manage.py test core.tests.TestClassName.test_method_name`
- **Create migrations**: `cd src && python manage.py makemigrations`
- **Apply migrations**: `cd src && python manage.py migrate`
- **Collect static files**: `cd src && python manage.py collectstatic --noinput`
- **Create superuser**: `cd src && python manage.py createsuperuser`

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

### Testing
- Write tests in `core/tests.py`
- Use Django's TestCase class
- Test both success and error scenarios
- Mock external API calls when testing

## Project Structure
- Main app: `core/`
- Templates: `src/templates/`
- Static files: `src/static/`
- Django settings: `src/asistencias/settings.py`
- Database: PostgreSQL with Docker