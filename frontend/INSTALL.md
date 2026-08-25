# WATHBA authentication update

Run these commands in PowerShell from `D:\Projects\WATHBA_PHASE2\frontend`.

```powershell
Copy-Item .\app\page.tsx .\app\page.before-auth.tsx
Copy-Item .\app\layout.tsx .\app\layout.before-auth.tsx
Expand-Archive -Path "$env:USERPROFILE\Downloads\WATHBA_AUTH_UPDATE_READY.zip" -DestinationPath . -Force
npm.cmd install @supabase/supabase-js
npm.cmd run build
npm.cmd run dev
```

Ensure `.env.local` contains:

```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Then open `http://localhost:3000`.

## Expected result

- Existing approved coach: signs in and opens Coach Command Center.
- New user: chooses Coach or Athlete, creates an account, confirms email, then sees Pending approval.
- No dashboard switch appears. The approved database role controls the dashboard.
- Sign out ends the Supabase session.

## Supabase URL configuration

In Supabase: Authentication > URL Configuration:

- Site URL: `http://localhost:3000`
- Redirect URLs: add `http://localhost:3000/**`

Add the Vercel production URL later as another redirect URL.
