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

# connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
# if connection:
#         connection.row_factory = dict_factory
#         cur = connection.cursor()
#         data = {"currency": "All currencies"}
#         query = 'SELECT * FROM currency'
#         subquery = ""
#         if 'date' in data and data['currency'] != 'All currencies':
#             subquery = ' WHERE update_at = :date AND currency = :currency'
#         elif 'date' in data:
#             subquery = ' WHERE update_at = :date'
#         elif data['currency'] != 'All currencies':
#             subquery = ' WHERE currency = :currency'
#         query += subquery + ' ORDER BY update_at ASC, currency ASC'
#         cur.execute(query, data)
#         rows = cur.fetchall()
#         print(rows)
#         cur.close()
#         connection.close()

# connection = sqlite3.connect("db.db", detect_types=sqlite3.PARSE_DECLTYPES)
# if connection:
#     cur = connection.cursor()
#     body = {"username": "khatmausr"}
#     query = '''SELECT EXISTS(SELECT * FROM account WHERE username = :username)'''
#     cur.execute(query, body)
#     check = cur.fetchone()
#     cur.close()
#     connection.close()
#     if check[0] == 1:
#         print(0)
#     else:
#         print(1)




