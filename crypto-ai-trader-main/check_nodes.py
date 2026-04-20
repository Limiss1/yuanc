import sqlite3
import json

conn = sqlite3.connect('D:/v2rayN/guiConfigs/guiNDB.db')
cursor = conn.cursor()

cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print(f"Tables: {tables}")

cursor.execute('SELECT * FROM ProfileItem')
cols = [d[0] for d in cursor.description]
print(f"Columns: {cols}")

rows = cursor.fetchall()
print(f"Total nodes: {len(rows)}")

for i, row in enumerate(rows):
    row_dict = dict(zip(cols, row))
    remarks = row_dict.get('remarks', 'N/A')
    address = row_dict.get('address', 'N/A')
    port = row_dict.get('port', 'N/A')
    config_type = row_dict.get('configType', 'N/A')
    print(f"  [{i}] {remarks} | {address}:{port} | type={config_type}")

conn.close()
