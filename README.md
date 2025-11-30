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

## Documentation

See [CLAUDE.md](CLAUDE.md) for architecture, code patterns, and development workflow.

Additional docs in `/docs/`:
- Environment setup and modes
- Database configuration
- Scheduling system
- Forum system
- Test data generation
