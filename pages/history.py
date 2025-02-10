import sqlite3
import streamlit as st
import pandas as pd
from database import DATABASE, get_current_user_id

def manage_history():
    st.title("⏳ History")
    user_id = get_current_user_id()
    
    # Filter history by entity type
    entity_types = ["All", "product", "sale", "customer", "customer_debt", "supplier", "supplier_debt", "report"]
    entity_filter = st.selectbox("Filter by Entity", entity_types)
    
    query = "SELECT * FROM history WHERE user_id=? "
    params = [user_id]
    if entity_filter != "All":
        query += "AND entity_type=?"
        params.append(entity_filter)
    query += "ORDER BY timestamp DESC"
    
    history = pd.read_sql(query, sqlite3.connect(DATABASE), params=params)
    if not history.empty:
        st.dataframe(history)
        if st.button("Export History"):
            csv = history.to_csv(index=False)
            st.download_button(label="Download CSV", data=csv, file_name="history.csv", mime="text/csv")
    else:
        st.info("No history records found.")