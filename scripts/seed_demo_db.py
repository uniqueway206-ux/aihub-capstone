"""Create a small demo SQLite database for the SQL-chat feature."""
import random
import sqlite3
from pathlib import Path

DB = Path("data/demo.db")
DB.parent.mkdir(exist_ok=True)
DB.unlink(missing_ok=True)
random.seed(7)

con = sqlite3.connect(DB)
con.executescript(
    """
    CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, city TEXT);
    CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
    CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER,
                        quantity INTEGER, order_date TEXT);
    """
)
cities = ["Lahore", "Karachi", "Islamabad", "Faisalabad"]
con.executemany("INSERT INTO customers VALUES(?,?,?)",
                [(i, f"Customer {i}", random.choice(cities)) for i in range(1, 21)])
con.executemany("INSERT INTO products VALUES(?,?,?,?)", [
    (1, "Laptop", "Electronics", 950.0), (2, "Headphones", "Electronics", 60.0),
    (3, "Desk Chair", "Furniture", 140.0), (4, "Notebook", "Stationery", 3.5),
    (5, "Monitor", "Electronics", 210.0)])
con.executemany("INSERT INTO orders VALUES(?,?,?,?,?)", [
    (i, random.randint(1, 20), random.randint(1, 5), random.randint(1, 4),
     f"2026-{random.randint(1, 10):02d}-{random.randint(1, 28):02d}") for i in range(1, 201)])
con.commit()
con.close()
print(f"Seeded {DB}")
