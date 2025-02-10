import pandas as pd
import streamlit as st
import sqlite3
import datetime
from database import DATABASE, get_current_user_id, get_products, log_history

def generate_receipt(sale_items, total, customer_name):
    receipt = f"Shop Manager Pro Receipt\nDate: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    if customer_name:
        receipt += f"Customer: {customer_name}\n"
    receipt += "-" * 40 + "\nItem          Qty    Price    Total\n"
    for item in sale_items:
        name = pd.read_sql("SELECT name FROM products WHERE id=?", sqlite3.connect(DATABASE), params=(item['product_id'],)).iloc[0]['name']
        receipt += f"{name:<12} {item['qty']:<6} {item['price']:<8.2f} {item['total']:.2f}\n"
    receipt += "-" * 40 + "\nTotal Amount: ₹{total:.2f}\n"
    return receipt

def manage_sales():
    st.title("💵 Sales Processing")
    user_id = get_current_user_id()
    
    products = get_products(user_id)
    if products.empty:
        st.warning("No products available for sale")
        return
    
    with st.container(border=True):
        st.subheader("New Sale Transaction")
        selected_products = st.multiselect(
            "Select products to sell",
            options=products.to_dict('records'),
            format_func=lambda x: f"{x['name']} (₹{x['unit_price']} | Stock: {x['quantity']})",
            key="sale_products"
        )
        
        sale_items = []
        for idx, product in enumerate(selected_products):
            with st.container(border=True):
                cols = st.columns([1, 2, 1])
                with cols[0]:
                    st.markdown(f"**{product['name']}**")
                with cols[1]:
                    qty = st.slider("Quantity", 1, product['quantity'], key=f"qty_{product['id']}")
                with cols[2]:
                    price = st.number_input("Price", value=product['unit_price'], min_value=0.0, key=f"price_{product['id']}", step=0.5)
                sale_items.append({'product_id': product['id'], 'qty': qty, 'price': price, 'total': qty * price})

        if sale_items:
            total = sum(item['total'] for item in sale_items)
            st.markdown(f"### Total Amount: ₹{total:,.2f}")
            cols = st.columns([3, 1])
            with cols[0]:
                customer_name = st.text_input("Customer Name (Optional)")
            with cols[1]:
                if st.button("💳 Process Sale", type="primary"):
                    try:
                        with sqlite3.connect(DATABASE) as conn:
                            cursor = conn.cursor()
                            for item in sale_items:
                                cursor.execute('''
                                    UPDATE products SET quantity = quantity - ? WHERE id = ? AND user_id = ?
                                ''', (item['qty'], item['product_id'], user_id))
                                cursor.execute('''
                                    INSERT INTO sales (user_id, product_id, quantity_sold, total_price)
                                    VALUES (?, ?, ?, ?)
                                ''', (user_id, item['product_id'], item['qty'], item['total']))
                            conn.commit()
                            sale_id = cursor.lastrowid
                            log_history(user_id, "sale", sale_id, "create", f"Sale: {total} for {len(sale_items)} items")
                        st.success("Sale processed!")
                        st.balloons()
                        receipt = generate_receipt(sale_items, total, customer_name)
                        st.download_button(label="📄 Download Receipt", data=receipt, file_name=f"receipt_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt", mime="text/plain")
                    except Exception as e:
                        st.error(f"Transaction failed: {str(e)}")
    
    # Sales/Transaction History
    st.subheader("Sales History")
    sales = pd.read_sql("SELECT * FROM sales WHERE user_id=? ORDER BY sale_date DESC", sqlite3.connect(DATABASE), params=(user_id,))
    if not sales.empty:
        st.dataframe(sales)
        if st.button("Export Sales History"):
            csv = sales.to_csv(index=False)
            st.download_button(label="Download CSV", data=csv, file_name="sales_history.csv", mime="text/csv")
            log_history(user_id, "sale", None, "export", "Exported sales history")
    else:
        st.info("No sales history available.")