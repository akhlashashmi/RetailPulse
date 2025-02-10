import hashlib
import streamlit as st
import pandas as pd
import sqlite3
from database import DATABASE, get_current_user_id, log_history

def manage_settings():
    st.title("⚙️ Settings")
    user_id = get_current_user_id()
    
    if st.session_state.user['role'] != 'admin':
        st.warning("Only admins can access settings")
        return
    
    tab1, tab2 = st.tabs(["User Management", "Database"])
    
    with tab1:
        st.subheader("User Accounts")
        users = pd.read_sql("SELECT id, username, role FROM users", sqlite3.connect(DATABASE))
        st.dataframe(users)
        
        with st.expander("Create New User"):
            with st.form("create_user_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                role = st.selectbox("Role", ["admin", "staff"])
                if st.form_submit_button("Create User"):
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            conn.execute('''
                            INSERT INTO users (username, password, role)
                            VALUES (?, ?, ?)
                            ''', (username, hashlib.sha256(password.encode()).hexdigest(), role))
                            conn.commit()
                            log_history(user_id, "user", conn.lastrowid, "create", f"Created user: {username}")
                        st.success("User created!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists!")
        
        with st.expander("Delete User"):
            user_id_to_delete = st.number_input("User ID to delete", min_value=1)
            if st.button("Delete User"):
                with sqlite3.connect(DATABASE) as conn:
                    conn.execute("DELETE FROM users WHERE id = ?", (user_id_to_delete,))
                    conn.commit()
                    log_history(user_id, "user", user_id_to_delete, "delete", f"Deleted user ID: {user_id_to_delete}")
                st.success("User deleted!")
                st.rerun()
    
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
            st.success("Database restored!")
            log_history(user_id, "database", None, "restore", "Restored database backup")
            st.rerun()