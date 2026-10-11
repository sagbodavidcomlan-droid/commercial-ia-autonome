# System Architecture

## Overview

This is a full-stack SaaS application with a React frontend, FastAPI backend, PostgreSQL database, and LangGraph AI agent integration.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    http://localhost:3000                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/HTTPS
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      React Frontend                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Components:                                              │  │
│  │  • Landing Page        • Dashboard                        │  │
│  │  • Login/Register      • New Project Form                 │  │
│  │  • Project Detail      • Protected Routes                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Services:                                                │  │
│  │  • API Client (Axios)  • Auth Utils                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ REST API (JSON)
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend                              │
│                   http://localhost:8000                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Endpoints:                                           │  │
│  │  • POST /api/auth/register                                │  │
│  │  • POST /api/auth/login                                   │  │
│  │  • GET  /api/projects                                     │  │
│  │  • POST /api/projects     (triggers AI generation)        │  │
│  │  • GET  /api/projects/{id}                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Authentication:                                          │  │
│  │  • JWT Token Generation                                   │  │
│  │  • Password Hashing (bcrypt)                              │  │
│  │  • Protected Route Middleware                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Database Layer (SQLAlchemy):                             │  │
│  │  • User Model                                             │  │
│  │  • Project Model                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────┬────────────────────────────┬─────────────────────┘
              │                            │
              │ SQL Queries                │ API Calls
              │                            │
┌─────────────▼───────────┐   ┌────────────▼──────────────────────┐
│   PostgreSQL Database   │   │   LangGraph Marketing Agent       │
│   ┌─────────────────┐   │   │   ┌───────────────────────────┐   │
│   │  users table    │   │   │   │  State Graph:             │   │
│   │  • id           │   │   │   │  1. Research Audience     │   │
│   │  • email        │   │   │   │  2. Analyze Competitors   │   │
│   │  • password     │   │   │   │  3. Generate Facebook     │   │
│   │  • full_name    │   │   │   │  4. Generate Instagram    │   │
│   └─────────────────┘   │   │   │  5. Generate TikTok       │   │
│   ┌─────────────────┐   │   │   │  6. Generate YouTube      │   │
│   │ projects table  │   │   │   │  7. Generate Google Ads   │   │
│   │  • id           │   │   │   │  8. Generate Image Prompt │   │
│   │  • user_id (FK) │   │   │   └───────────────────────────┘   │
│   │  • product_name │   │   │                                    │
│   │  • description  │   │   │   Uses: Claude 3.5 Haiku          │
│   │  • content JSON │   │   └────────────┬───────────────────────┘
│   └─────────────────┘   │                │
└─────────────────────────┘                │
                                           │
                              ┌────────────▼──────────────┐
                              │   Anthropic Claude API    │
                              │   (External Service)      │
                              └───────────────────────────┘
```

## Data Flow

### 1. User Registration/Login
```
User → Frontend → POST /api/auth/register → Backend
                                           ↓
                                    Hash Password
                                           ↓
                                    Save to Database
                                           ↓
                                    Return JWT Token
                                           ↓
Frontend ← Store Token in localStorage ← Backend
```

### 2. Creating a Project (AI Content Generation)
```
User fills form → Frontend → POST /api/projects → Backend
                                                    ↓
                                          Validate Auth (JWT)
                                                    ↓
                                          Initialize LangGraph Agent
                                                    ↓
                                          Execute State Graph:
                                          ┌──────────────────┐
                                          │ Research         │
                                          │ Audience         │
                                          └────────┬─────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │ Analyze          │
                                          │ Competitors      │
                                          └────────┬─────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │ Generate Content │
                                          │ for All Platforms│
                                          └────────┬─────────┘
                                                   │
                                          Save to Database
                                                   ↓
                    Frontend ← Return Project with Content ← Backend
                       ↓
                  Display Results
```

### 3. Viewing Projects
```
User → Frontend → GET /api/projects → Backend
                                        ↓
                                  Validate Auth
                                        ↓
                                  Query Database
                                        ↓
                   Frontend ← Return Projects ← Backend
                       ↓
                  Display Dashboard
