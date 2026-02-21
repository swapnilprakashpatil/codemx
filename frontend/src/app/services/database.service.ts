/**
 * Database Service - Browser SQLite via sql.js
 *
 * Manages in-browser SQLite database loaded via sql.js.
 * Downloads and caches the database file, provides query execution,
 * and handles initialization/loading states.
 */

import { Injectable, inject, signal } from '@angular/core';
import initSqlJs, { Database, SqlJsStatic } from 'sql.js';
import { ungzip } from 'pako';
import { environment } from '../../environments/environment';

export interface DatabaseLoadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface QueryResult {
  columns: string[];
  values: any[][];
}

@Injectable({
  providedIn: 'root',
})
export class DatabaseService {
  private db: Database | null = null;
  private SQL: SqlJsStatic | null = null;
  private initializationPromise: Promise<void> | null = null;

  // Signals for reactive state
  public isLoading = signal(false);
  public isReady = signal(false);
  public loadProgress = signal<DatabaseLoadProgress | null>(null);
  public error = signal<string | null>(null);

  constructor() {}

  /**
   * Initialize sql.js and load the database file.
   * Returns a promise that resolves when ready.
   */
  async initialize(): Promise<void> {
    // Return existing initialization if already in progress
    if (this.initializationPromise) {
      return this.initializationPromise;
    }

    // Already initialized
    if (this.isReady()) {
      return Promise.resolve();
    }

    this.initializationPromise = this._initializeInternal();
    return this.initializationPromise;
  }

  private async _initializeInternal(): Promise<void> {
    try {
      this.isLoading.set(true);
      this.error.set(null);
      this.loadProgress.set({ loaded: 0, total: 0, percentage: 0 });

      console.log('🔄 Initializing sql.js...');

      // Step 1: Load sql.js WASM module
      this.SQL = await initSqlJs({
        locateFile: (file: string) => `assets/sql.js/${file}`,
      });

      console.log('✓ sql.js loaded');

      // Step 2: Check if database is cached in IndexedDB
      const cachedDb = await this.getCachedDatabase();

      if (cachedDb) {
        console.log('✓ Using cached database');
        this.db = new this.SQL.Database(cachedDb);
        this.isReady.set(true);
        this.isLoading.set(false);
        return;
      }

      // Step 3: Download database file
      console.log('🔄 Downloading database...');
      const dbData = await this.downloadDatabase(environment.sqlJsDatabaseUrl);

      console.log('✓ Database downloaded');

      // Step 4: Initialize database
      this.db = new this.SQL.Database(dbData);

      // Step 5: Cache database in IndexedDB
      await this.cacheDatabase(dbData);

      console.log('✓ Database initialized and cached');

      this.isReady.set(true);
      this.isLoading.set(false);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to initialize database';
      console.error('❌ Database initialization error:', err);
      this.error.set(errorMsg);
      this.isLoading.set(false);
      throw err;
    }
  }

