# Step-by-Step Deployment Guide: Split Architecture (Vercel + Railway)

Because StockAI v2.0 requires background tasks, persistent storage (SQLite), and long-running WebSockets for the simulation engine, it **cannot** be deployed entirely on Vercel's free serverless tier. 

Instead, we use a **Split Architecture**:
1. **Frontend (Vercel)**: Fast, global CDN delivery for your HTML, CSS, and JS files.
2. **Backend (Railway)**: A dedicated container to run the Python FastAPI server, simulation loops, and database.

Follow this guide exactly, step-by-step, to get your project live.

---

## Phase 1: Push Your Code to GitHub
Before deploying anything, your code needs to be in a GitHub repository.
1. Go to [GitHub.com](https://github.com/) and log in.
2. Click the **+** icon in the top right and select **New repository**.
3. Name it `StockAI-ver2.0` (or whatever you prefer) and keep it Public or Private.
4. If you haven't pushed your code yet, open your terminal (VS Code Terminal) and run:
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```
*(Note: If your code is already pushed, skip to Phase 2).*

---

## Phase 2: Deploy the Backend (Railway)
We deploy the backend first so we can get its live URL, which the frontend will need.

1. **Sign up / Log in to Railway:**
   - Go to [railway.app](https://railway.app/) in your browser.
   - Click **Login** in the top right.
   - Select **Log in with GitHub** and authorize Railway.

2. **Create a New Project:**
   - From your Railway Dashboard, click the **+ New Project** button.
   - Select **Deploy from GitHub repo**.
   - If prompted, click **Configure GitHub App** to give Railway access to your `StockAI-ver2.0` repository.
   - Select the `StockAI-ver2.0` repository from the list.
   - Click **Deploy Now**.

3. **Configure the Start Command:**
   - Railway will start building your project, but it might not know how to start the Python server.
   - Click on your new deployment block in the Railway canvas.
   - Go to the **Settings** tab.
   - Scroll down to the **Deploy** section.
   - Find **Start Command** and type: `python backend/run.py`
   - Hit **Enter** to save.

4. **Add Environment Variables (API Keys):**
   - In that same Railway menu, switch to the **Variables** tab.
   - Click **+ New Variable**.
   - Add your keys here (e.g., `GROQ_API_KEY`, `OPENAI_API_KEY`). You can find these in your local `.env` file.
   - *(Note: The app will still run in "mock mode" if you skip this).*

5. **Generate a Public Domain:**
   - Go to the **Settings** tab again.
   - Scroll down to the **Networking** section.
   - Click **Generate Domain**.
   - Railway will give you a URL like `stockai-production.up.railway.app`.
   - **Copy this URL.** You will need it for Vercel!

---

## Phase 3: Connect Frontend to Backend
Now that your backend is live on Railway, we need to tell Vercel to proxy all API requests to it.

1. Open your code in VS Code.
2. Open the file named `vercel.json` in the root folder.
3. Update the `"destination"` URLs in the `"rewrites"` or `"routes"` section to point to your new Railway URL. 
   
   *Example `vercel.json`:*
   ```json
   {
     "version": 2,
     "rewrites": [
       { 
         "source": "/api/(.*)", 
         "destination": "https://YOUR-RAILWAY-URL.up.railway.app/api/$1" 
       },
       { 
         "source": "/simulation/(.*)", 
         "destination": "https://YOUR-RAILWAY-URL.up.railway.app/simulation/$1" 
       },
       { 
         "source": "/data/(.*)", 
         "destination": "https://YOUR-RAILWAY-URL.up.railway.app/data/$1" 
       },
       { 
         "source": "/live-market/(.*)", 
         "destination": "https://YOUR-RAILWAY-URL.up.railway.app/live-market/$1" 
       }
     ]
   }
   ```
4. Save the file, commit, and push it to GitHub:
   ```bash
   git add vercel.json
   git commit -m "Update vercel.json with Railway backend URL"
   git push origin main
   ```

---

## Phase 4: Deploy the Frontend (Vercel)

1. **Sign up / Log in to Vercel:**
   - Go to [vercel.com](https://vercel.com/) in your browser.
   - Click **Sign Up** or **Log In**.
   - Choose **Continue with GitHub** and authorize Vercel.

2. **Import Your Project:**
   - From your Vercel Dashboard, click **Add New...** and select **Project**.
   - Find your `StockAI-ver2.0` repository in the list and click **Import**.

3. **Configure the Project:**
   - **Project Name:** `stock-ai` (or leave default).
   - **Framework Preset:** Leave it as **Other**.
   - **Root Directory:** Leave it as `./`.
   - **Build and Output Settings:** Leave exactly as they are (Vercel will detect the static HTML files automatically).
   - **Environment Variables:** You do *not* need to add API keys here. The backend handles all API keys!

4. **Deploy:**
   - Click the big **Deploy** button.
   - Wait 1–2 minutes while Vercel builds and assigns a domain (e.g., `stockai.vercel.app`).
   - Click **Continue to Dashboard** and copy your new Vercel Domain.

---

## Phase 5: Fix CORS (Final Step)
Right now, your frontend is on Vercel, and your backend is on Railway. Browsers block communication between different domains for security (CORS). We need to whitelist your Vercel domain in the backend.

1. Go back to VS Code.
2. Open `backend/app/main.py`.
3. Find the `CORSMiddleware` section (around line 30).
4. Add your new Vercel domain to the `allow_origins` list:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "http://localhost:8000",
           "https://YOUR-VERCEL-DOMAIN.vercel.app"  # <-- ADD YOUR EXACT VERCEL URL HERE
       ],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
5. Save the file, commit, and push to GitHub:
   ```bash
   git add backend/app/main.py
   git commit -m "Update CORS with Vercel frontend domain"
   git push origin main
   ```
6. **Wait for Railway to redeploy.** Railway automatically detects the push and deploys the update.

---

## 🎉 You're Done!
Go to your Vercel URL (e.g., `https://stockai.vercel.app`). 
- The HTML, CSS, and UI load instantly from Vercel.
- When you click "Launch Simulation", Vercel silently routes that request to your Railway backend, which executes the heavy Python code and returns the results. 

Your application is now live on the internet using a production-ready split architecture!