```

## Technology Stack Details

### Frontend Stack
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first CSS
- **Axios** - HTTP client

### Backend Stack
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migration tool
- **Pydantic** - Data validation
- **python-jose** - JWT token handling
- **passlib** - Password hashing

### AI Stack
- **LangGraph** - Stateful AI agent framework
- **LangChain** - LLM application framework
- **Claude 3.5 Haiku** - Fast, cost-effective LLM
- **Anthropic API** - Claude API provider

### Database
- **PostgreSQL 15** - Relational database
- **JSON columns** - For flexible content storage

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

## Security Features

### Authentication
- JWT tokens for stateless auth
- Bcrypt password hashing
- HTTP Bearer token authentication
- Token expiration (30 minutes default)

### API Security
- CORS configuration
- Input validation with Pydantic
- SQL injection prevention (SQLAlchemy ORM)
- Environment variable secrets

### Database Security
- Password hashing (never store plain text)
- Foreign key constraints
- User-specific data isolation

## Scalability Considerations

### Current Setup (Development)
- Single container per service
- Development mode with hot reload
- SQLite-compatible (PostgreSQL in use)

### Production Recommendations
1. **Database:** Use managed PostgreSQL (AWS RDS, Supabase)
2. **Backend:** Deploy to container platform (Railway, Render, AWS ECS)
3. **Frontend:** Use CDN (Vercel, Netlify, Cloudflare)
4. **Caching:** Add Redis for sessions and rate limiting
5. **Queue:** Add Celery/Redis for async AI generation
6. **Monitoring:** Add Sentry, DataDog, or New Relic

## API Request Flow Example

### Creating a New Marketing Project

```
1. User fills form on frontend
   ↓
2. Frontend sends request:
   POST http://localhost:8000/api/projects
   Headers: { Authorization: "Bearer eyJ0eXAi..." }
   Body: {
     "product_name": "Smart Water Bottle",
     "product_description": "...",
     "target_audience": "...",
     "unique_selling_points": ["...", "..."]
   }
   ↓
3. Backend receives request
   ↓
4. Verify JWT token (get_current_user dependency)
   ↓
5. Initialize MarketingAgentService
   ↓
6. Execute LangGraph workflow (1-2 minutes):
   - Call Claude API 8 times (once per node)
   - Each node returns partial state
   - State accumulates through graph
   ↓
7. Combine all generated content
   ↓
8. Save to database:
   {
     "product_info": {...},
     "research": {
       "audience_insights": "...",
       "competitor_analysis": "..."
     },
     "content": {
       "facebook": "...",
       "instagram": "...",
       "tiktok": "...",
       "youtube": "...",
       "google_ads": "..."
     },
     "creative": {
       "image_prompt": "..."
     }
   }
   ↓
9. Return project with ID
   ↓
10. Frontend navigates to /projects/{id}
    ↓
11. Display content with download buttons
```

## File Organization

```
Monorepo Structure:
├── backend/          # Python FastAPI application
├── frontend/         # React application
├── docker-compose.yml
└── README.md

Backend Structure:
backend/
├── app/
│   ├── api/          # API routes
│   ├── core/         # Config, database, security
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   └── services/     # Business logic (AI agent)
└── alembic/          # Database migrations

Frontend Structure:
frontend/
└── src/
    ├── components/   # Reusable UI components
    ├── pages/        # Route pages
    ├── services/     # API client
    └── utils/        # Helper functions
```

## Performance Metrics

**Expected Performance:**
- Registration/Login: < 500ms
- List Projects: < 200ms
- View Project: < 300ms
- **Generate Content: 60-120 seconds** (8 AI calls)

**Database Queries:**
- User lookup: 1 query
- List projects: 1 query
- Create project: 2 queries (insert + return)

**API Calls (per project generation):**
- 8 calls to Claude API
- ~30 tokens per response (varies by prompt)
- Total cost: ~$0.01-0.02 per project (with Haiku)

## Future Enhancements

1. **Async Processing:** Move AI generation to background jobs
2. **Webhooks:** Notify users when generation is complete
3. **Templates:** Allow users to save prompt templates
4. **Teams:** Multi-user collaboration
5. **Export:** PDF/Word document exports
6. **Analytics:** Track content performance
7. **A/B Testing:** Compare different content versions
8. **Scheduling:** Schedule content posting
9. **API Access:** Allow programmatic access
10. **White-label:** Custom branding options
