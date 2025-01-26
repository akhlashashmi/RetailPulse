import streamlit as st
from streamlit_option_menu import option_menu
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import sqlite3
import pandas as pd
import datetime
import plotly.express as px
import base64
import hashlib
from io import BytesIO
from barcode.ean import EAN13
from barcode.writer import ImageWriter
import os

# -------------------- Database Setup --------------------
DATABASE = "inventory.db"

# -------------------- Database Setup --------------------
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT CHECK(role IN ('admin', 'staff')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Products Table (Added user_id)
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
        
        # Sales Table (Added user_id)
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
        
        # Debts Table (Added user_id)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            customer_name TEXT,
            phone TEXT,
            initial_amount REAL CHECK(initial_amount >= 0),
            remaining_amount REAL CHECK(remaining_amount >= 0),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date DATE,
            status TEXT CHECK(status IN ('active', 'paid', 'overdue')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        # Debt Payments Table (Added user_id)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            debt_id INTEGER,
            amount REAL CHECK(amount >= 0),
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (debt_id) REFERENCES debts (id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')
        
        # Suppliers Table (Added user_id)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            contact TEXT,
            email TEXT,
            address TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, name)
        )''')

# Initialize database
init_db()

# -------------------- Helper Functions --------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, role):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
        ''', (username, hash_password(password), role))
        conn.commit()

