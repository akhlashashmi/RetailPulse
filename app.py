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
DATABASE = "shop_management.db"

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT CHECK(role IN ('admin', 'staff'))
        )''')
        
        # Products Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            category TEXT,
            quantity INTEGER CHECK(quantity >= 0),
            unit_price REAL CHECK(unit_price >= 0),
            barcode TEXT UNIQUE,
            alert_threshold INTEGER DEFAULT 5,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_restock TIMESTAMP
        )''')
        
        # Sales Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity_sold INTEGER CHECK(quantity_sold > 0),
            total_price REAL CHECK(total_price >= 0),
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )''')
        
        # Debts Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            phone TEXT,
            initial_amount REAL CHECK(initial_amount >= 0),
            remaining_amount REAL CHECK(remaining_amount >= 0),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date DATE,
            status TEXT CHECK(status IN ('active', 'paid', 'overdue'))
        )''')
        
        # Debt Payments Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_id INTEGER,
            amount REAL CHECK(amount >= 0),
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (debt_id) REFERENCES debts (id)
        )''')
        
        # Suppliers Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            contact TEXT,
            email TEXT,
            address TEXT
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
            file_name="shop_backup.db",
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
    
    # Bulk Operations
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Bulk Import")
        uploaded_file = st.file_uploader("Upload CSV", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            try:
                with sqlite3.connect(DATABASE) as conn:
                    df.to_sql('products', conn, if_exists='append', index=False)
                st.success(f"Imported {len(df)} products successfully!")
            except Exception as e:
                st.error(f"Error importing: {str(e)}")
    
    with col2:
        st.subheader("Export Data")
        if st.button("Export Inventory"):
            df = get_products()
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="inventory.csv",
                mime="text/csv"
            )
    
    # Product Management
    st.subheader("Product List")
    products = get_products()
    
    # Low stock alerts
    low_stock = products[products['quantity'] <= products['alert_threshold']]
    if not low_stock.empty:
        st.warning(f"⚠️ {len(low_stock)} items below stock threshold!")
        st.dataframe(low_stock[['name', 'quantity', 'alert_threshold']])
    
    # Interactive Grid
    gb = GridOptionsBuilder.from_dataframe(products)
    gb.configure_pagination(paginationPageSize=10)
    gb.configure_side_bar()
    gb.configure_selection('single')
    gb.configure_column("quantity", headerName="Stock", editable=True)
    grid_options = gb.build()
    
    grid_response = AgGrid(
        products,
        gridOptions=grid_options,
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        theme="streamlit",
        update_mode='MODEL_CHANGED'
    )
    
    # Product Actions
    selected = grid_response['selected_rows']
    if selected:
        product = selected[0]
        with st.expander("Product Actions"):
            col1, col2 = st.columns(2)
            with col1:
                # Update stock
                new_quantity = st.number_input("Update Quantity", 
                                             value=product['quantity'],
                                             min_value=0)
                if st.button("Update Stock"):
                    with sqlite3.connect(DATABASE) as conn:
                        conn.execute("UPDATE products SET quantity = ? WHERE id = ?",
                                   (new_quantity, product['id']))
                        st.success("Stock updated!")
            with col2:
                # Generate barcode
                if st.button("Generate Barcode"):
                    barcode_path = generate_barcode(product['id'])
                    st.image(barcode_path)
                    os.remove(barcode_path)
    
    # Add New Product
    with st.expander("Add New Product"):
        with st.form("add_product_form"):
            name = st.text_input("Product Name")
            category = st.text_input("Category")
            quantity = st.number_input("Initial Stock", min_value=0)
            unit_price = st.number_input("Unit Price", min_value=0.0)
            alert_threshold = st.number_input("Low Stock Alert", min_value=0)
            
            if st.form_submit_button("Add Product"):
                try:
                    with sqlite3.connect(DATABASE) as conn:
                        conn.execute('''
                        INSERT INTO products 
                        (name, category, quantity, unit_price, alert_threshold)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (name, category, quantity, unit_price, alert_threshold))
                    st.success("Product added successfully!")
                except sqlite3.IntegrityError:
                    st.error("Product name already exists!")

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
    
    # Select Products
    selected_products = st.multiselect(
        "Select products to sell",
        options=products.to_dict('records'),
        format_func=lambda x: f"{x['name']} (₹{x['unit_price']} | Stock: {x['quantity']})"
    )
    
    # Create Sale Items
    sale_items = []
    for product in selected_products:
        col1, col2 = st.columns(2)
        with col1:
            qty = st.number_input(
                f"Quantity for {product['name']}",
                min_value=1,
                max_value=product['quantity'],
                value=1,
                key=f"qty_{product['id']}"
            )
        with col2:
            price = st.number_input(
                "Unit Price",
                value=product['unit_price'],
                min_value=0.0,
                key=f"price_{product['id']}"
            )
        sale_items.append({
            'product_id': product['id'],
            'qty': qty,
            'price': price,
            'total': qty * price
        })
    
    # Display Cart
    if sale_items:
        st.subheader("Sale Summary")
        cart_df = pd.DataFrame(sale_items)
        st.dataframe(cart_df[['product_id', 'qty', 'price', 'total']])
        
        total = cart_df['total'].sum()
        st.metric("Total Amount", f"₹{total:,.2f}")
        
        if st.button("Process Sale"):
            try:
                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    # Process each item
                    for item in sale_items:
                        # Update inventory
                        cursor.execute('''
                        UPDATE products 
                        SET quantity = quantity - ?
                        WHERE id = ?
                        ''', (item['qty'], item['product_id']))
                        
                        # Record sale
                        cursor.execute('''
                        INSERT INTO sales (product_id, quantity_sold, total_price)
                        VALUES (?, ?, ?)
                        ''', (item['product_id'], item['qty'], item['total']))
                    
                    st.success("Sale processed successfully!")
                    st.balloons()
                    
                    # Generate receipt
                    receipt = f"""
                    ╔══════════════════════════════╗
                    ║        SALES RECEIPT         ║
                    ╠══════════════════════════════╣
                    {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    
                    Items:
                    {cart_df.to_string(index=False)}
                    
                    Total: ₹{total:,.2f}
                    ╚══════════════════════════════╝
                    """
                    st.download_button(
                        label="Download Receipt",
                        data=receipt,
                        file_name="receipt.txt"
                    )
            except Exception as e:
                st.error(f"Error processing sale: {str(e)}")

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