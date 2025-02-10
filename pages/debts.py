import streamlit as st
import pandas as pd
import sqlite3
from database import DATABASE, get_current_user_id, log_history

def manage_debts():
    st.title("📝 Debt Management")
    user_id = get_current_user_id()
    
    tab1, tab2 = st.tabs(["Customer Debts", "Supplier Debts"])
    
    with tab1:
        st.subheader("Customer Debts (To Receive)")
        debts = pd.read_sql("SELECT * FROM customer_debts WHERE status='active' AND user_id=?", 
                           sqlite3.connect(DATABASE), params=(user_id,))
        if not debts.empty:
            st.dataframe(debts)
        else:
            st.info("No active customer debts")
        
        with st.form("customer_payment_form"):
            active_debts = pd.read_sql("SELECT id, customer_id, remaining_amount FROM customer_debts WHERE status='active' AND user_id=?", 
                                      sqlite3.connect(DATABASE), params=(user_id,))
            if not active_debts.empty:
                debt_options = {f"Debt ID {row['id']} (₹{row['remaining_amount']})": row['id'] for index, row in active_debts.iterrows()}
                selected_debt = st.selectbox("Select Debt to Pay", options=list(debt_options.keys()))
                debt_id = debt_options[selected_debt]
                max_amount = float(active_debts[active_debts['id'] == debt_id]['remaining_amount'].iloc[0])
                amount = st.number_input("Payment Amount", min_value=0.0, max_value=max_amount)
                payment_method = st.selectbox("Payment Method", ["Cash", "Card", "Online"])
                if st.form_submit_button("Record Payment"):
                    with sqlite3.connect(DATABASE) as conn:
                        conn.execute('''
                        INSERT INTO customer_debt_payments (user_id, debt_id, amount, payment_method)
                        VALUES (?, ?, ?, ?)
                        ''', (user_id, debt_id, amount, payment_method))
                        conn.execute('''
                        UPDATE customer_debts SET remaining_amount = remaining_amount - ? WHERE id = ? AND user_id = ?
                        ''', (amount, debt_id, user_id))
                        remaining = pd.read_sql("SELECT remaining_amount FROM customer_debts WHERE id=? AND user_id=?", 
                                               conn, params=(debt_id, user_id)).iloc[0,0]
                        if remaining <= 0:
                            conn.execute("UPDATE customer_debts SET status = 'paid' WHERE id = ? AND user_id = ?", (debt_id, user_id))
                        conn.commit()
                        log_history(user_id, "customer_debt", debt_id, "payment", f"Paid ₹{amount} on debt {debt_id}")
                    st.success("Payment recorded!")
    
    with tab2:
        st.subheader("Supplier Debts (To Pay)")
        debts = pd.read_sql("SELECT * FROM supplier_debts WHERE status='active' AND user_id=?", 
                           sqlite3.connect(DATABASE), params=(user_id,))
        if not debts.empty:
            st.dataframe(debts)
        else:
            st.info("No active supplier debts")
        
        with st.form("supplier_payment_form"):
            active_debts = pd.read_sql("SELECT id, supplier_id, remaining_amount FROM supplier_debts WHERE status='active' AND user_id=?", 
                                      sqlite3.connect(DATABASE), params=(user_id,))
            if not active_debts.empty:
                debt_options = {f"Debt ID {row['id']} (₹{row['remaining_amount']})": row['id'] for index, row in active_debts.iterrows()}
                selected_debt = st.selectbox("Select Debt to Pay", options=list(debt_options.keys()))
                debt_id = debt_options[selected_debt]
                max_amount = float(active_debts[active_debts['id'] == debt_id]['remaining_amount'].iloc[0])
                amount = st.number_input("Payment Amount", min_value=0.0, max_value=max_amount)
                payment_method = st.selectbox("Payment Method", ["Cash", "Card", "Online"])
                if st.form_submit_button("Record Payment"):
                    with sqlite3.connect(DATABASE) as conn:
                        conn.execute('''
                        INSERT INTO supplier_debt_payments (user_id, debt_id, amount, payment_method)
                        VALUES (?, ?, ?, ?)
                        ''', (user_id, debt_id, amount, payment_method))
                        conn.execute('''
                        UPDATE supplier_debts SET remaining_amount = remaining_amount - ? WHERE id = ? AND user_id = ?
                        ''', (amount, debt_id, user_id))
                        remaining = pd.read_sql("SELECT remaining_amount FROM supplier_debts WHERE id=? AND user_id=?", 
                                               conn, params=(debt_id, user_id)).iloc[0,0]
                        if remaining <= 0:
                            conn.execute("UPDATE supplier_debts SET status = 'paid' WHERE id = ? AND user_id = ?", (debt_id, user_id))
                        conn.commit()
                        log_history(user_id, "supplier_debt", debt_id, "payment", f"Paid ₹{amount} on debt {debt_id}")
                    st.success("Payment recorded!")
    
    # Debt History
    st.subheader("Debt History")
    customer_debt_payments = pd.read_sql("SELECT * FROM customer_debt_payments WHERE user_id=?", sqlite3.connect(DATABASE), params=(user_id,))
    supplier_debt_payments = pd.read_sql("SELECT * FROM supplier_debt_payments WHERE user_id=?", sqlite3.connect(DATABASE), params=(user_id,))
    if not customer_debt_payments.empty or not supplier_debt_payments.empty:
        debt_history = pd.concat([customer_debt_payments, supplier_debt_payments], ignore_index=True).sort_values('payment_date', ascending=False)
        st.dataframe(debt_history)
        if st.button("Export Debt History"):
            csv = debt_history.to_csv(index=False)
            st.download_button(label="Download CSV", data=csv, file_name="debt_history.csv", mime="text/csv")
            log_history(user_id, "debt", None, "export", "Exported debt history")
    else:
        st.info("No debt history available.")