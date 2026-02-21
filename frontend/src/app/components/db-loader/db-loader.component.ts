/**
 * Database Loader Component
 *
 * Displays loading progress for sql.js database initialization.
 * Shows progress bar, status messages, and handles errors.
 */

import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DatabaseService } from '../../services/database.service';

@Component({
  selector: 'app-db-loader',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="db-loader-overlay" *ngIf="db.isLoading() || db.error()">
      <div class="db-loader-card">
        <div class="db-loader-header">
          <h2>{{ db.error() ? '⚠️ Database Error' : '🔄 Loading Database' }}</h2>
        </div>

        <div class="db-loader-body">
          @if (db.error()) {
            <div class="error-message">
              <p class="error-text">{{ db.error() }}</p>
              <button class="retry-button" (click)="retry()">Retry</button>
            </div>
          } @else {
            <div class="progress-info">
              @if (db.loadProgress(); as progress) {
                <p class="progress-text">
                  {{ formatBytes(progress.loaded) }} / {{ formatBytes(progress.total) }}
                  ({{ progress.percentage }}%)
                </p>
                <div class="progress-bar">
                  <div class="progress-fill" [style.width.%]="progress.percentage"></div>
                </div>
              } @else {
                <p class="progress-text">Initializing...</p>
                <div class="spinner"></div>
              }
            </div>
            <p class="help-text">This may take a few seconds on first load. The database will be cached for future visits.</p>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .db-loader-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      backdrop-filter: blur(4px);
    }

    .db-loader-card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      max-width: 500px;
      width: 90%;
      overflow: hidden;
    }

    .db-loader-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 24px;
      text-align: center;
    }

    .db-loader-header h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
    }

    .db-loader-body {
      padding: 32px 24px;
    }

    .progress-info {
      margin-bottom: 16px;
    }

    .progress-text {
      font-size: 16px;
      color: #333;
      margin-bottom: 12px;
      text-align: center;
      font-weight: 500;
    }

    .progress-bar {
      height: 8px;
      background: #e0e0e0;
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 16px;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      transition: width 0.3s ease;
      border-radius: 4px;
    }

    .spinner {
      width: 40px;
      height: 40px;
      margin: 0 auto;
      border: 4px solid #e0e0e0;
      border-top-color: #667eea;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .help-text {
      font-size: 14px;
      color: #666;
      text-align: center;
      margin: 0;
      line-height: 1.5;
    }

    .error-message {
      text-align: center;
    }

    .error-text {
      font-size: 16px;
      color: #d32f2f;
      margin-bottom: 24px;
      padding: 16px;
      background: #ffebee;
      border-radius: 8px;
      border-left: 4px solid #d32f2f;
    }

    .retry-button {
      padding: 12px 32px;
      font-size: 16px;
      font-weight: 600;
      color: white;
      background: #667eea;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .retry-button:hover {
      background: #764ba2;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    .retry-button:active {
      transform: translateY(0);
    }
  `]
})
export class DbLoaderComponent implements OnInit {
  db = inject(DatabaseService);

  ngOnInit(): void {
    // Component automatically shows/hides based on db.isLoading() and db.error() signals
  }

  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  }

  retry(): void {
    // Clear cache and reload page
    this.db.clearCache().then(() => {
      window.location.reload();
    });
  }
}