def authenticate(username, password):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id, username, role FROM users 
        WHERE username = ? AND password = ?
        ''', (username, hash_password(password)))
        return cursor.fetchone()

def get_products():
    with sqlite3.connect(DATABASE) as conn:
        return pd.read_sql("SELECT * FROM products", conn)

def generate_barcode(product_id):
    barcode = EAN13(str(product_id).zfill(12), writer=ImageWriter())
    filename = f"barcode_{product_id}"
    barcode.save(filename)
    return f"{filename}.png"

# -------------------- Authentication --------------------
# -------------------- Authentication --------------------
def login_page():
    st.title("🔐 Shop Manager Pro Login")
    
    # Check if any users exist
    with sqlite3.connect(DATABASE) as conn:
        user_count = pd.read_sql("SELECT COUNT(*) FROM users", conn).iloc[0,0]
    
    if user_count == 0:
        st.warning("No users found! Please create an admin account.")
        create_account_form(initial_admin=True)
        return
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.form_submit_button("Login"):
            user = authenticate(username, password)
            if user:
                st.session_state.user = {
                    "id": user[0],
                    "username": user[1],
                    "role": user[2]
                }
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    st.markdown("---")
    with st.expander("Create New Account (Admin Only)"):
        create_account_form()

def create_account_form(initial_admin=False):
    with st.form("create_account_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = "admin" if initial_admin else st.selectbox("Role", ["admin", "staff"])
        
        if st.form_submit_button("Create Account"):
            if not username or not password:
                st.error("Please fill all fields")
                return
            
            try:
                create_user(username, password, role)
                st.success("Account created successfully!")
                if initial_admin:
                    st.rerun()
            except sqlite3.IntegrityError:
                st.error("Username already exists!")

# -------------------- Settings Management --------------------
def manage_settings():
    st.title("⚙️ Settings")
    
    if st.session_state.user['role'] != 'admin':
        st.warning("Only admins can access settings")
        return
    
    tab1, tab2 = st.tabs(["User Management", "Database"])
    
    with tab1:
        st.subheader("User Accounts")
        users = pd.read_sql("SELECT id, username, role FROM users", sqlite3.connect(DATABASE))
        st.dataframe(users)
        
        with st.expander("Create New User"):
            create_account_form()
        
        with st.expander("Delete User"):
            user_id = st.number_input("User ID to delete", min_value=1)
            if st.button("Delete User"):
                with sqlite3.connect(DATABASE) as conn:
                    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                st.success("User deleted successfully!")
    
    with tab2:
        st.subheader("Database Management")
        st.download_button(
            label="Backup Database",
            data=open(DATABASE, "rb").read(),
            file_name="inventory_backup.db",
            mime="application/octet-stream"
        )
        
        st.markdown("---")
        uploaded_db = st.file_uploader("Restore Database", type="db")
        if uploaded_db and st.button("Restore Backup"):
            with open(DATABASE, "wb") as f:
                f.write(uploaded_db.getvalue())
            st.success("Database restored successfully!")
# -------------------- Main Application --------------------
def main_app():
    st.set_page_config(
        page_title="Shop Manager Pro",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2331/2331966.png", width=100)
        menu = option_menu(
            menu_title="Main Menu",
            options=["Dashboard", "Inventory", "Sales", "Debts", "Suppliers", "Reports", "Settings"],
            icons=["speedometer", "box", "cash", "person-rolodex", "truck", "graph-up", "gear"],
            default_index=0
        )
    
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Inventory":
        manage_inventory()
    elif menu == "Sales":
        manage_sales()
    elif menu == "Debts":
        manage_debts()
    elif menu == "Suppliers":
        manage_suppliers()
    elif menu == "Reports":
        generate_reports()
    elif menu == "Settings":
        manage_settings()

# -------------------- Dashboard --------------------
def show_dashboard():
    st.title("📊 Shop Dashboard")
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_stock = get_products()['quantity'].sum()
        st.metric("Total Stock Value", f"₹{total_stock:,.2f}")
    with col2:
        low_stock = get_products()[get_products()['quantity'] <= get_products()['alert_threshold']]
        st.metric("Low Stock Items", len(low_stock), delta_color="inverse")
    with col3:
        total_sales = pd.read_sql("SELECT SUM(total_price) FROM sales", sqlite3.connect(DATABASE)).iloc[0,0] or 0
        st.metric("Total Sales", f"₹{total_sales:,.2f}")
    with col4:
        active_debts = pd.read_sql("SELECT SUM(remaining_amount) FROM debts WHERE status='active'", 
                                 sqlite3.connect(DATABASE)).iloc[0,0] or 0
        st.metric("Active Debts", f"₹{active_debts:,.2f}")
    
    # Sales Chart
    st.subheader("Sales Trend (Last 30 Days)")
    sales_data = pd.read_sql('''
    SELECT DATE(sale_date) as date, SUM(total_price) as total 
    FROM sales 
    WHERE sale_date >= DATE('now', '-30 days')
    GROUP BY DATE(sale_date)
    ''', sqlite3.connect(DATABASE))
    if not sales_data.empty:
        fig = px.line(sales_data, x='date', y='total', 
                     labels={'total': 'Daily Sales'}, markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sales data available")

# -------------------- Inventory Management --------------------
def manage_inventory():
    st.title("📦 Inventory Management")
    
    with st.expander("Bulk Operations", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("CSV Import")
            uploaded_file = st.file_uploader("Upload products CSV", type="csv")
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    df['user_id'] = get_current_user_id()
                    with sqlite3.connect(DATABASE) as conn:
                        df.to_sql('products', conn, if_exists='append', index=False)
                    st.success(f"Imported {len(df)} products successfully!")
                except Exception as e:
                    st.error(f"Import error: {str(e)}")
        
        with col2:
            st.subheader("Export Data")
            if st.button("Export Current Inventory"):
                df = get_products()
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="inventory.csv",
                    mime="text/csv"
                )

    st.markdown("---")
    st.subheader("Product Management")
    
    with st.expander("Real-time Stock Alerts"):
        products = get_products()
        low_stock = products[products['quantity'] <= products['alert_threshold']]
        if not low_stock.empty:
            st.warning(f"🚨 {len(low_stock)} items need restocking!")
            st.dataframe(low_stock[['name', 'quantity', 'alert_threshold']])
        else:
            st.success("All stock levels are satisfactory")

    with st.expander("Product List & Actions"):
        products = get_products()
        if not products.empty:
            gb = GridOptionsBuilder.from_dataframe(products)
            gb.configure_pagination(paginationPageSize=10)
            gb.configure_side_bar()
            gb.configure_selection('single', use_checkbox=True)
            gb.configure_column("quantity", editable=True, headerName="Current Stock")
            grid_options = gb.build()
            
            grid_response = AgGrid(
                products,
                gridOptions=grid_options,
                columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                theme="streamlit",
                update_mode='MODEL_CHANGED'
            )
            
            selected = grid_response['selected_rows']
            if selected:
                product = selected[0]
                with st.container(border=True):
                    st.subheader("Selected Product Actions")
                    col1, col2, col3 = st.columns([2,2,1])
                    with col1:
                        with st.form("update_stock_form"):
                            new_qty = st.number_input("Update Stock", 
                                                    value=product['quantity'],
                                                    min_value=0)
                            if st.form_submit_button("Update Quantity"):
                                with sqlite3.connect(DATABASE) as conn:
                                    conn.execute("""
                                        UPDATE products 
                                        SET quantity = ?, last_restock = CURRENT_TIMESTAMP 
                                        WHERE id = ? AND user_id = ?
                                    """, (new_qty, product['id'], get_current_user_id()))
                                    st.success("Stock updated!")
                    with col2:
                        if st.button("Generate Barcode"):
                            barcode_path = generate_barcode(product['id'])
                            st.image(barcode_path)
                            os.remove(barcode_path)
                    with col3:
                        if st.button("🗑️ Delete Product", type="secondary"):
                            with sqlite3.connect(DATABASE) as conn:
                                conn.execute("DELETE FROM products WHERE id = ? AND user_id = ?",
                                           (product['id'], get_current_user_id()))
                            st.rerun()
        else:
            st.info("No products found in inventory")

    with st.expander("Add New Product", expanded=False):
        with st.form("add_product_form", clear_on_submit=True):
            cols = st.columns([2,1,1,1])
            with cols[0]:
                name = st.text_input("Product Name", key="prod_name")
                category = st.text_input("Category")
            with cols[1]:
                quantity = st.number_input("Initial Stock", min_value=0, step=10)
            with cols[2]:
                unit_price = st.number_input("Unit Price", min_value=0.0, step=0.5)
            with cols[3]:
                alert_threshold = st.number_input("Low Stock Alert", min_value=1, value=5)
            
            if st.form_submit_button("➕ Add Product"):
                try:
                    with sqlite3.connect(DATABASE) as conn:
                        conn.execute('''
                            INSERT INTO products 
                            (user_id, name, category, quantity, unit_price, alert_threshold)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (get_current_user_id(), name, category, quantity, unit_price, alert_threshold))
                    st.success("Product added successfully!")
                except sqlite3.IntegrityError:
                    st.error("Product name already exists for your account!")

