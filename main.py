

import streamlit as st
from streamlit_option_menu import option_menu
from auth import login_page, create_account_page
from pages.dashboard import show_dashboard
from pages.inventory import manage_inventory
from pages.sales import manage_sales
from pages.debts import manage_debts
from pages.suppliers import manage_suppliers
from pages.customers import manage_customers
from pages.reports import generate_reports
from pages.history import manage_history
from pages.settings import manage_settings
from database import init_db

# Initialize database
init_db()

# Page configuration
st.set_page_config(page_title="Shop Manager Pro", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")

# Main screen with auth switch
if 'user' not in st.session_state:
    st.title("Welcome to Shop Manager Pro")
    auth_choice = st.radio("Choose an option:", ["Login", "Create Account"])
    
    if auth_choice == "Login":
        login_page()
    else:
        create_account_page()
else:
    # Sidebar navigation
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2331/2331966.png", width=100)
        st.markdown(f"**Logged in as:** {st.session_state.user['username']} ({st.session_state.user['role']})")
        menu = option_menu(
            menu_title="Main Menu",
            options=["Dashboard", "Inventory", "Sales", "Debts", "Customers", "Suppliers", "Reports", "History", "Settings", "Logout"],
            icons=["speedometer", "box", "cash", "person-rolodex", "person", "truck", "graph-up", "clock", "gear", "door-open"],
            default_index=0
        )
    
    # Route to selected page
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Inventory":
        manage_inventory()
    elif menu == "Sales":
        manage_sales()
    elif menu == "Debts":
        manage_debts()
    elif menu == "Customers":
        manage_customers()
    elif menu == "Suppliers":
        manage_suppliers()
    elif menu == "Reports":
        generate_reports()
    elif menu == "History":
        manage_history()
    elif menu == "Settings":
        manage_settings()
    elif menu == "Logout":
        del st.session_state.user
        st.rerun()