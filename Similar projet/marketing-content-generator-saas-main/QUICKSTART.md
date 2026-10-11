# Quick Start Guide

Get your Marketing Content Generator SaaS up and running in 5 minutes!

## Prerequisites

- Docker Desktop installed and running
- Anthropic API key ([Get one free](https://console.anthropic.com/))

## Step-by-Step Setup

### 1️⃣ Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Open the .env file in your editor
nano .env  # or use your preferred editor
```

Add your credentials:
```env
# Generate a secure secret key
SECRET_KEY=paste-result-of-openssl-rand-hex-32-here

# Add your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Generate SECRET_KEY:**
```bash
openssl rand -hex 32
```

### 2️⃣ Start the Application

Using Make (recommended):
```bash
make dev
```

Or using Docker Compose directly:
```bash
docker-compose up --build
```

### 3️⃣ Wait for Services to Start

Watch the logs until you see:
- ✅ Database ready
- ✅ Migrations complete
- ✅ Backend running on port 8000
- ✅ Frontend running on port 3000

This takes about 1-2 minutes on first run.

### 4️⃣ Access the Application

Open your browser:
- **App:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

### 5️⃣ Create Your Account

1. Click **"Sign Up"**
2. Enter your email and password
3. You'll be redirected to the dashboard

### 6️⃣ Generate Your First Content

1. Click **"+ New Project"**
2. Fill in the form:
   - Product Name: "Smart Water Bottle"
   - Description: "A smart bottle that tracks hydration with LED reminders"
   - Target Audience: "Health-conscious professionals aged 25-40"
   - USPs: Add 3-5 unique selling points
3. Click **"Generate Content"**
4. Wait 1-2 minutes for AI to generate content
5. View content for all platforms!

## Useful Commands

```bash
# View all logs
make logs

# View specific service logs
make logs-backend
make logs-frontend
make logs-db

# Restart services
make restart

# Stop everything
make down

# Clean everything and start fresh
make clean
make dev
```

## Troubleshooting

### "Container already in use" error
```bash
make down
make up
```

### "Database connection failed"
```bash
# Check database is running
docker-compose ps db

# Restart database
docker-compose restart db
```

### "Anthropic API error"
- Check your API key is correct in `.env`
- Verify you have credits: https://console.anthropic.com/

### Frontend not loading
```bash
# Clear and rebuild
make clean
make dev
```

## What's Next?

- Create multiple projects
- Download content for each platform
- Customize the prompts in `backend/app/services/marketing_agent.py`
- Add your own branding to the frontend

## Getting Help

- Check the main [README.md](README.md) for detailed documentation
- View API documentation at http://localhost:8000/docs
- Check Docker logs: `make logs`

---

**Estimated Time:** 5 minutes
**Difficulty:** Beginner-friendly
