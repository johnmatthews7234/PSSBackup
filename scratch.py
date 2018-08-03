import sqlite3

db = sqlite3.connect('mydb.db')

cursor = db.cursor()

cursor.execute('''
    CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, phone TEXT,
        email TEXT unique, password TEXT)
''')
db.commit()

db.close()