# -------------------- Helper Functions --------------------
def get_current_user_id():
    return st.session_state.user['id']

def get_products():
    user_id = get_current_user_id()
    with sqlite3.connect(DATABASE) as conn:
        return pd.read_sql("SELECT * FROM products WHERE user_id = ?", conn, params=(user_id,))

def get_sales():
    user_id = get_current_user_id()
    with sqlite3.connect(DATABASE) as conn:
        return pd.read_sql('''
            SELECT sales.*, products.name 
            FROM sales 
            JOIN products ON sales.product_id = products.id
            WHERE sales.user_id = ?
        ''', conn, params=(user_id,))

# -------------------- Supplier Management --------------------
def manage_suppliers():
    st.title("🚚 Supplier Management")
    
    tab1, tab2 = st.tabs(["View Suppliers", "Add Supplier"])
    
    with tab1:
        suppliers = pd.read_sql("SELECT * FROM suppliers", sqlite3.connect(DATABASE))
        if not suppliers.empty:
            st.dataframe(suppliers)
        else:
            st.info("No suppliers registered")
    
    with tab2:
        with st.form("add_supplier_form"):
            name = st.text_input("Supplier Name")
            contact = st.text_input("Contact Person")
            email = st.text_input("Email")
            address = st.text_area("Address")
            
            if st.form_submit_button("Add Supplier"):
                try:
                    with sqlite3.connect(DATABASE) as conn:
                        conn.execute('''
                        INSERT INTO suppliers (name, contact, email, address)
                        VALUES (?, ?, ?, ?)
                        ''', (name, contact, email, address))
                    st.success("Supplier added successfully!")
                except sqlite3.IntegrityError:
                    st.error("Supplier name already exists!")

# -------------------- Report Generation --------------------
def generate_reports():
    st.title("📈 Reporting & Analytics")
    
    report_type = st.selectbox("Select Report Type", 
                             ["Sales Report", "Inventory Report", "Debt Report"])
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.date.today())
    
    if st.button("Generate Report"):
        if report_type == "Sales Report":
            sales_data = pd.read_sql(f'''
            SELECT products.name, SUM(quantity_sold) as total_quantity, 
                   SUM(total_price) as total_sales
            FROM sales
            JOIN products ON sales.product_id = products.id
            WHERE DATE(sale_date) BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY products.name
            ''', sqlite3.connect(DATABASE))
            
            st.subheader("Sales Report")
            if not sales_data.empty:
                fig = px.bar(sales_data, x='name', y='total_sales', 
                           title="Product Sales Performance")
                st.plotly_chart(fig)
                st.dataframe(sales_data)
            else:
                st.warning("No sales data in selected period")
        
        elif report_type == "Inventory Report":
            inventory = get_products()
            st.subheader("Inventory Status")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Products", len(inventory))
            with col2:
                st.metric("Total Stock Value", f"₹{inventory['quantity'].sum():,.2f}")
            
            fig = px.pie(inventory, names='category', values='quantity', 
                       title="Stock Distribution by Category")
            st.plotly_chart(fig)
        
        elif report_type == "Debt Report":
            debts = pd.read_sql(f'''
            SELECT customer_name, phone, initial_amount, remaining_amount, due_date
            FROM debts
            WHERE status = 'active' AND due_date BETWEEN '{start_date}' AND '{end_date}'
            ''', sqlite3.connect(DATABASE))
            
            st.subheader("Active Debts Report")
            if not debts.empty:
                st.dataframe(debts)
                total_debt = debts['remaining_amount'].sum()
                st.metric("Total Outstanding Debt", f"₹{total_debt:,.2f}")
            else:
                st.info("No active debts in selected period")

