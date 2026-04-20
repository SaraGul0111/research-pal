# ResearchPal — Complete Free Deployment Guide
# =============================================
# Goal: Anyone on the internet can use your app
#       Your laptop can be OFF
#       Zero cost for you
# Platform: Railway.app (free tier)
# =============================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERVIEW — What is happening
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Right now your app only runs when you type "uvicorn app:app..."
and only YOU can access it at localhost:8000.

After this guide:
- Your code lives on GitHub (free)
- Railway runs it on their servers 24/7 (free tier)
- Anyone gets a link like: https://researchpal-production.up.railway.app
- Your laptop can be completely off

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — Create a GitHub Account (if you don't have one)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to https://github.com
2. Click "Sign up"
3. Enter email, password, username
4. Verify your email
5. Done — you have a GitHub account

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — Install Git on your PC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to https://git-scm.com/download/win
2. Download and install (click Next through everything)
3. Open a NEW terminal after installing
4. Verify: type   git --version
   Should show: git version 2.x.x

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — Prepare your project folder
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your research-pal folder must have EXACTLY these files:

  research-pal/
  ├── app.py
  ├── requirements.txt
  ├── Procfile              ← tells Railway how to start your app
  ├── .gitignore            ← keeps .env and uploads off GitHub
  ├── .env                  ← your API key (NEVER goes to GitHub)
  └── static/
      └── index.html

Check your Procfile contains exactly this one line:
  web: uvicorn app:app --host 0.0.0.0 --port $PORT

Check your requirements.txt has these packages:
  fastapi==0.115.5
  uvicorn[standard]==0.32.1
  python-multipart==0.0.12
  python-dotenv==1.0.1
  langchain==0.3.9
  langchain-community==0.3.9
  langchain-core==0.3.21
  langchain-text-splitters==0.3.2
  faiss-cpu==1.9.0
  sentence-transformers==3.3.1
  pypdf==5.1.0
  pydantic==2.10.3
  httpx==0.28.0
  google-genai>=1.0.0

Check your .gitignore contains:
  .env
  uploads/
  __pycache__/
  *.pyc
  .venv/
  venv/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — Create a GitHub Repository
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to https://github.com → click the "+" icon top right
2. Click "New repository"
3. Repository name: research-pal
4. Set to: Public  (Railway free tier needs public repos)
5. DO NOT check "Add README" or anything else
6. Click "Create repository"
7. You will see a page with setup instructions — keep it open

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — Push your code to GitHub
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Open your terminal, navigate to your project folder:

  cd D:\Study\Agentic\research-pal

Run these commands ONE BY ONE:

  git init
  git add .
  git commit -m "Initial ResearchPal deployment"
  git branch -M main
  git remote add origin https://github.com/YOUR_USERNAME/research-pal.git
  git push -u origin main

⚠️  REPLACE "YOUR_USERNAME" with your actual GitHub username

When you run git push, it will ask for:
  Username: your GitHub username
  Password: NOT your GitHub password — use a Personal Access Token

To get a Personal Access Token:
  1. GitHub → click your profile picture → Settings
  2. Scroll down → click "Developer settings" (bottom left)
  3. Click "Personal access tokens" → "Tokens (classic)"
  4. Click "Generate new token (classic)"
  5. Note: "ResearchPal deploy"
  6. Expiration: 90 days
  7. Check the box: "repo" (gives full repo access)
  8. Click "Generate token"
  9. COPY the token immediately (you won't see it again)
  10. Paste it as your password when git push asks

After push succeeds:
  Go to https://github.com/YOUR_USERNAME/research-pal
  You should see all your files there
  ⚠️  Confirm .env is NOT there (it should be invisible due to .gitignore)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — Create Railway Account
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Go to https://railway.app
2. Click "Login" → "Login with GitHub"
3. Authorize Railway to access your GitHub
4. You are now logged into Railway

Railway Free Tier gives you:
  - $5 of compute credit per month
  - This runs a small FastAPI app for ~500 hours/month
  - More than enough for personal use
  - No credit card required

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — Deploy on Railway
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. On Railway dashboard → click "New Project"
2. Click "Deploy from GitHub repo"
3. Click "Configure GitHub App" if asked → allow access to your repos
4. Select "research-pal" from the list
5. Click "Deploy Now"

Railway will now:
  - Clone your GitHub repo
  - Detect it's a Python app
  - Install packages from requirements.txt
  - Start with the Procfile command
  - This takes 3-5 minutes first time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8 — Add your Gemini API Key to Railway
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the most important step.
Your .env file is NOT on GitHub (we kept it secret).
You need to add the key directly in Railway's dashboard.

1. Click on your "research-pal" service in Railway
2. Click the "Variables" tab
3. Click "New Variable"
4. Add this:
   Variable name:  GEMINI_API_KEY
   Value:          AIzaSy...your actual key...

5. Click "Add"
6. Railway will automatically restart your app with the key

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 9 — Get your public URL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Click on your service → click "Settings" tab
2. Scroll to "Networking" section
3. Click "Generate Domain"
4. Railway gives you a URL like:
   https://research-pal-production.up.railway.app

5. Click that URL — your app is LIVE on the internet!
6. Share this link with anyone — they can use it without you doing anything

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 10 — Watch your deployment logs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In Railway → click "Deployments" tab → click the latest deployment
You will see live build logs. Look for:

  ✓ Installing packages...        (pip install running)
  ✓ Application startup complete  (your app started)
  ✓ Uvicorn running on 0.0.0.0   (ready for traffic)

If you see errors, look for the red text and fix accordingly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO UPDATE YOUR APP (after making changes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every time you change any file, just run:

  git add .
  git commit -m "describe what you changed"
  git push origin main

Railway detects the push AUTOMATICALLY and redeploys.
New version is live in about 2 minutes.
Zero manual work on Railway's side.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING COMMON ISSUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ App starts but shows error on upload
→ Check GEMINI_API_KEY is set in Railway Variables tab
→ Go to your-app-url/health to see if key is configured

❌ Build fails with "ModuleNotFoundError"
→ That package is missing from requirements.txt
→ Add it, commit, push → Railway rebuilds automatically

❌ "Application failed to start" in logs
→ Click the failed deployment → read the full error log
→ Usually a syntax error in app.py or missing file

❌ App works but is slow on first upload
→ Normal! First upload downloads the embedding model (~90MB)
→ Railway caches it after first run — subsequent uploads are fast

❌ Railway says "Usage limit reached"
→ You've used your $5 free credit
→ Options: add a credit card (pay only for actual usage, ~$0.50/month)
→ Or use Render.com free tier instead (see below)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALTERNATIVE: Render.com (also free, no credit card ever)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If Railway's free credit runs out:

1. Go to https://render.com → Sign up with GitHub
2. Click "New" → "Web Service"
3. Connect your research-pal GitHub repo
4. Settings:
   Build Command:  pip install -r requirements.txt
   Start Command:  uvicorn app:app --host 0.0.0.0 --port $PORT
5. Environment Variables → Add GEMINI_API_KEY
6. Click "Create Web Service"

Render free tier: 750 hours/month, sleeps after 15min inactivity
(first request after sleep takes ~30 seconds to wake up)
Railway free tier: always on, better performance

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT EACH PLATFORM DOES (concept explanation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GitHub: stores your code files safely in the cloud
        think of it as Google Drive but for code
        version controlled — every change is tracked

Railway: reads your code from GitHub
         runs it on their Linux servers
         gives it a public URL
         handles HTTPS, routing, uptime automatically
         you never touch a server — Railway manages everything

Procfile: one instruction file that tells Railway
          "to start my app, run this command"
          web: uvicorn app:app --host 0.0.0.0 --port $PORT
          $PORT is auto-assigned by Railway

Environment Variables: secrets (like API keys) stored
          on the server directly — never in your code files
          this is the professional way to handle secrets

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK COMMAND REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

First time setup:
  git init
  git add .
  git commit -m "first commit"
  git branch -M main
  git remote add origin https://github.com/USERNAME/research-pal.git
  git push -u origin main

Every update after that:
  git add .
  git commit -m "what I changed"
  git push origin main

Check app health after deploy:
  https://your-app.up.railway.app/health

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COST BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GitHub:           FREE forever
Railway:          FREE ($5 credit/month, ~500 hours)
Gemini API:       FREE (1500 requests/day free tier)
Embeddings model: FREE (runs on Railway's server CPU)
FAISS vector DB:  FREE (in-memory, no external service)
Domain/HTTPS:     FREE (Railway provides *.railway.app)

TOTAL MONTHLY COST: $0
