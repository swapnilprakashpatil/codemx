# CodeMx Deployment Guide

## GitHub Pages Deployment

This application can be deployed to GitHub Pages using the static mode (browser-based database with sql.js).

### Prerequisites

- GitHub repository: https://github.com/swapnilprakashpatil/codemx
- Compressed database file: `frontend/public/data/coding_database.sqlite.gz` (65.65 MB)

### Deployment Steps

#### 1. Commit and Push Your Code

```bash
# Check status
git status

# Add all files (the .gitignore is configured to allow the compressed database)
git add .

# Commit changes
git commit -m "Deploy to GitHub Pages with static mode"

# Push to main branch
git push origin main
```

#### 2. Enable GitHub Pages

1. Go to your repository: https://github.com/swapnilprakashpatil/codemx
2. Click **Settings** → **Pages** (in left sidebar)
3. Under **Build and deployment**:
   - Source: Select **GitHub Actions**
4. Save the settings

#### 3. Trigger Deployment

The deployment will automatically trigger when you push to the `main` branch. The GitHub Actions workflow (`.github/workflows/deploy-pages.yml`) will:

1. ✅ Checkout code
2. ✅ Install Node.js dependencies
3. ✅ Build Angular app in static mode
4. ✅ Verify compressed database exists
5. ✅ Deploy to GitHub Pages

#### 4. Monitor Deployment

1. Go to **Actions** tab in your repository
2. Watch the "Deploy to GitHub Pages" workflow
3. Wait for ✓ to appear (takes ~2-5 minutes)

#### 5. Access Your Deployed App

Once deployed, your app will be available at:

**https://swapnilprakashpatil.github.io/codemx/**

### What Gets Deployed

- ✅ Angular frontend (optimized production build)
- ✅ Compressed database (65.65 MB) automatically decompresses in browser
- ✅ All medical coding data accessible offline after first load
- ✅ No backend required - 100% static

### File Structure

```
frontend/
├── public/
│   └── data/
│       └── coding_database.sqlite.gz  # 65.65 MB compressed database
├── dist/                              # Generated during build
└── src/
    └── environments/
        └── environment.static.ts      # Static mode configuration
```

### Testing Locally Before Deployment

```bash
# Build for static mode
cd frontend
npm run build -- --configuration=static

# Serve the built files
npx http-server dist/frontend -p 8080

# Open browser
http://localhost:8080
```

### Troubleshooting

#### Database not loading?
- Check browser console (F12) for errors
- Verify database URL: `/codemx/data/coding_database.sqlite.gz`
- Clear browser cache and reload

#### 404 errors?
- Ensure GitHub Pages is enabled with "GitHub Actions" source
- Check that `base-href` in workflow matches repo name: `/codemx/`

#### Deployment failed?
- Go to Actions tab and check error logs
- Ensure database file exists: `frontend/public/data/coding_database.sqlite.gz`
- Verify all dependencies installed: `cd frontend && npm ci`

### Updating the Deployment

```bash
# Make changes to code
# ...

# Rebuild and commit
git add .
git commit -m "Update application"
git push origin main

# GitHub Actions will automatically redeploy
```

### Manual Build Command

If you need to build manually:

```bash
cd frontend
npm run build -- --configuration=static --base-href=/codemx/
```

### Database Updates

If you update the source data:

```bash
# Regenerate backend database
python -m backend.pipeline.process_data

# Export compressed browser database
python -m backend.pipeline.export_sqlite_browser --compress

# Verify
ls -lh frontend/public/data/coding_database.sqlite.gz

# Commit and push
git add frontend/public/data/coding_database.sqlite.gz
git commit -m "Update database"
git push origin main
```

---

## Alternative Deployment Options

### Azure Static Web Apps

For Azure deployment with custom domain and CDN:

1. Create Azure Static Web App
2. Connect to GitHub repository
3. Use build configuration:
   - App location: `/frontend`
   - Api location: `` (leave empty for static mode)
   - Output location: `dist/frontend`
   - Build command: `npm run build -- --configuration=static`

### Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel --prod
```

### Netlify

1. Connect repository to Netlify
2. Build settings:
   - Base directory: `frontend`
   - Build command: `npm run build -- --configuration=static`
   - Publish directory: `dist/frontend`

---

## Production Considerations

✅ **Compression**: Database is gzipped (287 MB → 65.65 MB)
✅ **Caching**: IndexedDB caches database in browser
✅ **Offline**: Works offline after first load
✅ **Performance**: All queries execute in-browser
⚠️ **First Load**: ~65 MB download (1-2 minutes on fast connection)
⚠️ **Browser Storage**: Requires ~350 MB browser storage space

---

**Repository**: https://github.com/swapnilprakashpatil/codemx  
**Technology**: Angular 20 + sql.js + IndexedDB
