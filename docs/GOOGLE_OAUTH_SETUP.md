# Google OAuth Setup Guide

This guide will help you configure Google OAuth for the AI Bootcamp authentication system.

## Prerequisites

- Google Cloud Platform (GCP) account
- Access to Google Cloud Console

---

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click **"New Project"**
4. Enter project name (e.g., "AI Bootcamp Auth")
5. Click **"Create"**

---

## Step 2: Enable Google+ API

1. In your GCP project, go to **APIs & Services** > **Library**
2. Search for **"Google+ API"**
3. Click on it and press **"Enable"**

---

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **"External"** user type (unless you have Google Workspace)
3. Click **"Create"**
4. Fill in the required information:
   - **App name:** AI Bootcamp
   - **User support email:** Your email
   - **Developer contact email:** Your email
5. Click **"Save and Continue"**
6. **Scopes:** Click **"Add or Remove Scopes"**
   - Add these scopes:
     - `openid`
     - `email`
     - `profile`
   - Click **"Update"** then **"Save and Continue"**
7. **Test users:** Add your email for testing
8. Click **"Save and Continue"** then **"Back to Dashboard"**

---

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **"Create Credentials"** > **"OAuth client ID"**
3. Select **"Web application"**
4. Configure:
   - **Name:** AI Bootcamp Web Client
   - **Authorized JavaScript origins:**
     - `http://localhost:3001` (for local frontend)
     - `http://localhost:8000` (for local backend)
     - Add your production URLs when deploying
   - **Authorized redirect URIs:**
     - `http://localhost:8000/api/v1/auth/google/callback`
     - Add your production callback URL when deploying (e.g., `https://your-api.com/api/v1/auth/google/callback`)
5. Click **"Create"**
6. **Save your credentials:**
   - Copy the **Client ID** (ends with `.apps.googleusercontent.com`)
   - Copy the **Client Secret**

---

## Step 5: Update Backend Environment Variables

1. Open `aibc_auth/.env`
2. Update the following variables with your credentials:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
SESSION_SECRET_KEY=your-random-secret-key-here
```

3. Generate a secure session secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Step 6: Install Dependencies

1. Navigate to the backend directory:
```bash
cd aibc_auth
```

2. Install new OAuth dependencies:
```bash
pip install authlib==1.3.0 itsdangerous==2.1.2
```

Or rebuild the Docker container:
```bash
docker-compose build auth_service
```

---

## Step 7: Restart Services

1. Restart the backend to load new environment variables:
```bash
docker-compose restart auth_service
```

2. Verify the service is running:
```bash
curl http://localhost:8000/health
```

---

## Step 8: Test the OAuth Flow

1. Start your frontend (if not already running):
```bash
cd ../ai_bootcamp_frontend
npm run dev
```

2. Visit `http://localhost:3001/landing`

3. Click **"Sign in with Google"** or **"Sign up with Google"**

4. You should be redirected to Google's consent screen

5. After approving, you'll be redirected back and logged in

---

## Production Deployment

When deploying to production, update these settings:

### 1. Update Google Cloud Console

Go back to **APIs & Services** > **Credentials** > Your OAuth Client

Add production URLs to:
- **Authorized JavaScript origins:**
  - `https://your-frontend-domain.com`
  - `https://your-backend-domain.com`
- **Authorized redirect URIs:**
  - `https://your-backend-domain.com/api/v1/auth/google/callback`

### 2. Update Environment Variables

Production `.env`:
```env
GOOGLE_CLIENT_ID=your-production-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-production-client-secret
GOOGLE_REDIRECT_URI=https://your-backend-domain.com/api/v1/auth/google/callback
SESSION_SECRET_KEY=your-production-secret-key
CORS_ORIGINS=https://your-frontend-domain.com
```

### 3. Enable HTTPS

Update `aibc_auth/app/main.py`:
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    max_age=3600,
    https_only=True  # Change to True in production
)
```

---

## Troubleshooting

### Error: "OAuth is not configured"
- Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`
- Restart the backend service after updating `.env`

### Error: "redirect_uri_mismatch"
- Ensure the redirect URI in Google Console exactly matches `GOOGLE_REDIRECT_URI` in `.env`
- Check for trailing slashes (they must match exactly)

### Error: "Access blocked: This app's request is invalid"
- Make sure you've enabled Google+ API in your GCP project
- Check that the OAuth consent screen is configured

### User not redirected after login
- Check that `CORS_ORIGINS` in backend `.env` includes your frontend URL
- Verify the callback page exists at `/app/auth/callback/page.tsx`

### Database errors after implementation
- The database schema was updated to make `password_hash` nullable
- If using existing database, run:
```sql
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
```

---

## Security Best Practices

1. **Never commit credentials** - Keep `.env` in `.gitignore`
2. **Rotate secrets regularly** - Update `SESSION_SECRET_KEY` periodically
3. **Use HTTPS in production** - Never use OAuth over HTTP in production
4. **Verify email domains** - Consider restricting to specific email domains if needed
5. **Monitor OAuth usage** - Check Google Cloud Console for unusual activity

---

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Authlib Documentation](https://docs.authlib.org/)
- [FastAPI Security Guide](https://fastapi.tiangolo.com/tutorial/security/)

---

## Support

If you encounter issues:
1. Check the backend logs: `docker logs aibc_auth`
2. Verify environment variables are loaded correctly
3. Test the OAuth endpoints directly in browser:
   - Visit `http://localhost:8000/api/v1/auth/google/login`
4. Check Google Cloud Console for any API errors or quota limits
