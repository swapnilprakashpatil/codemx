/**
 * Environment configuration — API mode (default).
 * The Angular app connects to the Flask backend API.
 */
export const environment = {
  production: false,
  apiMode: 'api' as 'api' | 'static' | 'sqljs',
  apiUrl: 'http://localhost:5000/api',
  staticDataPath: 'data',
  useSqlJs: false,
  sqlJsDatabaseUrl: 'data/coding_database.sqlite.gz',
};
