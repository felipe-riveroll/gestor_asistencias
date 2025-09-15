# Django Asistencias Project - Context for Qwen Code

## Project Overview

This is a Django-based web application for managing employee attendance and schedules. It allows organizations to track employees, assign shifts, manage work locations, and automate attendance logging.

### Key Technologies
- **Backend**: Django 5.2.4 (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML templates with CSS/JavaScript
- **Deployment**: Docker with Docker Compose (Nginx + Gunicorn)
- **Dependencies**:
  - `django`
  - `psycopg[binary]` (PostgreSQL adapter)
  - `pyyaml` (for data fixtures)
  - `gunicorn` (WSGI server)

---

## Project Structure

```
django-asistencias/
├── compose.yml              # Docker Compose configuration
├── Dockerfile               # Docker image definition
├── nginx.conf               # Nginx reverse proxy configuration
├── src/                     # Main Django application
│   ├── asistencias/         # Django project settings
│   ├── core/                # Main application with models and business logic
│   ├── templates/           # HTML templates
│   ├── static/              # CSS, JavaScript, and image assets
│   ├── staticfiles/         # Collected static files (generated)
│   ├── media/               # Uploaded media files
│   ├── manage.py            # Django management script
│   ├── requirements.txt     # Python dependencies
│   ├── entrypoint.sh        # Docker entrypoint script
│   ├── assign_users.py      # Script for user management
│   └── initial_data_numerado.yaml  # Initial data fixture
```

---

## Core Functionality

### Data Models
1. **Empleado** – Employee details including names, codes, and user linkage.
2. **Sucursal** – Work location/branch information.
3. **TipoTurno** – Shift pattern definitions (e.g., Monday-Friday).
4. **Horario** – Schedule with entry and exit times.
5. **DiaSemana** – Days of the week reference data.
6. **AsignacionHorario** – Links employees to their schedules, locations, and shift types.

### Authentication & Authorization
- Email-based authentication system.
- Role-based access control via "Admin" and "Manager" groups.
- Employees can be linked to Django User accounts.

### User Interface
- Login page with email/password authentication.
- Role-specific dashboards.
- Responsive design using Font Awesome icons.

---

## Development Setup

> ⚠️ This project is fully containerized using Docker. All development commands should be run inside the containers unless explicitly stated otherwise.

### Prerequisites
- Docker and Docker Compose installed
- Optional: Python 3.13+ and PostgreSQL for local development (not required if using Docker)

### Running with Docker (Recommended)

1. Create a `.env` file in the root directory with the following content:
   ```env
   POSTGRES_DB=asistencias
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   DB_HOST=db
   DB_PORT=5432
   ```

2. Build and start the services:
   ```bash
   docker-compose up --build
   ```

3. Access the app at [http://localhost](http://localhost).

4. Run any Django command inside the `web` container:
   ```bash
   docker-compose exec web uv run manage.py <command>
   ```

   Examples:
   ```bash
   docker-compose exec web uv run manage.py migrate
   docker-compose exec web uv run manage.py createsuperuser
   docker-compose exec web uv run manage.py collectstatic
   ```

---

## Deployment Architecture

The application uses a multi-container architecture:

1. **web**: Django application served by Gunicorn
2. **nginx**: Reverse proxy handling static files and routing
3. **db**: PostgreSQL database

All services are orchestrated using Docker Compose.

---

## Key Commands

### Development (Inside Container)

| Command | Description |
|--------|-------------|
| `docker-compose exec web uv run manage.py migrate` | Apply database migrations |
| `docker-compose exec web uv run manage.py collectstatic` | Collect static files |
| `docker-compose exec web uv run manage.py loaddata initial_data_numerado.yaml` | Load initial data |
| `docker-compose exec web uv run python assign_users.py` | Create and link users to employees |

### Docker Management

| Command | Description |
|--------|-------------|
| `docker-compose up` | Start all services |
| `docker-compose up --build` | Rebuild and start services |
| `docker-compose down` | Stop and remove containers |
| `docker-compose logs -f web` | Follow logs from the web service |

---

## Custom Scripts

### `assign_users.py`

This script automates the creation and assignment of Django users to employees:

1. Creates a new Django User account
2. Assigns the user to the "Manager" group
3. Links the user to an existing Employee record

To run:
```bash
docker-compose exec web uv run python assign_users.py
```

---

## Data Management

Initial data is loaded using YAML fixtures. The fixture includes:

- Weekdays (`DiaSemana`)
- Branches (`Sucursal`)
- Shift types (`TipoTurno`)
- Schedules (`Horario`)
- Employee records and assignments

To load initial data:
```bash
docker-compose exec web uv run manage.py loaddata initial_data_numerado.yaml
```

---

## Configuration

### Django Settings
- Language: Spanish (Mexico) – `es-mx`
- Timezone: `America/Mexico_City`
- Static files: `/static/`
- Media files: `/media/`
- Database configuration via environment variables

### Environment Variables

| Variable | Description |
|----------|-------------|
| `POSTGRES_DB` | Name of the PostgreSQL database |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Hostname of the database service (usually `db`) |
| `DB_PORT` | Port number of the database (default: 5432) |

---