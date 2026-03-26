import sqlite3

conn = sqlite3.connect('audit.db')
cur = conn.cursor()
rows = cur.execute(
    """
    SELECT doc_id, step, status, substr(response,1,800)
    FROM audit_logs
    WHERE step IN ('NA_ORDER_EXTRACTION','LEASE_EXTRACTION','DNR_EXTRACTION')
    ORDER BY timestamp DESC
    LIMIT 20
    """
).fetchall()
conn.close()

for row in rows:
    print('---')
    print('DOC:', row[0])
    print('STEP:', row[1])
    print('STATUS:', row[2])
    print('RESP:', row[3])
