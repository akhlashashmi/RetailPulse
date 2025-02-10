import sqlite3
import pandas as pd
import streamlit as st

DATABASE = "inventory.db"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        # Users Table (unchanged)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT CHECK(role IN ('admin', 'staff')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Products Table (unchanged)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            category TEXT,
            quantity INTEGER CHECK(quantity >= 0),
            unit_price REAL CHECK(unit_price >= 0),
            barcode TEXT,
            alert_threshold INTEGER DEFAULT 5,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_restock TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, name)
        )''')
        
        # Sales Table (unchanged)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity_sold INTEGER CHECK(quantity_sold > 0),
            total_price REAL CHECK(total_price >= 0),
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        # Customers Table (new)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            phone TEXT,
            address TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        # Customer Debts Table (enhanced)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            customer_id INTEGER,
            initial_amount REAL CHECK(initial_amount >= 0),
            remaining_amount REAL CHECK(remaining_amount >= 0),
            description TEXT,
            due_date DATE,
            status TEXT CHECK(status IN ('active', 'paid', 'overdue')),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )''')
        
        # Customer Debt Payments Table (enhanced)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            debt_id INTEGER,
            amount REAL CHECK(amount >= 0),
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (debt_id) REFERENCES customer_debts(id)
        )''')
        
        # Suppliers Table (enhanced)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            contact TEXT,
            email TEXT,
            address TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, name)
        )''')
        
        # Supplier Debts Table (new)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplier_debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            supplier_id INTEGER,
            initial_amount REAL CHECK(initial_amount >= 0),
            remaining_amount REAL CHECK(remaining_amount >= 0),
            description TEXT,
            due_date DATE,
            status TEXT CHECK(status IN ('active', 'paid', 'overdue')),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        )''')
        
        # Supplier Debt Payments Table (new)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplier_debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            debt_id INTEGER,
            amount REAL CHECK(amount >= 0),
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (debt_id) REFERENCES supplier_debts(id)
        )''')
        
        # History Table (new for tracking all changes)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            entity_type TEXT,  -- e.g., 'product', 'sale', 'customer_debt', 'supplier_debt'
            entity_id INTEGER,
            action TEXT,       -- e.g., 'create', 'update', 'delete', 'payment'
            details TEXT,      -- JSON or text description of changes
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        conn.commit()

# Helper functions
def get_current_user_id():
    return st.session_state.user['id']

def get_products(user_id):
    with sqlite3.connect(DATABASE) as conn:
        return pd.read_sql("SELECT * FROM products WHERE user_id = ?", conn, params=(user_id,))

def get_sales(user_id):
    with sqlite3.connect(DATABASE) as conn:
        return pd.read_sql('''
            SELECT sales.*, products.name 
            FROM sales 
            JOIN products ON sales.product_id = products.id
            WHERE sales.user_id = ?
        ''', conn, params=(user_id,))

def log_history(user_id, entity_type, entity_id, action, details):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
        INSERT INTO history (user_id, entity_type, entity_id, action, details)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, entity_type, entity_id, action, str(details)))
        conn.commit()