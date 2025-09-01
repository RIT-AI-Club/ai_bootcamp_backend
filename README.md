# AI Bootcamp

Production-grade full-stack application with authentication microservice and modern React frontend.

## Architecture
- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: FastAPI microservice with PostgreSQL 
- **Auth**: JWT tokens with refresh token rotation
- **Infrastructure**: Docker Compose orchestration

## Quick Start

1. **Start Backend Services**
   ```bash
   docker-compose up
   ```
   This launches PostgreSQL + Auth Service on port 8000

2. **Start Frontend**
   ```bash
   cd ai_bootcamp_frontend
   npm run dev
   ```
   Frontend runs on port 3000

3. **Access Application**
   - Frontend: http://localhost:3000
   - Auth API: http://localhost:8000

## Features
- Secure user authentication with JWT
- Responsive landing page and dashboard
- Production-ready PostgreSQL database
- Rate limiting and security controls
- Elegant UI with modal-based auth flows