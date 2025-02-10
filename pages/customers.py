import pandas as pd
import streamlit as st
import sqlite3
from database import DATABASE, get_current_user_id, log_history

def manage_customers():
    st.title("👤 Customer Management")
    user_id = get_current_user_id()
    
    # Add Customer
    with st.expander("Add New Customer"):
        with st.form("add_customer_form"):
            name = st.text_input("Customer Name")
            phone = st.text_input("Phone Number")
            address = st.text_area("Address")
            if st.form_submit_button("Add Customer"):
                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                    INSERT INTO customers (user_id, name, phone, address)
                    VALUES (?, ?, ?, ?)
                    ''', (user_id, name, phone, address))
                    conn.commit()
                    log_history(user_id, "customer", cursor.lastrowid, "create", f"Created customer: {name}")
                st.success("Customer added!")

    # Add Debt
    with st.expander("Add Customer Debt"):
        with st.form("new_customer_debt_form"):
            customers = pd.read_sql("SELECT id, name FROM customers WHERE user_id=?", sqlite3.connect(DATABASE), params=(user_id,))
            customer_options = {row['name']: row['id'] for index, row in customers.iterrows()}
            customer_name = st.selectbox("Select Customer", list(customer_options.keys()))
            amount = st.number_input("Debt Amount", min_value=0.0)
            description = st.text_input("Description")
            due_date = st.date_input("Due Date")
            if st.form_submit_button("Add Debt"):
                customer_id = customer_options[customer_name]
                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                    INSERT INTO customer_debts (user_id, customer_id, initial_amount, remaining_amount, description, due_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'active')
                    ''', (user_id, customer_id, amount, amount, description, due_date))
                    conn.commit()
                    log_history(user_id, "customer_debt", cursor.lastrowid, "create", f"Added debt for {customer_name}: ₹{amount}")
                st.success("Debt added!")

    # View Customers
    st.subheader("Customer List")
    customers = pd.read_sql("SELECT * FROM customers WHERE user_id=?", sqlite3.connect(DATABASE), params=(user_id,))
    if not customers.empty:
        st.dataframe(customers)
    else:
        st.info("No customers found.")
    
    # Customer History
    st.subheader("Customer History")
    customer_history = pd.read_sql("SELECT * FROM history WHERE user_id=? AND entity_type IN ('customer', 'customer_debt') ORDER BY timestamp DESC", 
                                 sqlite3.connect(DATABASE), params=(user_id,))
    if not customer_history.empty:
        st.dataframe(customer_history)
        if st.button("Export Customer History"):
            csv = customer_history.to_csv(index=False)
            st.download_button(label="Download CSV", data=csv, file_name="customer_history.csv", mime="text/csv")
            log_history(user_id, "customer", None, "export", "Exported customer history")
    else:
        st.info("No customer history available.")