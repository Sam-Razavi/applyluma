# Vercel Frontend Deployment Guide

## Prerequisites
- Vercel account created
- Railway backend deployed and URL copied

## Step 1: Import GitHub Repository
1. Go to vercel.com/dashboard
2. Click "Add New" -> "Project"
3. Import: `Sam-Razavi/applyluma`
4. Framework: Vite
5. Root directory: `/frontend`

## Step 2: Configure Build Settings
Vercel should auto-detect Vite, but verify:

- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

## Step 3: Add Environment Variable
In Vercel project settings -> Environment Variables:

```bash
VITE_API_URL=https://your-railway-backend-url.up.railway.app
VITE_ENVIRONMENT=production
```

Replace `VITE_API_URL` with the actual Railway backend URL from `RAILWAY_SETUP.md` Step 5.

## Step 4: Deploy
1. Click "Deploy"
2. Wait for build to complete, usually about 2 minutes
3. Vercel provides a preview URL, for example `https://applyluma-xxx.vercel.app`

## Step 5: Test Frontend
1. Visit the preview URL
2. Register a new user
3. Check browser console for errors
4. Verify API calls go to the Railway backend URL

## Next: Configure Custom Domain
Proceed to `DNS_SETUP.md` to point `applyluma.com` to Vercel.

