# Marketing Content Generator SaaS

A production-ready SaaS application that generates AI-powered marketing content for multiple platforms using LangGraph and Claude AI.

## Features

### Backend (FastAPI)
- User authentication with JWT tokens
- PostgreSQL database with Users and Projects tables
- RESTful API endpoints
- Integration with LangGraph marketing agent
- Docker support

### Frontend (React + Vite)
- Modern, responsive UI with Tailwind CSS
- User authentication (Login/Register)
- Dashboard for managing projects
- Project creation form
- Project detail view with platform-specific content tabs
- Download functionality for each platform's content

### AI Marketing Agent
Generates optimized content for:
- 📘 Facebook (longer posts with engagement)
- 📸 Instagram (visual-focused captions with hashtags)
- 🎵 TikTok (short video scripts with trending elements)
- 🎬 YouTube (SEO-optimized descriptions)
- 🔍 Google Ads (multiple ad variations)
- 🎨 Image Generation Prompts

Plus audience insights and competitor analysis!

## Tech Stack

**Backend:**
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic (migrations)
- LangGraph + LangChain
- Claude 3.5 Haiku (Anthropic)

**Frontend:**
- React 18
- Vite
- React Router
- Tailwind CSS
- Axios

**Infrastructure:**
- Docker & Docker Compose
- PostgreSQL 15

## Prerequisites

- Docker and Docker Compose installed
- Anthropic API key ([Get one here](https://console.anthropic.com/))

## Quick Start

### 1. Clone and Setup Environment

```bash
# Copy environment variables
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Update the `.env` file:
```env
# Generate with: openssl rand -hex 32
SECRET_KEY=your-secret-key-here

# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 2. Start the Application

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

This will start:
- **PostgreSQL** on `localhost:5432`
- **Backend API** on `http://localhost:8000`
- **Frontend** on `http://localhost:3000`

### 3. Access the Application

Open your browser and navigate to:
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **API:** http://localhost:8000

### 4. Create an Account

1. Click "Sign Up" on the homepage
2. Fill in your details and create an account
3. You'll be automatically logged in and redirected to the dashboard

### 5. Create Your First Project

1. Click "New Project" on the dashboard
2. Fill in:
   - Product Name
   - Product Description
   - Target Audience
   - Unique Selling Points (add multiple)
3. Click "Generate Content"
4. Wait 1-2 minutes while AI generates content for all platforms
5. View and download platform-specific content!

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Projects
- `POST /api/projects` - Create new project (generates content)
- `GET /api/projects` - List all user projects
- `GET /api/projects/{id}` - Get specific project
- `DELETE /api/projects/{id}` - Delete project

## Development

### Backend Development

```bash
# Enter backend container
docker-compose exec backend bash

# Create new migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Frontend Development

```bash
# Enter frontend container
docker-compose exec frontend sh

# Install new package
npm install package-name

# Build for production
npm run build
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

## Project Structure

```
first-agent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py          # Auth endpoints
│   │   │   │   └── projects.py      # Project endpoints
│   │   │   └── deps.py              # Dependencies (auth)
│   │   ├── core/
│   │   │   ├── config.py            # Configuration
│   │   │   ├── database.py          # Database setup
│   │   │   └── security.py          # JWT & password hashing
│   │   ├── models/
│   │   │   ├── user.py              # User model
│   │   │   └── project.py           # Project model
│   │   ├── schemas/
│   │   │   ├── user.py              # User schemas
│   │   │   └── project.py           # Project schemas
│   │   ├── services/
│   │   │   └── marketing_agent.py   # LangGraph agent
│   │   └── main.py                  # FastAPI app
│   ├── alembic/                     # Database migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   └── LoadingSpinner.jsx
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── NewProject.jsx
│   │   │   └── ProjectDetail.jsx
│   │   ├── services/
│   │   │   └── api.js               # API client
│   │   ├── utils/
│   │   │   └── auth.js              # Auth utilities
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── docker-compose.yml
├── .env.example
├── .gitignore
├── product_marketing_agent.py       # Original agent (for reference)
└── README.md
```

## Database Schema

### Users Table
```sql
- id (Primary Key)
- email (Unique)
- hashed_password
- full_name
- created_at
```

### Projects Table
```sql
- id (Primary Key)
- user_id (Foreign Key -> users.id)
- product_name
- product_description
- target_audience
- unique_selling_points (JSON Array)
- content (JSON Object)
- created_at
```

## Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/marketing_saas
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=your-anthropic-key
CORS_ORIGINS=http://localhost:3000
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
```

## Troubleshooting

### Database Connection Issues
```bash
# Check if database is running
docker-compose ps db

# Restart database
docker-compose restart db

# View database logs
docker-compose logs db
```

### Backend Issues
```bash
# Restart backend
docker-compose restart backend

# Check migrations
docker-compose exec backend alembic current

# Run migrations manually
docker-compose exec backend alembic upgrade head
```

### Frontend Issues
```bash
# Restart frontend
docker-compose restart frontend

# Clear node_modules and reinstall
docker-compose down
rm -rf frontend/node_modules
docker-compose up --build
```

### API Key Issues
- Make sure your `ANTHROPIC_API_KEY` is valid
- Check you have sufficient credits in your Anthropic account
- Verify the key is correctly set in `.env` file

## Production Deployment

### Security Checklist
- [ ] Generate strong `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Set strong database password
- [ ] Enable HTTPS
- [ ] Set appropriate CORS origins
- [ ] Use environment-specific API keys
- [ ] Enable database backups
- [ ] Set up monitoring and logging

### Recommended Hosting
- **Backend:** Railway, Render, AWS ECS
- **Frontend:** Vercel, Netlify, Cloudflare Pages
- **Database:** AWS RDS, Supabase, Railway

## License

MIT

## Support

For issues and questions, please create an issue in the repository.

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Claude AI](https://www.anthropic.com/)
- [Tailwind CSS](https://tailwindcss.com/)
