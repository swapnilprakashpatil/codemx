# 🧪 Testing sql.js Implementation Locally

## Quick Test (3 Steps)

### 1. Build the static version
```powershell
cd frontend
npm run build -- --configuration=static
```

### 2. Serve the built files
```powershell
# Install http-server if you don't have it
npm install -g http-server

# Serve from dist directory
npx http-server dist/frontend -p 8080 -c-1
```

### 3. Open in browser
Open: `http://localhost:8080`

You should see:
1. **Loading overlay** with progress bar
2. Database download progress (65.7 MB)
3. App loads with all features working!

---

## What to Test

### ✅ Basic Functionality
- [ ] Search for codes (e.g., "diabetes", "J45.0")
- [ ] Autocomplete works
- [ ] Pagination works
- [ ] Code detail pages load
- [ ] View SNOMED → ICD-10-CM mappings
- [ ] View ICD-10-CM → HCC mappings

### ✅ Performance
- [ ] First load: 5-10 seconds (database download)
- [ ] Reload page: <1 second (cached database)
- [ ] Search queries: <200ms
- [ ] No errors in browser console

### ✅ Offline Support
1. Load the app once
2. Stop the http-server
3. Reload the page → Should still work! ✨

---

## Debugging

### Check Database Service
Open browser DevTools (F12) → Console:
```javascript
// Check if database loaded
window.dbService // Should show DatabaseService instance

// Check database stats
window.dbService.getStats().then(console.log)
```

### Check IndexedDB Cache
DevTools → Application → IndexedDB → `CodingManagerDB`
- Should see `coding_database` entry (~287 MB)

### Force Re-download
```javascript
// Clear cache and reload
window.dbService.clearCache().then(() => location.reload())
```

---

## Compare Modes

### Mode 1: Backend API (Normal Dev)
```powershell
# Terminal 1
cd backend
python -m api.app

# Terminal 2
cd frontend
npm start
```
→ Uses backend at `http://localhost:5000/api`

### Mode 2: sql.js (Static/Production)
```powershell
cd frontend
npm run build -- --configuration=static
npx http-server dist/frontend -p 8080
```
→ Uses browser database (no backend needed)

### Mode 3: JSON Static (Fallback)
Not implemented yet - future option if sql.js has issues

---

## Performance Comparison

| Metric | Backend API | sql.js |
|--------|-------------|---------|
| **Initial Load** | Instant | 5-10s (first time) |
| **Subsequent Loads** | Instant | <1s (cached) |
| **Search Query** | 50-100ms | 50-200ms |
| **Hosting Cost** | $5-50/month | $0 (GitHub Pages) |
| **Scalability** | Limited | Infinite (CDN) |
| **Offline** | ❌ | ✅ |

---

## Common Issues

### 1. Database Not Found
**Error**: `Failed to download database: 404`

**Fix**:
```powershell
# Generate the database
cd backend
python -m pipeline.export_sqlite_browser --compress
```

### 2. Module Not Found: sql.js
**Error**: `Cannot find module 'sql.js'`

**Fix**:
```powershell
cd frontend
npm install
```

### 3. WASM File Not Found
**Error**: `Could not locate sql-wasm.wasm`

**Fix**: Check `angular.json` has sql.js assets configured:
```json
{
  "glob": "**/*",
  "input": "node_modules/sql.js/dist",
  "output": "assets/sql.js"
}
```

### 4. Database Too Large
**Issue**: 65MB download is slow on mobile

**Options**:
- Split by code type (future enhancement)
- Use differential updates
- Compress more aggressively
- Show option to use backend API instead

---

## Production Checklist

Before deploying to GitHub Pages:

- [ ] Database exported: `backend/pipeline/export_sqlite_browser.py`
- [ ] Build works: `npm run build -- --configuration=static`
- [ ] No errors in browser console
- [ ] Search functionality tested
- [ ] Mappings display correctly
- [ ] Loading states work (progress bar)
- [ ] Error handling works (retry button)
- [ ] Database cached after first load
- [ ] Works offline (after initial load)
- [ ] GitHub Actions workflow configured
- [ ] Repository settings: Pages enabled

---

## Next Steps

1. **Test locally** (this guide)
2. **Commit all changes**:
   ```bash
   git add -A
   git commit -m "feat: add sql.js support for GitHub Pages deployment"
   git push
   ```
3. **Enable GitHub Pages**:
   - Go to Settings → Pages
   - Source: GitHub Actions
4. **Watch deployment**: Actions tab
5. **Access app**: `https://username.github.io/CodingManager/`

---

## Bonus: Service Worker (Future Enhancement)

For true offline-first experience:

```typescript
// frontend/src/sw.ts
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('coding-db-v1').then((cache) => {
      return cache.addAll([
        '/data/coding_database.sqlite',
        '/assets/sql.js/sql-wasm.wasm',
      ]);
    })
  );
});
```

This would enable:
- ✅ Instant startup (no download wait)
- ✅ Background updates
- ✅ True offline mode
- ✅ Push notifications for data updates

---

Happy testing! 🚀

If everything works, you're ready to deploy to GitHub Pages! 🎉
