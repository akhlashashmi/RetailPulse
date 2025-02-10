import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode
import pandas as pd
import sqlite3
from database import DATABASE, get_current_user_id, get_products, log_history
from io import BytesIO
import barcode
from barcode.writer import ImageWriter

def generate_barcode(product_id):
    barcode_class = barcode.get_barcode_class('ean13')
    barcode_instance = barcode_class(str(product_id).zfill(12), writer=ImageWriter())
    buffer = BytesIO()
    barcode_instance.write(buffer)
    buffer.seek(0)
    return buffer

def manage_inventory():
    st.title("📦 Inventory Management")
    user_id = get_current_user_id()
    
    # Search and Filter
    st.subheader("Filter Products")
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("Search by Name")
    with col2:
        category_filter = st.text_input("Filter by Category (leave blank for all)")
    
    # Bulk Operations
    with st.expander("Bulk Operations"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("CSV Import")
            uploaded_file = st.file_uploader("Upload products CSV", type="csv")
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    df['user_id'] = user_id
                    with sqlite3.connect(DATABASE) as conn:
                        df.to_sql('products', conn, if_exists='append', index=False)
                    log_history(user_id, "product", None, "bulk_import", f"Imported {len(df)} products")
                    st.success(f"Imported {len(df)} products!")
                except Exception as e:
                    st.error(f"Import error: {str(e)}")
        with col2:
            st.subheader("Export Data")
            if st.button("Export Inventory"):
                df = get_products(user_id)
                csv = df.to_csv(index=False)
                st.download_button(label="Download CSV", data=csv, file_name="inventory.csv", mime="text/csv")
                log_history(user_id, "product", None, "export", "Exported inventory")

    # Real-time Stock Alerts
    with st.expander("Stock Alerts"):
        products = get_products(user_id)
        low_stock = products[products['quantity'] <= products['alert_threshold']]
        if not low_stock.empty:
            st.warning(f"🚨 {len(low_stock)} items need restocking!")
            st.dataframe(low_stock[['name', 'quantity', 'alert_threshold']], use_container_width=True)
        else:
            st.success("All stock levels are satisfactory")

    # Product List with Enhanced UX
    st.subheader("Product List")
    products = get_products(user_id)
    if search_term:
        products = products[products['name'].str.contains(search_term, case=False, na=False)]
    if category_filter:
        products = products[products['category'].str.contains(category_filter, case=False, na=False)]
    
    if not products.empty:
        gb = GridOptionsBuilder.from_dataframe(products)
        gb.configure_pagination(paginationPageSize=10)
        gb.configure_side_bar()
        gb.configure_selection('single', use_checkbox=True)
        gb.configure_column("quantity", editable=True, headerName="Stock")
        grid_options = gb.build()
        
        grid_response = AgGrid(
            products,
            gridOptions=grid_options,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
            theme="streamlit",
            update_mode='MODEL_CHANGED',
            height=400
        )
        
        selected = grid_response['selected_rows']
        if isinstance(selected, list) and selected:
            product = selected[0]
            with st.container(border=True):
                st.subheader(f"Manage: {product['name']}")
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    with st.form(f"update_{product['id']}"):
                        new_qty = st.number_input("Update Stock", value=int(product['quantity']), min_value=0)
                        if st.form_submit_button("Update"):
                            with sqlite3.connect(DATABASE) as conn:
                                conn.execute("UPDATE products SET quantity = ?, last_restock = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?", 
                                            (new_qty, product['id'], user_id))
                            log_history(user_id, "product", product['id'], "update", f"Updated quantity to {new_qty}")
                            st.success("Stock updated!")
                            st.rerun()
                with col2:
                    if st.button("Generate Barcode", key=f"barcode_{product['id']}"):
                        barcode_buffer = generate_barcode(product['id'])
                        st.image(barcode_buffer)
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{product['id']}"):
                        with sqlite3.connect(DATABASE) as conn:
                            conn.execute("DELETE FROM products WHERE id = ? AND user_id = ?", (product['id'], user_id))
                        log_history(user_id, "product", product['id'], "delete", f"Deleted product: {product['name']}")
                        st.success("Product deleted!")
                        st.rerun()
    else:
        st.info("No products match your criteria.")

    # Add New Product
    with st.expander("Add New Product"):
        with st.form("add_product_form", clear_on_submit=True):
            cols = st.columns([2, 1, 1, 1])
            with cols[0]:
                name = st.text_input("Product Name")
                category = st.text_input("Category")
            with cols[1]:
                quantity = st.number_input("Initial Stock", min_value=0, step=10)
            with cols[2]:
                unit_price = st.number_input("Unit Price", min_value=0.0, step=0.5)
            with cols[3]:
                alert_threshold = st.number_input("Low Stock Alert", min_value=1, value=5)
            if st.form_submit_button("➕ Add Product"):
                if not name:
                    st.error("Product name is required!")
                else:
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO products (user_id, name, category, quantity, unit_price, alert_threshold)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (user_id, name, category, quantity, unit_price, alert_threshold))
                            conn.commit()
                            log_history(user_id, "product", cursor.lastrowid, "create", f"Created product: {name}")
                        st.success("Product added!")
                    except sqlite3.IntegrityError:
                        st.error("Product name already exists!")