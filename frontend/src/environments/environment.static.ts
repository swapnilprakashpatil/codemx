/**
 * Environment configuration — Static mode (GitHub Pages).
 * The Angular app uses sql.js to query a SQLite database in the browser.
 */
export const environment = {
  production: true,
  apiMode: 'sqljs' as 'api' | 'static' | 'sqljs',
  apiUrl: '',
  staticDataPath: '/data',
  useSqlJs: true,
  sqlJsDatabaseUrl: '/data/coding_database.sqlite.gz',
};
