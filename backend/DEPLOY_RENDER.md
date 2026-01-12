# Deploying Attrangi Backend to Render

Follow these steps to deploy **only the backend** to Render.

## Prerequisites
1. Push your latest code to GitHub (which you just did!).
2. Create an account on [Render.com](https://render.com/).

## Step 1: Create a New Web Service
1. On your Render Dashboard, click **New +** -> **Web Service**.
2. Connect your GitHub repository (`bot-heyattrangi-v2`).
3. Select the repository.

## Step 2: Configure the Service
Fill in the following details:

- **Name**: `attrangi-backend` (or similar)
- **Region**: Choose one close to you (e.g., Singapore, Oregon).
- **Branch**: `master`
- **Root Directory**: `backend` (Important: This tells Render to look inside the backend folder).
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`

## Step 3: Environment Variables
Scroll down to the **Environment Variables** section and add the following keys. You can copy the values from your local `backend/.env` file.

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_...` (Your actual Groq API Key) |
| `DATABASE_URL` | `postgresql://...` (Your NeonDB connection string) |
| `PYTHON_VERSION` | `3.11.0` (Optional, but recommended for stability) |

> **Note on Database**: Since you are using NeonDB, simply provide the full connection string as `DATABASE_URL`. Render will connect to it externally.

## Step 4: Deploy
1. Click **Create Web Service**.
2. Render will start building your service. Watch the logs for any errors.
3. Once deployed, you will see a URL ending in `.onrender.com`.

## Step 5: Update Frontend (Later)
Once your backend is live, you will need to update your Frontend's `.env` or configuration to point to this new URL instead of `localhost:8000`.

```env
NEXT_PUBLIC_API_URL=https://attrangi-backend.onrender.com
```
