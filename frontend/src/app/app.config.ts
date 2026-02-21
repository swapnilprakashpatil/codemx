import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, HttpClient } from '@angular/common/http';

import { routes } from './app.routes';
import { environment } from '../environments/environment';
import { CodingApi } from './services/coding-api';
import { CodingApiHttp } from './services/coding-api-http';
import { CodingApiStatic } from './services/coding-api-static';
import { CodingApiSqlJs } from './services/coding-api-sqljs';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(),
    {
      provide: CodingApi,
      useFactory: (http: HttpClient) => {
        if (environment.apiMode === 'sqljs' || (environment as any).useSqlJs) {
          console.log('🔧 Using sql.js mode');
          return new CodingApiSqlJs();
        }
        if (environment.apiMode === 'static') {
          console.log('🔧 Using static JSON mode');
          return new CodingApiStatic(http);
        }
        console.log('🔧 Using backend API mode');
        return new CodingApiHttp(http);
      },
      deps: [HttpClient],
    },
  ]
};
