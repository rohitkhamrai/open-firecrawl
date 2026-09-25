import psycopg2, json, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("SELECT schema_data FROM keyword_data WHERE keyword = 'Ashlesha Bali Pooja'")
row = cur.fetchone()
if row:
    print(json.dumps(row[0], indent=2))
else:
    print("Not found")