  /**
   * Download the database file with progress tracking
   */
  private async downloadDatabase(url: string): Promise<Uint8Array> {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to download database: ${response.statusText}`);
    }

    const contentLength = response.headers.get('content-length');
    const total = contentLength ? parseInt(contentLength, 10) : 0;

    if (!response.body) {
      throw new Error('Response body is null');
    }

    // Check if the file is gzipped
    const isGzipped = url.endsWith('.gz');

    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let loaded = 0;

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      chunks.push(value);
      loaded += value.length;

      if (total > 0) {
        this.loadProgress.set({
          loaded,
          total,
          percentage: Math.round((loaded / total) * 100),
        });
      }
    }

    // Combine chunks
    const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const compressed = new Uint8Array(totalLength);
    let offset = 0;

    for (const chunk of chunks) {
      compressed.set(chunk, offset);
      offset += chunk.length;
    }

    // Decompress if gzipped
    if (isGzipped) {
      console.log('🔄 Checking if database needs decompression...');
      console.log(`   Downloaded size: ${(compressed.length / 1024 / 1024).toFixed(2)} MB`);
      console.log(`   First bytes: ${Array.from(compressed.slice(0, 10)).map(b => b.toString(16).padStart(2, '0')).join(' ')}`);
      
      // Check if the file is actually gzipped by checking the magic bytes
      // Gzip files start with 0x1F 0x8B
      // SQLite files start with "SQLite format 3" (0x53 0x51 0x4C 0x69 0x74 0x65)
      const isActuallyGzipped = compressed[0] === 0x1F && compressed[1] === 0x8B;
      const isSqliteFormat = compressed[0] === 0x53 && compressed[1] === 0x51 && compressed[2] === 0x4C;
      
      if (isSqliteFormat) {
        console.log('✓ File is already decompressed (SQLite format detected)');
        return compressed;
      }
      
      if (!isActuallyGzipped) {
        console.warn('⚠ File does not have gzip magic bytes, using as-is');
        return compressed;
      }
      
      try {
        const result = ungzip(compressed);
        console.log(`✓ Database decompressed: ${(result.length / 1024 / 1024).toFixed(2)} MB`);
        return result;
      } catch (err: any) {
        console.error('Decompression error details:', err);
        const errorMsg = err?.message || err?.toString() || 'Unknown decompression error';
        throw new Error(`Failed to decompress database: ${errorMsg}`);
      }
    }

    return compressed;
  }

  /**
   * Cache database in IndexedDB for faster subsequent loads
   */
  private async cacheDatabase(data: Uint8Array): Promise<void> {
    try {
      const dbName = 'CodingManagerDB';
      const storeName = 'database';

      const db = await new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open(dbName, 1);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
          const db = (event.target as IDBOpenDBRequest).result;
          if (!db.objectStoreNames.contains(storeName)) {
            db.createObjectStore(storeName);
          }
        };
      });

      // Wait for any pending upgrade to complete before creating transaction
      await new Promise(resolve => setTimeout(resolve, 100));

      // Verify object store exists before creating transaction
      if (!db.objectStoreNames.contains(storeName)) {
        throw new Error(`Object store '${storeName}' not found`);
      }

      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      store.put(data, 'coding_database');

      await new Promise<void>((resolve, reject) => {
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
      });

      db.close();
    } catch (err) {
      console.warn('Failed to cache database:', err);
      // Non-fatal error - continue without caching
    }
  }

  /**
   * Retrieve cached database from IndexedDB
   */
  private async getCachedDatabase(): Promise<Uint8Array | null> {
    try {
      const dbName = 'CodingManagerDB';
      const storeName = 'database';

      const db = await new Promise<IDBDatabase | null>((resolve) => {
        const request = indexedDB.open(dbName, 1);
        request.onerror = () => resolve(null);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
          const db = (event.target as IDBOpenDBRequest).result;
          if (!db.objectStoreNames.contains(storeName)) {
            db.createObjectStore(storeName);
          }
        };
      });

      if (!db) return null;

      // Check if object store exists
      if (!db.objectStoreNames.contains(storeName)) {
        db.close();
        return null;
      }

      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.get('coding_database');

      const result = await new Promise<Uint8Array | null>((resolve) => {
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => resolve(null);
      });

      db.close();
      return result;
    } catch (err) {
      console.warn('Failed to retrieve cached database:', err);
      return null;
    }
  }

  /**
   * Execute a SQL query and return results.
   * Always uses prepared statements so we get column names from getColumnNames()
   * (exec() in some sql.js builds returns empty columns).
   */
  async query(sql: string, params: any[] = []): Promise<QueryResult[]> {
    if (!this.isReady()) {
      await this.initialize();
    }

    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const stmt = this.db.prepare(sql);
      if (params.length > 0) {
        stmt.bind(params);
      }

      const values: any[][] = [];
      let columns: string[] = [];

      while (stmt.step()) {
        if (columns.length === 0) {
          // getColumnNames() must be called after first step()
          columns = stmt.getColumnNames() ?? [];
        }
        values.push(stmt.get());
      }

      stmt.free();

      if (columns.length === 0) {
        return [];
      }

      return [{ columns, values }];
    } catch (err: any) {
      console.error('Query error:', sql, err);
      throw new Error(`Query failed: ${err.message}`);
    }
  }

  /**
   * Execute a query and return the first result as objects
   */
  async queryAsObjects<T = any>(sql: string, params: any[] = []): Promise<T[]> {
    try {
      const results = await this.query(sql, params);

      if (!results || results.length === 0 || !results[0]) {
        return [];
      }

      const { columns, values } = results[0];
      const cols = columns ?? [];
      const vals = values ?? [];

      if (cols.length === 0 || vals.length === 0) {
        if (vals.length > 0 && cols.length === 0) {
          console.warn('queryAsObjects: result has rows but no column names (sql may vary). Columns:', columns);
        }
        return [];
      }

      return vals.map((row) => {
        const obj: any = {};
        cols.forEach((col, i) => {
          obj[col] = row[i];
        });
        return obj as T;
      });
    } catch (error) {
      console.error('queryAsObjects error:', error);
      // Always return an array, never undefined
      return [];
    }
  }

  /**
   * Execute a query and return a single object (first row only)
   */
  async queryOne<T = any>(sql: string, params: any[] = []): Promise<T | null> {
    try {
      const results = await this.queryAsObjects<T>(sql, params);
      return results.length > 0 ? results[0] : null;
    } catch (error) {
      console.error('queryOne error:', error);
      return null;
    }
  }

  /**
   * Execute a query and return a single value (first column of first row)
   */
  async queryScalar<T = any>(sql: string, params: any[] = []): Promise<T | null> {
    const results = await this.query(sql, params);

    if (!results || results.length === 0 || !results[0]?.values?.length) {
      return null;
    }

    return results[0].values[0][0] as T;
  }

  /**
   * Clear the cached database (force re-download on next load)
   */
  async clearCache(): Promise<void> {
    try {
      const dbName = 'CodingManagerDB';
      await new Promise<void>((resolve, reject) => {
        const request = indexedDB.deleteDatabase(dbName);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
      console.log('✓ Database cache cleared');
    } catch (err) {
      console.error('Failed to clear cache:', err);
      throw err;
    }
  }

  /**
   * Get database statistics
   */
  async getStats(): Promise<Record<string, number>> {
    const stats: Record<string, number> = {};

    const tables = [
      'snomed_codes',
      'icd10_codes',
      'hcc_codes',
      'cpt_codes',
      'hcpcs_codes',
      'rxnorm_codes',
      'ndc_codes',
      'snomed_icd10_mapping',
      'snomed_hcc_mapping',
      'icd10_hcc_mapping',
      'rxnorm_snomed_mapping',
      'ndc_rxnorm_mapping',
    ];

    for (const table of tables) {
      try {
        const count = await this.queryScalar<number>(`SELECT COUNT(*) FROM ${table}`);
        // Transform table names ending in "_mapping" to "_mappings" (plural) for API compatibility
        const key = table.endsWith('_mapping') ? table + 's' : table;
        stats[key] = count || 0;
      } catch {
        // Transform table names ending in "_mapping" to "_mappings" (plural) for API compatibility
        const key = table.endsWith('_mapping') ? table + 's' : table;
        stats[key] = 0;
      }
    }

    return stats;
  }

  /**
   * Close the database connection
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
    this.isReady.set(false);
  }
}
