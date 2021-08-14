import sqlite3

def update_rate(data):
    connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
    if connection:
        cur = connection.cursor()
        # REPLACE: EXISTS       ->      UPDATE 
        #          NOT EXISTS   ->      INSERT
        query = '''REPLACE INTO currency (currency, buy, sell) 
                VALUES (:currency, :buy, :sell)'''
        cur.executemany(query, data)
        connection.commit()
        cur.close()
        connection.close()

def register(data):
    connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
    if connection:
        cur = connection.cursor()
        query = '''INSERT INTO account (username, password) 
                VALUES (:username, :password)'''
        cur.execute(query, data)
        connection.commit()
        cur.close()
        connection.close()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d