# -------------------- Sales Management --------------------
def manage_sales():
    st.title("💵 Sales Processing")
    
    products = get_products()
    if products.empty:
        st.warning("No products available for sale")
        return
    
    with st.container(border=True):
        st.subheader("New Sale Transaction")
        selected_products = st.multiselect(
            "Select products to sell",
            options=products.to_dict('records'),
            format_func=lambda x: f"{x['name']} (₹{x['unit_price']} | Stock: {x['quantity']})",
            key="sale_products"
        )
        
        sale_items = []
        for idx, product in enumerate(selected_products):
            with st.container(border=True):
                cols = st.columns([1,2,1])
                with cols[0]:
                    st.markdown(f"**{product['name']}**")
                with cols[1]:
                    qty = st.slider(
                        "Quantity",
                        1, product['quantity'],
                        key=f"qty_{product['id']}",
                        help="Adjust quantity to sell"
                    )
                with cols[2]:
                    price = st.number_input(
                        "Price",
                        value=product['unit_price'],
                        min_value=0.0,
                        key=f"price_{product['id']}",
                        step=0.5
                    )
                sale_items.append({
                    'product_id': product['id'],
                    'qty': qty,
                    'price': price,
                    'total': qty * price
                })

        if sale_items:
            st.divider()
            total = sum(item['total'] for item in sale_items)
            st.markdown(f"### Total Amount: ₹{total:,.2f}")
            
            cols = st.columns([3,1])
            with cols[0]:
                customer_name = st.text_input("Customer Name (Optional)")
            with cols[1]:
                if st.button("💳 Process Sale", type="primary", use_container_width=True):
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            cursor = conn.cursor()
                            for item in sale_items:
                                # Update inventory
                                cursor.execute('''
                                    UPDATE products 
                                    SET quantity = quantity - ?
                                    WHERE id = ? AND user_id = ?
                                ''', (item['qty'], item['product_id'], get_current_user_id()))
                                # Record sale
                                cursor.execute('''
                                    INSERT INTO sales 
                                    (user_id, product_id, quantity_sold, total_price)
                                    VALUES (?, ?, ?, ?)
                                ''', (get_current_user_id(), item['product_id'], item['qty'], item['total']))
                        
                        st.success("Sale processed successfully!")
                        st.balloons()
                        
                        # Generate receipt
                        receipt = generate_receipt(sale_items, total, customer_name)
                        st.download_button(
                            label="📄 Download Receipt",
                            data=receipt,
                            file_name=f"receipt_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                            mime="text/plain"
                        )
                    except Exception as e:
                        st.error(f"Transaction failed: {str(e)}")


# -------------------- Debt Management --------------------
def manage_debts():
    st.title("📝 Debt Management")
    
    tab1, tab2, tab3 = st.tabs(["Active Debts", "Record Payment", "Add New Debt"])
    
    with tab1:
        debts = pd.read_sql("SELECT * FROM debts WHERE status='active'", sqlite3.connect(DATABASE))
        if not debts.empty:
            st.dataframe(debts)
        else:
            st.info("No active debts")
    
    with tab2:
        with st.form("payment_form"):
            debt_id = st.number_input("Debt ID", min_value=1)
            amount = st.number_input("Payment Amount", min_value=0.0)
            
            if st.form_submit_button("Record Payment"):
                with sqlite3.connect(DATABASE) as conn:
                    # Record payment
                    conn.execute('''
                    INSERT INTO debt_payments (debt_id, amount)
                    VALUES (?, ?)
                    ''', (debt_id, amount))
                    
                    # Update debt status
                    conn.execute('''
                    UPDATE debts 
                    SET remaining_amount = remaining_amount - ?
                    WHERE id = ?
                    ''', (amount, debt_id))
                    
                    st.success("Payment recorded!")
    
    with tab3:
        with st.form("new_debt_form"):
            name = st.text_input("Customer Name")
            phone = st.text_input("Phone Number")
            amount = st.number_input("Debt Amount", min_value=0.0)
            due_date = st.date_input("Due Date")
            
            if st.form_submit_button("Add Debt"):
                with sqlite3.connect(DATABASE) as conn:
                    conn.execute('''
                    INSERT INTO debts 
                    (customer_name, phone, initial_amount, remaining_amount, due_date, status)
                    VALUES (?, ?, ?, ?, ?, 'active')
                    ''', (name, phone, amount, amount, due_date))
                st.success("Debt added successfully!")

# -------------------- Main Execution --------------------
if __name__ == "__main__":
    if 'user' not in st.session_state:
        login_page()
    else:
        main_app()