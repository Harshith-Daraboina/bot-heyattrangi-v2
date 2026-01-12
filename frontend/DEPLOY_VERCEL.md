# Deploying Attrangi Frontend to Vercel

Follow these steps to deploy the **frontend** to Vercel and connect it to your Render backend.

## Prerequisites
1. Ensure you have pushed the latest code (including the CORS fix in `backend/app.py`) to GitHub.
2. The backend should be running on Render (copy the URL, e.g., `https://bot-heyattrangi-v2.onrender.com`).

## Step 1: Create a New Project on Vercel
1. Go to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository (`bot-heyattrangi-v2`).

## Step 2: Configure the Project
Vercel should automatically detect that this is a Next.js project.

- **Framework Preset**: Next.js (Default)
- **Root Directory**: Click the **Edit** button and select `frontend`. **(Important)**.

## Step 3: Environment Variables
Expand the **Environment Variables** section and add the following:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://bot-heyattrangi-v2.onrender.com` |

> **Note**: Do not add a trailing slash `/` at the end of the URL.

## Step 4: Deploy
1. Click **Deploy**.
2. Vercel will build your frontend.
3. Once done, you will get a domain (e.g., `bot-heyattrangi-v2.vercel.app`).

## Step 5: Verify
Open your new Vercel app URL. It should load the chat interface and successfully connect to your Render backend.
