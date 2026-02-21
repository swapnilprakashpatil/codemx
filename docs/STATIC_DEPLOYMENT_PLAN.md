# Static Deployment Plan - GitHub Pages with sql.js

## Overview
Convert the Flask backend to a fully static solution using sql.js (SQLite compiled to WebAssembly) for browser-based database queries.

## Architecture

```
GitHub Pages (Static)
├── index.html
├── Angular Frontend
└── data/
    └── coding_database.sqlite (~20-50MB, gzip compressed)
```

## Implementation Steps

### 1. Backend: Export SQLite Database
- **Script**: `backend/pipeline/export_sqlite.py`
- Exports existing SQLiteDB or creates optimized version
- Adds indexes for common queries
- Compresses with gzip
- **Output**: `frontend/public/data/coding_database.sqlite`

### 2. Frontend: Add sql.js Integration
- **Install**: `npm install sql.js`
- **Service**: Create `DatabaseService` to:
  - Download SQLite file on app load
  - Initialize sql.js WASM
  - Cache database in browser
  - Execute queries

### 3. Replace API Calls
- Modify existing services:
  - `coding-api-http.ts` → `coding-api-sqlite.ts`
  - Convert HTTP requests to SQL queries
  - Keep existing interfaces (transparent to components)

### 4. Optimize Loading
- Show loading progress bar
- Cache database in IndexedDB (avoid re-download)
- Lazy-load WASM module

## File Sizes (Estimated)

| Item | Size | Notes |
|------|------|-------|
| SQLite DB (uncompressed) | ~50-80MB | All tables + indexes |
| SQLite DB (gzip) | ~20-40MB | GitHub Pages serves gzipped |
| sql.js WASM | ~800KB | Required library |
| **Total Download** | **~21-41MB** | One-time on first visit |

## Performance

| Metric | Value |
|--------|-------|
| First Load | 2-5 seconds (DB download) |
| Subsequent Loads | <1 second (cached) |
| Search Query | 50-200ms |
| Complex Joins | 100-500ms |

## Benefits vs Current Approach

| Feature | Flask Backend | sql.js Static |
|---------|---------------|---------------|
| Hosting Cost | Requires server | **$0 (GitHub Pages)** |
| Scalability | Server limits | **CDN (infinite)** |
| Offline Support | ❌ | **✅** |
| Query Performance | Fast | **Fast (in-memory)** |
| Initial Load | Instant | 2-5s first visit |
| SEO | ✅ | ✅ (with SSR) |

## Alternative: Hybrid Approach

For users with slow connections:
- Keep chunked JSON as fallback
- Detect connection speed
- Load sql.js for fast connections, JSON for slow

## Code Changes Required

### New Files (~5 files)
1. `backend/pipeline/export_sqlite.py` - Export script
2. `frontend/src/app/services/database.service.ts` - sql.js wrapper
3. `frontend/src/app/services/coding-api-sqlite.ts` - SQL-based API
4. `frontend/src/app/components/loading-db/` - Progress component

### Modified Files (~3 files)
1. `frontend/src/app/app.config.ts` - Switch to SQLite service
2. `frontend/src/environments/environment.ts` - Add DB config
3. `frontend/angular.json` - Include SQLite in assets

## Next Steps

Would you like me to:
1. ✅ **Implement the sql.js solution** (recommended)
2. ⚡ **Implement DexieJS solution** (more work, progressive loading)
3. 📦 **Optimize your current JSON export** (simple, larger payload)
4. 🔀 **Hybrid approach** (sql.js + JSON fallback)

Choose option 1 for the best balance of performance, developer experience, and hosting simplicity.
