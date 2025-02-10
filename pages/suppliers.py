import pandas as pd
import streamlit as st
import sqlite3
from database import DATABASE, get_current_user_id, log_history

def manage_suppliers():
    st.title("🚚 Supplier Management")
    user_id = get_current_user_id()
    
    # Add Supplier
    with st.expander("Add New Supplier"):
        with st.form("add_supplier_form"):
            name = st.text_input("Supplier Name")
            contact = st.text_input("Contact Person")
            email = st.text_input("Email")
            address = st.text_area("Address")
            if st.form_submit_button("Add Supplier"):
                try:
                    with sqlite3.connect(DATABASE) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                        INSERT INTO suppliers (user_id, name, contact, email, address)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (user_id, name, contact, email, address))
                        conn.commit()
                        log_history(user_id, "supplier", cursor.lastrowid, "create", f"Created supplier: {name}")
                    st.success("Supplier added!")
                except sqlite3.IntegrityError:
                    st.error("Supplier name already exists!")

    # Add Debt
    with st.expander("Add Supplier Debt"):
        with st.form("new_supplier_debt_form"):
            suppliers = pd.read_sql("SELECT id, name FROM suppliers WHERE user_id=?", sqlite3.connect(DATABASE), params=(user_id,))
            supplier_options = {row['name']: row['id'] for index, row in suppliers.iterrows()}
            supplier_name = st.selectbox("Select Supplier", list(supplier_options.keys()))
            amount = st.number_input("Debt Amount", min_value=0.0)
            description = st.text_input("Description")
            due_date = st.date_input("Due Date")
            if st.form_submit_button("Add Debt"):
                supplier_id = supplier_options[supplier_name]
                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                    INSERT INTO supplier_debts (user_id, supplier_id, initial_amount, remaining_amount, description, due_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'active')
                    ''', (user_id, supplier_id, amount, amount, description, due_date))
                    conn.commit()
                    log_history(user_id, "supplier_debt", cursor.lastrowid, "create", f"Added debt for {supplier_name}: ₹{amount}")
                st.success("Debt added!")

    # View Suppliers
    st.subheader("Supplier List")
    suppliers = pd.read_sql("SELECT * FROM suppliers WHERE user_id=?", sqlite3.connect(DATABASE), params=(user_id,))
    if not suppliers.empty:
        st.dataframe(suppliers)
    else:
        st.info("No suppliers found.")
    
    # Supplier History
    st.subheader("Supplier History")
    supplier_history = pd.read_sql("SELECT * FROM history WHERE user_id=? AND entity_type IN ('supplier', 'supplier_debt') ORDER BY timestamp DESC", 
                                 sqlite3.connect(DATABASE), params=(user_id,))
    if not supplier_history.empty:
        st.dataframe(supplier_history)
        if st.button("Export Supplier History"):
            csv = supplier_history.to_csv(index=False)
            st.download_button(label="Download CSV", data=csv, file_name="supplier_history.csv", mime="text/csv")
            log_history(user_id, "supplier", None, "export", "Exported supplier history")
    else:
        st.info("No supplier history available.")