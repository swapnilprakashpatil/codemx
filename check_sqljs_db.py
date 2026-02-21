import sqlite3

conn = sqlite3.connect('frontend/public/data/coding_database.sqlite')
cursor = conn.cursor()

print('\n📋 Tables in sql.js database:\n')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for table in cursor.fetchall():
    table_name = table[0]
    count = cursor.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
    print(f'  ✓ {table_name}: {count:,} rows')

conn.close()
print()
