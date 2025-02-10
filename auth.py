import streamlit as st
import sqlite3
import hashlib
from database import DATABASE, log_history

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, role="staff"):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
        ''', (username, hash_password(password), role))
        conn.commit()
        # Log history for user creation
        log_history(None, "user", cursor.lastrowid, "create", f"Created user: {username}")

def authenticate(username, password):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id, username, role FROM users 
        WHERE username = ? AND password = ?
        ''', (username, hash_password(password)))
        return cursor.fetchone()

def login_page():
    st.title("🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user = authenticate(username, password)
            if user:
                st.session_state.user = {"id": user[0], "username": user[1], "role": user[2]}
                st.rerun()
            else:
                st.error("Invalid credentials")

def create_account_page():
    st.title("🔐 Create Account")
    with st.form("create_account_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["staff", "admin"]) if 'user' in st.session_state and st.session_state.user['role'] == 'admin' else "staff"
        if st.form_submit_button("Create Account"):
            try:
                create_user(username, password, role)
                st.success("Account created! Please log in.")
            except sqlite3.IntegrityError:
                st.error("Username already exists")