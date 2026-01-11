# THE BOT Platform

Educational platform with personalized learning, progress tracking, and real-time communication. Multi-role system (student, teacher, tutor, parent) with WebSocket chat, lesson scheduling, forum system, and payment integration.

## Quick Start

**Requirements**: Python 3.10+, Node.js 18+

```bash
# Setup
make install
cp .env.example .env  # Edit ENVIRONMENT, database, API keys

# Run
./start.sh

# Access
- Frontend: http://localhost:8080
- Backend: http://localhost:8000/api/
- Admin: http://localhost:8000/admin
```

## Deployment

### Quick Start

Deploy to production:
```bash
./deploy.sh
```

### Options

- `--dry-run` - Preview mode (no changes)
- `--force` - Skip confirmation prompts
- `--skip-migrations` - Hotfix mode (code only, no DB migrations)
- `--skip-frontend` - Backend code only
- `--verbose` - Detailed logging
- `--help` - Show help message

### Examples

Full deployment with confirmations:
```bash
./deploy.sh
```

Preview what would be deployed:
```bash
./deploy.sh --dry-run
```

Hotfix deployment (fast, no migrations):
```bash
./deploy.sh --skip-migrations --force
```

### Configuration

Deployment configuration is in `deploy/.env`. To customize:
```bash
cp deploy/.env.template deploy/.env
# Edit deploy/.env with your settings
```

### Services Managed

- **thebot-daphne.service** - ASGI server (WebSocket + HTTP)
- **thebot-celery-worker.service** - Async task processing
- **thebot-celery-beat.service** - Periodic task scheduler

### Auto-Rollback

If deployment fails at any point, the system automatically:
1. Stops services
2. Restores code from backup
3. Restores database
4. Restarts services
5. Reports status to user

See `deploy/README.md` for detailed module documentation.

## Running Tests

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend
cd frontend && npm test -- --run
```

## Project Structure

```
backend/
  ├── accounts/        # User management, roles, profiles
  ├── chat/            # Forum, WebSocket, real-time messaging
  ├── materials/       # Subjects, enrollments, dashboards
  ├── assignments/     # Homework and submissions
  ├── payments/        # YooKassa integration
  ├── reports/         # Progress reports
  └── core/            # Utilities, tasks, monitoring

frontend/
  ├── src/pages/       # Role-specific dashboards
  ├── src/components/  # Reusable UI components
  ├── src/hooks/       # Custom React hooks
  └── src/utils/       # Utilities, API client
```

## Tech Stack

**Backend**: Django 5.2, DRF, Channels, PostgreSQL/SQLite
**Frontend**: React 18, TypeScript, Vite, TanStack Query
**Real-time**: WebSocket (Channels), Django Channels with Redis/in-memory
**Payments**: YooKassa (recurring subscriptions)
**Notifications**: Pachca API

## Database Configuration

The application uses separate environment variables for PostgreSQL database configuration:

- `DB_ENGINE=postgresql` - Database backend (always PostgreSQL)
- `DB_HOST=localhost` - Database hostname
- `DB_PORT=5432` - Database port
- `DB_NAME=thebot_db` - Database name
- `DB_USER=postgres` - Database user
- `DB_PASSWORD=<generated>` - Database password

For local development with Docker:
```bash
# Copy example configuration
cp .env.docker .env

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

These variables are automatically used by Django settings in `backend/config/settings.py`.

### Why not DATABASE_URL?

While the system supports `DATABASE_URL` environment variable for backward compatibility, using separate `DB_*` variables is preferred because:
1. Special characters in passwords can break URL parsing
2. Separate variables are more maintainable and standard
3. Reduced parsing complexity and better security

If you have existing deployments using `DATABASE_URL`, simply remove it and use individual `DB_*` variables instead.

## Documentation

See [CLAUDE.md](CLAUDE.md) for architecture, code patterns, and development workflow.

Additional docs in `/docs/`:
- Environment setup and modes
- Scheduling system
- Forum system
- Test data generation
