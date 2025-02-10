import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from database import DATABASE, get_current_user_id, get_products, log_history

def generate_reports():
    st.title("📈 Reporting & Analytics")
    user_id = get_current_user_id()
    
    report_type = st.selectbox("Select Report Type", ["Sales Report", "Inventory Report", "Customer Debt Report", "Supplier Debt Report"])
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.date.today())
    
    if st.button("Generate Report"):
        if report_type == "Sales Report":
            sales_data = pd.read_sql(f'''
            SELECT products.name, SUM(sales.quantity_sold) as total_quantity, SUM(sales.total_price) as total_sales
            FROM sales
            JOIN products ON sales.product_id = products.id
            WHERE DATE(sales.sale_date) BETWEEN '{start_date}' AND '{end_date}' AND sales.user_id = ?
            GROUP BY products.name
            ''', sqlite3.connect(DATABASE), params=(user_id,))
            st.subheader("Sales Report")
            if not sales_data.empty:
                fig = px.bar(sales_data, x='name', y='total_sales', title="Product Sales Performance")
                st.plotly_chart(fig)
                st.dataframe(sales_data)
            else:
                st.warning("No sales data in selected period")
            log_history(user_id, "report", None, "generate", f"Generated {report_type}")
        
        elif report_type == "Inventory Report":
            inventory = get_products(user_id)
            st.subheader("Inventory Status")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Products", len(inventory))
            with col2:
                st.metric("Total Stock Value", f"₹{inventory['quantity'].sum():,.2f}")
            fig = px.pie(inventory, names='category', values='quantity', title="Stock Distribution by Category")
            st.plotly_chart(fig)
            log_history(user_id, "report", None, "generate", f"Generated {report_type}")
        
        elif report_type == "Customer Debt Report":
            debts = pd.read_sql(f'''
            SELECT c.name, cd.initial_amount, cd.remaining_amount, cd.due_date
            FROM customer_debts cd
            JOIN customers c ON cd.customer_id = c.id
            WHERE cd.status = 'active' AND cd.user_id = ? AND cd.due_date BETWEEN '{start_date}' AND '{end_date}'
            ''', sqlite3.connect(DATABASE), params=(user_id,))
            st.subheader("Active Customer Debts Report")
            if not debts.empty:
                st.dataframe(debts)
                total_debt = debts['remaining_amount'].sum()
                st.metric("Total Outstanding Debt", f"₹{total_debt:,.2f}")
            else:
                st.info("No active customer debts")
            log_history(user_id, "report", None, "generate", f"Generated {report_type}")
        
        elif report_type == "Supplier Debt Report":
            debts = pd.read_sql(f'''
            SELECT s.name, sd.initial_amount, sd.remaining_amount, sd.due_date
            FROM supplier_debts sd
            JOIN suppliers s ON sd.supplier_id = s.id
            WHERE sd.status = 'active' AND sd.user_id = ? AND sd.due_date BETWEEN '{start_date}' AND '{end_date}'
            ''', sqlite3.connect(DATABASE), params=(user_id,))
            st.subheader("Active Supplier Debts Report")
            if not debts.empty:
                st.dataframe(debts)
                total_debt = debts['remaining_amount'].sum()
                st.metric("Total Outstanding Debt", f"₹{total_debt:,.2f}")
            else:
                st.info("No active supplier debts")
            log_history(user_id, "report", None, "generate", f"Generated {report_type}")