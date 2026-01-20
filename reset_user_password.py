import sqlite3
from models_db import DB_PATH

email = "pablo@gmail.com"

c = sqlite3.connect(DB_PATH)
cur = c.cursor()
cur.execute("DELETE FROM users WHERE email = ?", (email,))
c.commit()
print("Deleted rows:", cur.rowcount)
c.close()
