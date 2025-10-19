# AI Club Bootcamp

![AI Club Bootcamp](./images/readme_image_bootcamp.png)

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-5A67D8?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/claude-code)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)](https://www.postgresql.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript)](https://www.typescriptlang.org/)


> A comprehensive, production-ready AI education platform providing free, accessible learning pathways for modern AI tools and techniques. Developed in collaboration with the RIT AI Club.

## Overview

AI Club Bootcamp is a full-stack learning management system designed to democratize AI education. The platform features structured learning pathways, interactive quizzes, hands-on projects, and an instructor-led review system to guide students through practical AI skills from foundational concepts to advanced applications.

### Key Highlights

- **Free and Open Source**: Entire codebase publicly available to support AI education globally
- **Instructor-Approved Learning**: Module completion requires instructor review and approval
- **Interactive Assessments**: Built-in quiz system with immediate feedback and progress tracking
- **Project Submissions**: File upload system with instructor grading and review workflows
- **Progress Tracking**: Comprehensive analytics for students and instructors
- **Production Architecture**: Enterprise-grade authentication, database design, and deployment strategy

## Architecture

### Technology Stack

**Frontend**
- Next.js 15 with App Router and Server Components
- TypeScript for type safety
- Tailwind CSS for responsive design
- Framer Motion for smooth animations
- Heroicons for consistent iconography

**Backend**
- FastAPI with async Python
- PostgreSQL 15 with advanced migrations
- JWT authentication with refresh token rotation
- Google Cloud Storage for file management
- Rate limiting and security middleware

**Infrastructure**
- Docker Compose for local development
- Google Cloud Run for production deployment
- Cloud SQL for managed PostgreSQL
- Environment-based configuration

### System Design

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Next.js 15    │ ──────> │  FastAPI Backend │ ──────> │  PostgreSQL 15  │
│   Frontend      │  REST   │  Authentication  │  Async  │    Database     │
│   (Port 3000)   │  APIs   │   (Port 8000)    │  SQLAlc │   (Port 5432)   │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                      │
                                      │
                                      v
                            ┌──────────────────┐
                            │  Google Cloud    │
                            │     Storage      │
                            │  (Submissions)   │
                            └──────────────────┘
```

## Features

### For Students
- **Learning Pathways**: Structured curriculum covering AI tools, prompt engineering, image generation, and more
- **Interactive Quizzes**: Immediate feedback with 80% passing requirement
- **Project Submissions**: Upload work for instructor review with resubmission support
- **Progress Dashboard**: Track completion status across all modules and pathways
- **Resource Library**: Curated videos, articles, and exercises

### For Instructors
- **Admin Dashboard**: Flask-based grading interface with dark theme
- **Submission Review**: View, download, and grade student work
- **Module Approval**: Accept or reject module completions with feedback
- **Analytics**: Monitor student progress and submission queues
- **Batch Operations**: Efficient workflows for reviewing multiple submissions

### Technical Features
- Secure JWT authentication with httpOnly cookies
- Refresh token rotation for enhanced security
- Rate limiting on sensitive endpoints
- Database migrations with Alembic
- Responsive design for mobile, tablet, and desktop
- Real-time progress synchronization
- File validation and secure storage

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ and npm
- Python 3.11+
- PostgreSQL 15 (or use Docker)

### Local Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/RomanSlack/ai_bootcamp_backend.git
   cd ai_bootcamp_backend
   ```

2. **Start Backend Services**
   ```bash
   docker-compose up -d
   ```
   This launches PostgreSQL and the FastAPI auth service on port 8000.

3. **Configure Environment**

   Backend environment variables are configured in `aibc_auth/.env`:
   ```env
   DATABASE_URL=postgresql://aibc_admin:AIbc2024SecurePass@postgres:5432/aibc_db
   SECRET_KEY=your-secret-key-here
   PORT=8000
   ```

4. **Start Frontend Development Server**
   ```bash
   cd ai_bootcamp_frontend
   npm install
   npm run dev
   ```
   Frontend runs on http://localhost:3000

5. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Admin Dashboard: `cd admin_dashboard && python app.py`

### Database Setup

The database is automatically initialized with the schema on first startup via `init-complete.sql`. No manual migrations are required for initial setup.

For production or schema updates:
```bash
cd aibc_auth
alembic upgrade head
```

## Project Structure

```
ai_bootcamp_backend/
├── aibc_auth/                  # FastAPI authentication service
│   ├── app/
│   │   ├── api/                # API endpoints
│   │   ├── core/               # Security, config, GCS
│   │   ├── crud/               # Database operations
│   │   ├── models/             # SQLAlchemy models
│   │   └── schemas/            # Pydantic schemas
│   ├── alembic/                # Database migrations
│   └── Dockerfile
├── ai_bootcamp_frontend/       # Next.js 15 application
│   ├── app/                    # App router pages
│   ├── components/             # React components
│   ├── lib/                    # Utilities and services
│   └── public/                 # Static assets
├── admin_dashboard/            # Flask instructor dashboard
│   ├── app.py                  # Main Flask application
│   └── templates/              # Dashboard templates
├── docs/                       # Technical documentation
├── images/                     # README assets
├── docker-compose.yml          # Local orchestration
└── init-complete.sql           # Database initialization
```

## Documentation

Detailed documentation is available in the `docs/` directory:

- [API Resource Tracking](./docs/API_RESOURCE_TRACKING.md)
- [Resource Tracking Implementation](./docs/RESOURCE_TRACKING_IMPLEMENTATION.md)
- [Resource Tracking Configuration](./docs/RESOURCE_TRACKING_CONFIG.md)

## Deployment

### Google Cloud Run

The platform is deployed on Google Cloud infrastructure:

1. **Backend**: FastAPI service on Cloud Run
2. **Database**: Cloud SQL PostgreSQL instance
3. **Storage**: Google Cloud Storage for file submissions
4. **Frontend**: Vercel or Cloud Run

Environment configuration for production is managed via `.env.production` files.

## Development

### Development Methodology

This project was developed using a custom Claude Code prompting structure, demonstrating the capabilities of AI-assisted development. 100% of the codebase was created through this innovative approach, showcasing what's possible with structured AI collaboration.

### Contributing

Contributions are welcome. This is an open-source educational project aimed at supporting AI learners worldwide.

## Team

**Development**
- Roman Slack - Full-stack development, architecture, deployment

**Curriculum & Content**
- Roman Slack - Course design and technical content
- Olivier Couthaud - Educational pathways and module content

**Affiliation**
- Developed in partnership with the Rochester Institute of Technology AI Club

## License

This project is open source and available under the MIT License.

## Acknowledgments

Built with Claude Code, this platform represents a commitment to democratizing AI education and providing free, accessible learning resources for students and enthusiasts worldwide.

---

For questions or support, please open an issue on GitHub or contact the RIT AI Club.
