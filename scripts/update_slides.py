import json
import psycopg2

with open("decks/FEN_MF1/audio/FEN_MF1-array.json", "r") as f:
    lines = json.load(f)
    print(f"Loaded {len(lines)} lines")

conn = psycopg2.connect(dbname="slides_db", user="cjohndesign", host="localhost")
cur = conn.cursor()

cur.execute("DELETE FROM slides WHERE presentation_id = 'FEN_MF1';")
print("Deleted existing slides")

for i, line in enumerate(lines, 1):
    cur.execute("INSERT INTO slides (presentation_id, slide_number, line, layout, transition) VALUES ('FEN_MF1', %s, %s, 'default', 'fade-out');", (i, line))
    print(f"Inserted slide {i}")

conn.commit()
print("Changes committed")

cur.execute("SELECT COUNT(*) FROM slides WHERE presentation_id = 'FEN_MF1';")
count = cur.fetchone()[0]
print(f"Total slides: {count}")

cur.close()
conn.close() 