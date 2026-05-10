from flask import Flask, request, jsonify, render_template, session, Response, redirect, url_for
import mysql.connector
from datetime import datetime, timedelta
from fpdf import FPDF
from fpdf.enums import XPos, YPos 
from functools import wraps
import os
import requests 
import base64

from ml_models import (
    get_book_recommendations,
    get_general_recommendations,
    predict_late_return,
    get_chatbot_response
)

app = Flask(__name__)
app.secret_key = 'a_very_secret_and_secure_key_change_it'

# --- PAYPAL SANDBOX CONFIGURATION ---
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET")
PAYPAL_API_BASE = "https://api.sandbox.paypal.com" 

# --- DATABASE CONFIGURATION ---
# Change these credentials according to your local MySQL setup
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'admin',
    'database': 'library_system',
    'autocommit': True
}

# --- FINE CONFIGURATION IN USD ---
FINE_PER_DAY_USD = 0.10


def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return None

def get_paypal_access_token():
    try:
        auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = "grant_type=client_credentials"
        response = requests.post(f"{PAYPAL_API_BASE}/v1/oauth2/token", headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Error getting PayPal token: {e}")
        return None

# --- ADMIN AUTH DECORATOR ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return jsonify({"status": "error", "message": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- PDF GENERATION HELPER CLASS (No changes) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'Automated Library Assistant', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, 'E-Receipt', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    def add_receipt_details(self, data):
        def safe_encode(text):
            if text is None: return ''
            return str(text).encode('latin-1', 'replace').decode('latin-1')
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Transaction Details', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, f"Transaction ID: {data.get('transaction_id', 'N/A')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        issue_date = data.get('issue_date')
        issue_date_dt = datetime.fromisoformat(str(issue_date)) if issue_date else None
        if issue_date_dt:
            self.cell(0, 8, f"Issue Date: {issue_date_dt.strftime('%d %b %Y, %I:%M %p')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Issued To', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, f"Name: {safe_encode(data.get('user_name', ''))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 8, f"User ID: {safe_encode(data.get('user_id', ''))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Book Details', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, f"Title: {safe_encode(data.get('book_title', ''))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 8, f"Author: {safe_encode(data.get('book_author', ''))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 8, f"Book ID: {safe_encode(data.get('book_id', ''))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Important Dates', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', 'B', 11)
        due_date = data.get('due_date')
        due_date_dt = datetime.fromisoformat(str(due_date)) if due_date else None
        if due_date_dt:
            self.cell(0, 8, f"Due Date: {due_date_dt.strftime('%d %b %Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)
        self.set_font('Helvetica', 'I', 10)
        self.multi_cell(0, 8, f"Note: {safe_encode(data.get('late_return_warning', ''))}")
        self.ln(10)
        self.cell(0, 10, 'Thank you for using the Automated Library Assistant!', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)


@app.route('/')
def index():
    return render_template('index.html')


# --- RECEIPT PDF GENERATION (No changes) ---
@app.route('/api/receipt/pdf/<int:transaction_id>')
def generate_receipt_pdf(transaction_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        query = """SELECT t.transaction_id, t.issue_date, t.due_date,
                          b.book_id, b.title as book_title, b.author as book_author,
                          u.user_id, u.name as user_name
                   FROM transactions t
                   JOIN books b ON t.book_id = b.book_id
                   JOIN users u ON t.user_id = u.user_id
                   WHERE t.transaction_id = %s AND t.user_id = %s"""
        cursor.execute(query, (transaction_id, session['user_id']))
        data = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    if not data:
        return jsonify({"status": "error", "message": "Receipt not found or access denied"}), 404
    prediction = predict_late_return(data['user_id'], data['book_id'], data['issue_date'])
    data['late_return_warning'] = prediction.get('message', 'N/A')
    pdf = PDF()
    pdf.add_page()
    pdf.add_receipt_details(data)
    pdf_output = bytes(pdf.output()) 
    return Response(pdf_output, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment;filename=receipt_{transaction_id}.pdf'})


# --- PAYPAL PAYMENT ENDPOINTS (No changes) ---
@app.route('/api/paypal/create_order', methods=['POST'])
def paypal_create_order():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed."}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        user_id = session['user_id']
        today = datetime.now().date()
        cursor.execute("SELECT transaction_id, due_date, fine_paid_until FROM transactions WHERE user_id = %s AND return_date IS NULL", (user_id,))
        current_loans = cursor.fetchall()
        for loan in current_loans:
            due_date = loan['due_date'].date()
            if today > due_date:
                paid_until = loan.get('fine_paid_until')
                fine_start_date = due_date
                if paid_until and paid_until > fine_start_date:
                    fine_start_date = paid_until
                if today > fine_start_date:
                    days_late = (today - fine_start_date).days
                    current_fine = days_late * FINE_PER_DAY_USD
                    cursor.execute("UPDATE transactions SET fine_amount = %s, fine_status = 'Pending' WHERE transaction_id = %s", (current_fine, loan['transaction_id']))
        cursor.execute("SELECT SUM(fine_amount) as total_fine FROM transactions WHERE user_id = %s AND fine_status = 'Pending'", (user_id,))
        result = cursor.fetchone()
        amount_usd = result.get('total_fine') if result.get('total_fine') else 0
        if not amount_usd or amount_usd < 0.01:
            return jsonify({"error": "No pending fines found."}), 400
        cursor.execute("SELECT name, email FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        user_name = "Library User"
        user_email = f"{user_id.replace(' ', '').lower()}@library-dummy.com"
        if user:
            user_name = user.get('name', user_name)
            user_email = user.get('email', user_email)
        if not user_email: 
            user_email = f"{user_id.replace(' ', '').lower()}@library-dummy.com"
        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({"error": "Could not get PayPal access token."}), 500
        headers = { "Authorization": f"Bearer {access_token}", "Content-Type": "application/json", }
        payload = { "intent": "CAPTURE", "purchase_units": [{"amount": {"currency_code": "USD", "value": f"{amount_usd:.2f}"}, "description": "Library Fine Payment"}] }
        response = requests.post(f"{PAYPAL_API_BASE}/v2/checkout/orders", headers=headers, json=payload)
        response.raise_for_status()
        order_data = response.json()
        order_id = order_data["id"]
        cursor.execute("INSERT INTO payment_log (user_id, amount, payment_request_id, status) VALUES (%s, %s, %s, 'Pending')", (user_id, amount_usd, order_id))
        return jsonify({"id": order_id})
    except Exception as e:
        print(f"An unexpected error occurred in create_order: {e}") 
        return jsonify({"error": "An unexpected error occurred on the server.", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/paypal/capture_order', methods=['POST'])
def paypal_capture_order():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed."}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        data = request.get_json()
        order_id = data.get('orderID')
        cursor.execute("SELECT user_id FROM payment_log WHERE payment_request_id = %s AND status = 'Pending'", (order_id,))
        log_entry = cursor.fetchone()
        if not log_entry:
            print(f"Warning: Received callback for unknown or already processed order_id: {order_id}")
            return jsonify({"error": "Invalid or already processed order ID."}), 400
        user_id = log_entry['user_id']
        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({"error": "Could not get PayPal access token."}), 500
        headers = { "Authorization": f"Bearer {access_token}", "Content-Type": "application/json", }
        response = requests.post(f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture", headers=headers, json={})
        response.raise_for_status() 
        capture_data = response.json()
        if capture_data.get('status') == 'COMPLETED':
            payment_id = capture_data['purchase_units'][0]['payments']['captures'][0]['id']
            today_date = datetime.now().date()
            cursor.execute("UPDATE payment_log SET status = 'Paid', payment_id = %s WHERE payment_request_id = %s", (payment_id, order_id))
            cursor.execute("""
                UPDATE transactions 
                SET fine_status = NULL, 
                    fine_amount = 0.00,
                    fine_paid_until = %s
                WHERE user_id = %s AND fine_status = 'Pending'
            """, (today_date, user_id))
            conn.commit()
            return jsonify({"status": "success", "capture_data": capture_data})
        else:
            return jsonify({"error": "Payment was not completed.", "details": capture_data}), 400
    except Exception as e:
        print(f"CRITICAL ERROR during payment capture: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"PAYPAL ERROR DETAILS: {e.response.json()}")
            except:
                print(f"PAYPAL ERROR DETAILS (text): {e.response.text}")
        conn.rollback()
        return jsonify({"error": "An unexpected error occurred during capture.", "details": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# --- LOGIN / LOGOUT / AUTHORIZE (No changes) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user_id = data.get('userId') or data.get('user_id')
    password = data.get('password')
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, name, role FROM users WHERE user_id = %s AND password = %s AND is_active = TRUE", (user_id, password))
        user = cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Login DB error: {err}")
        user = None
    finally:
        cursor.close()
        conn.close()
    if user:
        session['user_id'] = user['user_id']
        session['user_name'] = user['name']
        session['user_role'] = user.get('role', 'user')
        return jsonify({"status": "success", "user": {"name": user['name'], "role": user.get('role', 'user')}})
    return jsonify({"status": "error", "message": "Invalid credentials or account inactive."}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success"})

# --- LOGIN / LOGOUT / AUTHORIZE ---
# ... (your other functions) ...
@app.route('/api/user/deauthorize', methods=['POST'])
def deauthorize():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    
    cursor = conn.cursor()
    try:
        # Set the auth_timestamp to NULL to invalidate it
        cursor.execute("UPDATE users SET auth_timestamp = NULL WHERE user_id = %s", (session['user_id'],))
        conn.commit()
        return jsonify({"status": "success", "message": "Authorization invalidated."})
    except mysql.connector.Error as err:
        print(f"Deauthorize DB error: {err}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/authorize', methods=['POST'])
def authorize():
    data = request.get_json()
    rfid_uid = data.get('rfid_uid')
    if not rfid_uid:
        return jsonify({"status": "error", "message": "No RFID UID provided"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # **MODIFIED**: We now search for the user by RFID to get their name
        cursor.execute("SELECT user_id, name, is_active FROM users WHERE rfid_uid = %s", (rfid_uid,))
        user = cursor.fetchone()

        if not user:
            print(f"Auth Error: RFID UID {rfid_uid} not found in database.")
            # Send a clear error message back
            return jsonify({"status": "error", "message": "RFID Not Found"}), 404

        if not user['is_active']:
            print(f"Auth Error: User {user['name']} account is inactive.")
            return jsonify({"status": "error", "message": "Account Inactive"}), 403

        # User is valid, update their timestamp
        cursor.execute("UPDATE users SET auth_timestamp = NOW() WHERE rfid_uid = %s", (rfid_uid,))
        conn.commit()
        
        # **MODIFIED**: Send a success response with the user's name
        return jsonify({
            "status": "success", 
            "message": "Authorization successful",
            "user_name": user['name']
        })

    except mysql.connector.Error as err:
        print(f"Authorize DB error: {err}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

# ... (rest of your 5_app.py file) ...
    #return jsonify({"status": "success", "message": message})

@app.route('/api/user/status', methods=['GET'])
def user_status():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        query = """SELECT user_id FROM users
                   WHERE user_id = %s
                   AND auth_timestamp IS NOT NULL
                   AND auth_timestamp > (NOW() - INTERVAL 2 MINUTE)"""
        cursor.execute(query, (user_id,))
        authorized_user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    return jsonify({"authorized": True}) if authorized_user else jsonify({"authorized": False})


# --- USER DASHBOARD (No changes) ---
# --- USER DASHBOARD ---
@app.route('/api/user/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    user_id = session['user_id']
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # **MODIFIED**: Added b.`Image-URL-M` as image_url
        current_query = """SELECT b.title, b.author, t.issue_date, t.due_date, b.book_id,
                                  t.fine_status, t.fine_paid_until, b.`Image-URL-M` as image_url
                           FROM transactions t
                           JOIN books b ON t.book_id = b.book_id
                           WHERE t.user_id = %s AND t.return_date IS NULL
                           ORDER BY t.issue_date DESC"""
        cursor.execute(current_query, (user_id,))
        current_books = cursor.fetchall()

        current_fine_total = 0.0
        today = datetime.now().date()
        
        for book in current_books:
            try:
                prediction_result = predict_late_return(user_id, book['book_id'], book['issue_date'])
                book['late_prediction_percent'] = prediction_result.get('prob_percent', 0)
            except Exception as e:
                print(f"Prediction error for user {user_id}, book {book.get('book_id')}: {e}")
                book['late_prediction_percent'] = 0
            
            due_date = book['due_date'].date()
            fine_status = book.get('fine_status')
            paid_until = book.get('fine_paid_until')

            book['is_overdue'] = today > due_date
            book['current_fine'] = 0.0
            book['days_late'] = (today - due_date).days if today > due_date else 0
            
            if book['is_overdue']:
                if fine_status == 'Paid':
                    book['current_fine'] = 0.0
                
                elif paid_until: 
                    if today > paid_until:
                        days_late_since_payment = (today - paid_until).days
                        fine = days_late_since_payment * FINE_PER_DAY_USD
                        if fine_status != 'Pending':
                            current_fine_total += fine
                        book['current_fine'] = fine
                    else:
                        book['current_fine'] = 0.0
                
                else: 
                    days_late = (today - due_date).days
                    fine = days_late * FINE_PER_DAY_USD
                    if fine_status != 'Pending':
                        current_fine_total += fine
                    book['current_fine'] = fine


        history_query = """SELECT b.title, b.author, t.issue_date, t.return_date, b.book_id, b.`Image-URL-M` as image_url
                           FROM transactions t
                           JOIN books b ON t.book_id = b.book_id
                           WHERE t.user_id = %s AND t.return_date IS NOT NULL
                           ORDER BY t.return_date DESC"""
        cursor.execute(history_query, (user_id,))
        history_books = cursor.fetchall()
        
        cursor.execute("SELECT SUM(fine_amount) as pending_fine FROM transactions WHERE user_id = %s AND fine_status = 'Pending'", (user_id,))
        fine_result = cursor.fetchone()
        
        pending_fine_total = float(fine_result.get('pending_fine')) if fine_result.get('pending_fine') else 0.0

        total_fine = float(current_fine_total) + float(pending_fine_total)

        def process_books(book_list):
            for book in book_list:
                for key, value in list(book.items()):
                    if isinstance(value, datetime):
                        book[key] = value.isoformat()
            return book_list

        return jsonify({
            "status": "success",
            "current_books": process_books(current_books),
            "history_books": process_books(history_books),
            "total_fine": total_fine
        })
    except Exception as e:
        print(f"Error in dashboard function: {e}") 
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500
    finally:
        cursor.close()
        conn.close()


# --- TRANSACTION HANDLER (No changes) ---
# --- TRANSACTION HANDLER ---
# --- TRANSACTION HANDLER ---
def perform_transaction(book_id, user_id, action):
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "DB connection failed."}
    cursor = conn.cursor(dictionary=True)
    try:
        auth_query = """SELECT user_id FROM users WHERE user_id = %s
                        AND auth_timestamp IS NOT NULL
                        AND auth_timestamp > (NOW() - INTERVAL 2 MINUTE)"""
        cursor.execute(auth_query, (user_id,))
        if not cursor.fetchone():
            return {"status": "error", "message": "Authorization expired. Please scan your card again."}
        cursor.execute("UPDATE users SET auth_timestamp = NULL WHERE user_id = %s", (user_id,))
        
        if action == 'borrow':
            
            # ** THIS IS THE NEW CHECK **
            # 1. Count current active loans for the user
            cursor.execute("SELECT COUNT(*) as loan_count FROM transactions WHERE user_id = %s AND return_date IS NULL", (user_id,))
            loan_count_result = cursor.fetchone()
            active_loans = loan_count_result.get('loan_count') or 0
            
            if active_loans >= 2:
                return {"status": "error", "message": f"Cannot borrow. You already have {active_loans} books on loan. Please return a book first."}
            # ** END OF NEW CHECK **

            # 2. Check for pending fines
            cursor.execute("SELECT SUM(fine_amount) as total_fine FROM transactions WHERE user_id = %s AND fine_status = 'Pending'", (user_id,))
            fine_result = cursor.fetchone()
            pending_fine = fine_result.get('total_fine') or 0 
            if pending_fine > 0:
                return {"status": "error", "message": f"Cannot borrow. You have an outstanding fine of ${pending_fine:.2f}. Please pay it first."}
            
            # 3. Check for *currently overdue* books
            today = datetime.now().date()
            cursor.execute("SELECT COUNT(*) as overdue_count FROM transactions WHERE user_id = %s AND return_date IS NULL AND due_date < %s", (user_id, today))
            overdue_result = cursor.fetchone()
            overdue_count = overdue_result.get('overdue_count') or 0
            if overdue_count > 0:
                 return {"status": "error", "message": f"Cannot borrow. You have {overdue_count} overdue book(s). Please return them or pay the fine."}

            # 4. Proceed with borrowing
            cursor.execute("SELECT title, author, status FROM books WHERE book_id = %s", (book_id,))
            book = cursor.fetchone()
            if not book or book.get('status') == 'Issued':
                return {"status": "error", "message": "Book is unavailable or does not exist."}
            
            cursor.execute("UPDATE books SET status = 'Issued' WHERE book_id = %s", (book_id,))
            issue_date = datetime.now()
            due_date = issue_date + timedelta(days=14)
            insert_query = """INSERT INTO transactions (user_id, book_id, issue_date, due_date)
                              VALUES (%s, %s, %s, %s)"""
            cursor.execute(insert_query, (user_id, book_id, issue_date, due_date))
            conn.commit()
            transaction_id = cursor.lastrowid
            prediction = predict_late_return(user_id, book_id, issue_date)
            return { "status": "success", "message": "Book issued successfully!", "transaction_id": transaction_id, "receipt_url": f"/api/receipt/pdf/{transaction_id}", "book": {"title": book['title'], "author": book['author']}, "receipt": { "book_id": book_id, "user_id": user_id, "issue_date": issue_date.strftime('%Y-%m-%d %H:%M:%S'), "due_date": due_date.strftime('%Y-%m-%d %H:%M:%S'), "late_return_warning": prediction.get('message', '') } }
        
        elif action == 'return':
            cursor.execute("SELECT transaction_id, due_date, fine_paid_until, fine_status FROM transactions WHERE user_id = %s AND book_id = %s AND return_date IS NULL", (user_id, book_id))
            transaction = cursor.fetchone()
            if not transaction:
                return {"status": "error", "message": "No active loan found for this book and user."}
            fine_amount = 0.00
            fine_status = 'Waived' 
            fine_message = ""
            today = datetime.now().date()
            due_date = transaction['due_date'].date()
            paid_until = transaction.get('fine_paid_until')
            old_fine_status = transaction.get('fine_status')
            if today > due_date:
                fine_start_date = due_date
                if paid_until and paid_until >= fine_start_date:
                    fine_start_date = paid_until
                days_late = 0
                if today > fine_start_date:
                    days_late = (today - fine_start_date).days
                if days_late > 0:
                    fine_amount = days_late * FINE_PER_DAY_USD
                    fine_status = 'Pending'
                    fine_message = f" Book returned {days_late} day(s) after last due date. A final fine of ${fine_amount:.2f} has been added."
                if old_fine_status == 'Pending':
                    cursor.execute("SELECT fine_amount FROM transactions WHERE transaction_id = %s", (transaction['transaction_id'],))
                    pending_fine_result = cursor.fetchone()
                    pending_fine = pending_fine_result.get('fine_amount') or 0.0
                    fine_amount = pending_fine
                    fine_status = 'Pending'
                    fine_message = f" Book returned. A total pending fine of ${fine_amount:.2f} is on your account."
            cursor.execute("""
                UPDATE transactions 
                SET return_date = NOW(), 
                    fine_amount = %s,
                    fine_status = %s,
                    fine_paid_until = NULL 
                WHERE transaction_id = %s
            """, (fine_amount, fine_status, transaction['transaction_id']))
            cursor.execute("UPDATE books SET status = 'Available' WHERE book_id = %s", (book_id,))
            conn.commit()
            return {"status": "success", "message": f"Book returned successfully!{fine_message}"}
        
        return {"status": "error", "message": "Invalid action."}
    except mysql.connector.Error as err:
        print(f"Transaction DB error: {err}")
        return {"status": "error", "message": "Database error during transaction."}
    finally:
        cursor.close()
        conn.close()

@app.route('/api/book/borrow', methods=['POST'])
def borrow_book():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    
    # **THIS IS THE FIX**
    try:
        data = request.get_json()
        if not data or 'bookId' not in data:
            return jsonify({"status": "error", "message": "Book ID is missing."}), 400
            
        book_id = data.get('bookId')
        user_id = session['user_id']
        result = perform_transaction(book_id, user_id, 'borrow')
        return jsonify(result), 400 if result['status'] == 'error' else 200
    
    except Exception as e:
        print(f"Error in borrow_book: {e}")
        return jsonify({"status": "error", "message": "An internal server error or bad request occurred."}), 500
    # **END OF FIX**

@app.route('/api/book/return', methods=['POST'])
def return_book():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    
    # **THIS IS THE FIX**
    try:
        data = request.get_json()
        if not data or 'bookId' not in data:
            return jsonify({"status": "error", "message": "Book ID is missing."}), 400
            
        book_id = data.get('bookId')
        user_id = session['user_id']
        result = perform_transaction(book_id, user_id, 'return')
        return jsonify(result), 400 if result['status'] == 'error' else 200

    except Exception as e:
        print(f"Error in return_book: {e}")
        return jsonify({"status": "error", "message": "An internal server error or bad request occurred."}), 500
    # **END OF FIX**

# --- RECOMMENDATIONS (No changes) ---
@app.route('/api/recommendations/<book_id>', methods=['GET'])
def recommendations(book_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed."}), 500
    user_id = session['user_id']
    try:
        recs = get_book_recommendations(user_id, book_id, conn)
    except Exception as e:
        print(f"Personalized recommendations error: {e}")
        try:
            recs = get_general_recommendations(conn, user_id)
        except Exception as e2:
            print(f"General recommendations error: {e2}")
            recs = []
    finally:
        conn.close()
    return jsonify({"status": "success", "recommendations": recs})


# --- CHATBOT (No changes) ---
@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    message = request.get_json().get('message')
    conn = get_db_connection()
    if not conn:
        return jsonify({"response": "Sorry, I can't connect to the database right now."})
    try:
        response = get_chatbot_response(message, conn)
    except Exception as e:
        print(f"Chatbot error: {e}")
        response = "Sorry, something went wrong while processing your message."
    finally:
        conn.close()
    return jsonify({"response": response})


# --- ADMIN: DASHBOARD DATA (No changes) ---
# --- ADMIN: DASHBOARD DATA (due alerts + all borrowed) ---
@app.route('/api/admin/dashboard_data', methods=['GET'])
@admin_required
def admin_dashboard_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # **THIS IS THE FIX**
        # The old query only looked for books due in the future.
        # This new query finds all books that are *already overdue* OR *due in the next 2 days*.
        due_alert_query = """
            SELECT b.title, u.name as user_name, t.issue_date, t.due_date
            FROM transactions t
            JOIN books b ON t.book_id = b.book_id
            JOIN users u ON t.user_id = u.user_id
            WHERE t.return_date IS NULL 
              AND t.due_date <= DATE_ADD(CURDATE(), INTERVAL 2 DAY)
            ORDER BY t.due_date ASC;
        """
        # **END OF FIX**
        
        cursor.execute(due_alert_query)
        due_date_alerts = cursor.fetchall()

        all_borrowed_query = """
            SELECT b.title, u.name as user_name, t.issue_date, t.due_date, t.user_id, t.book_id
            FROM transactions t
            JOIN books b ON t.book_id = b.book_id
            JOIN users u ON t.user_id = u.user_id
            WHERE t.return_date IS NULL
            ORDER BY t.due_date ASC;
        """
        cursor.execute(all_borrowed_query)
        all_borrowed_books = cursor.fetchall()

        def process_dates(book_list):
            for book in book_list:
                for key, value in list(book.items()):
                    if isinstance(value, datetime):
                        book[key] = value.isoformat()
            return book_list

        return jsonify({
            "status": "success",
            "due_date_alerts": process_dates(due_date_alerts),
            "all_borrowed_books": process_dates(all_borrowed_books)
        })
    except Exception as e:
        print(f"Error in admin_dashboard_data function: {e}")
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500
    finally:
        cursor.close()
        conn.close()


# --- ADMIN: Add Book (No changes) ---
@app.route('/api/admin/add_book', methods=['POST'])
@admin_required
def add_book():
    data = request.get_json()
    required = ['book_id', 'title', 'author']
    if not all(k in data for k in required):
        return jsonify({"status": "error", "message": "Missing book_id/title/author"}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO books (book_id, title, author, status) VALUES (%s, %s, %s, 'Available')",
                       (data['book_id'], data['title'], data['author']))
        conn.commit()
        return jsonify({"status": "success", "message": "Book added successfully!"})
    except mysql.connector.Error as err:
        print(f"Add book error: {err}")
        return jsonify({"status": "error", "message": f"Database Error: {err}"}), 400
    finally:
        cursor.close()
        conn.close()


# --- ADMIN: Add User (No changes) ---
@app.route('/api/admin/add_user', methods=['POST'])
@admin_required
def add_user():
    data = request.get_json()
    required = ['user_id', 'name', 'password', 'email']
    if not all(k in data for k in required):
        return jsonify({"status": "error", "message": "Missing user_id, name, password, or email"}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (user_id, name, password, rfid_uid, role, email) VALUES (%s, %s, %s, %s, %s, %s)",
                       (data['user_id'], data['name'], data['password'], data.get('rfid_uid'), data.get('role', 'user'), data.get('email')))
        conn.commit()
        return jsonify({"status": "success", "message": "User added successfully!"})
    except mysql.connector.Error as err:
        print(f"Add user error: {err}")
        return jsonify({"status": "error", "message": f"Database Error: {err}"}), 400
    finally:
        cursor.close()
        conn.close()


# --- ADMIN: Remove User (No changes) ---
@app.route('/api/admin/remove_user', methods=['POST'])
@admin_required
def remove_user():
    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "User ID is required"}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor(dictionary=True) 
    try:
        cursor.execute("SELECT COUNT(*) as loan_count FROM transactions WHERE user_id = %s AND return_date IS NULL", (user_id,))
        loans = cursor.fetchone()
        if loans and loans['loan_count'] > 0:
            return jsonify({"status": "error", "message": f"Cannot deactivate user. They have {loans['loan_count']} active loan(s)."}), 400
        cursor.execute("SELECT SUM(fine_amount) as total_fine FROM transactions WHERE user_id = %s AND fine_status = 'Pending'", (user_id,))
        fines = cursor.fetchone()
        if fines and fines['total_fine'] and fines['total_fine'] > 0:
            return jsonify({"status": "error", "message": f"Cannot deactivate user. They have a pending fine of ${fines['total_fine']:.2f}."}), 400
        cursor.execute("UPDATE users SET is_active = FALSE WHERE user_id = %s", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"status": "error", "message": "User not found."}), 404
        return jsonify({"status": "success", "message": f"User {user_id} has been deactivated."})
    except mysql.connector.Error as err:
        print(f"Remove user error: {err}")
        return jsonify({"status": "error", "message": f"Database Error: {err}"}), 400
    finally:
        cursor.close()
        conn.close()


# --- ADMIN: Search Book (No changes) ---
@app.route('/api/admin/search_book', methods=['POST'])
@admin_required
def search_book():
    data = request.get_json()
    search_term = data.get('search_term', '')
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT book_id, title, author, status FROM books WHERE title LIKE %s OR author LIKE %s",
                       (f"%{search_term}%", f"%{search_term}%"))
        books = cursor.fetchall()
        return jsonify({"status": "success", "books": books})
    except mysql.connector.Error as err:
        print(f"Search book error: {err}")
        return jsonify({"status": "error", "message": f"Database Error: {err}"}), 400
    finally:
        cursor.close()
        conn.close()


# --- ADMIN: Reissue RFID (No changes) ---
@app.route('/api/admin/reissue_rfid', methods=['POST'])
@admin_required
def reissue_rfid():
    data = request.get_json()
    user_id = data.get('user_id')
    name = data.get('name')
    new_rfid = data.get('new_rfid')
    if not user_id or not name or not new_rfid:
        return jsonify({"status": "error", "message": "Missing user_id, name or new_rfid"}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "DB connection failed."}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s AND name = %s", (user_id, name))
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "error", "message": "User ID and Name do not match."}), 404
        cursor.execute("UPDATE users SET rfid_uid = %s WHERE user_id = %s", (new_rfid, user_id))
        conn.commit()
        return jsonify({"status": "success", "message": f"RFID for user {user_id} updated successfully!"})
    except mysql.connector.Error as err:
        print(f"Reissue RFID error: {err}")
        return jsonify({"status": "error", "message": f"Database Error: {err}"}), 400
    finally:
        cursor.close()
        conn.close()


# --- **NEW**: PASSWORD MANAGEMENT ENDPOINTS ---

@app.route('/api/user/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    
    data = request.get_json()
    user_id = session['user_id']
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({"status": "error", "message": "Old and new passwords are required."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed."}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # First, verify the old password is correct
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s AND password = %s", (user_id, old_password))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "Incorrect old password."}), 403

        # If correct, update to the new password
        cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (new_password, user_id))
        conn.commit()
        
        return jsonify({"status": "success", "message": "Password updated successfully!"})

    except Exception as e:
        print(f"Error in change_password: {e}")
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    user_id = data.get('user_id')
    email = data.get('email')
    new_password = data.get('new_password')

    if not user_id or not email or not new_password:
        return jsonify({"status": "error", "message": "User ID, email, and new password are required."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed."}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Verify that the User ID and Email match an existing user
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s AND email = %s AND is_active = TRUE", (user_id, email))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "User ID and Email do not match. Please check your details."}), 404

        # If they match, update the password
        cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (new_password, user_id))
        conn.commit()
        
        return jsonify({"status": "success", "message": "Password has been reset successfully! You can now log in."})

    except Exception as e:
        print(f"Error in forgot_password: {e}")
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)