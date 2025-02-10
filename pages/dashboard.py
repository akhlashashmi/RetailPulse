import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
from database import DATABASE, get_current_user_id, get_products, log_history

def show_dashboard():
    st.title("📊 Shop Dashboard")
    user_id = get_current_user_id()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_stock = get_products(user_id)['quantity'].sum()
        st.metric("Total Stock Value", f"₹{total_stock:,.2f}")
    with col2:
        low_stock = get_products(user_id)[get_products(user_id)['quantity'] <= get_products(user_id)['alert_threshold']]
        st.metric("Low Stock Items", len(low_stock), delta_color="inverse")
    with col3:
        total_sales = pd.read_sql("SELECT SUM(total_price) FROM sales WHERE user_id=?", 
                                 sqlite3.connect(DATABASE), params=(user_id,)).iloc[0,0] or 0
        st.metric("Total Sales", f"₹{total_sales:,.2f}")
    with col4:
        active_debts = (pd.read_sql("SELECT SUM(remaining_amount) FROM customer_debts WHERE status='active' AND user_id=?", 
                                  sqlite3.connect(DATABASE), params=(user_id,)).iloc[0,0] or 0) + \
                       (pd.read_sql("SELECT SUM(remaining_amount) FROM supplier_debts WHERE status='active' AND user_id=?", 
                                  sqlite3.connect(DATABASE), params=(user_id,)).iloc[0,0] or 0)
        st.metric("Active Debts", f"₹{active_debts:,.2f}")
    
    st.subheader("Sales Trend (Last 30 Days)")
    sales_data = pd.read_sql('''
    SELECT DATE(sale_date) as date, SUM(total_price) as total 
    FROM sales 
    WHERE sale_date >= DATE('now', '-30 days') AND user_id=?
    GROUP BY DATE(sale_date)
    ''', sqlite3.connect(DATABASE), params=(user_id,))
    if not sales_data.empty:
        fig = px.line(sales_data, x='date', y='total', labels={'total': 'Daily Sales'}, markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sales data available")
    
    # Log dashboard view (optional, for history tracking)
    log_history(user_id, "dashboard", None, "view", "Viewed dashboard")