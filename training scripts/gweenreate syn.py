import mysql.connector
import random
from datetime import datetime, timedelta

print("--- Starting Synthetic Transaction Data Generation ---")

# --- DATABASE CONFIGURATION ---
# Use the same credentials as your app.py file
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '2580', # Use your MySQL password
    'database': 'library_system'
}

# --- GENERATION SETTINGS ---
NUMBER_OF_TRANSACTIONS = 300  # How many historical records to create
LATE_RETURN_PROBABILITY = 0.35 # 35% chance a book is returned late

try:
    print("Connecting to the database...")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # 1. Fetch existing users and books to ensure data integrity
    print("Fetching existing users and books from the database...")
    cursor.execute("SELECT user_id FROM users")
    users = [row['user_id'] for row in cursor.fetchall()]
    
    cursor.execute("SELECT book_id FROM books")
    books = [row['book_id'] for row in cursor.fetchall()]

    if not users or not books:
        print("\nCRITICAL ERROR: Your 'users' or 'books' table is empty. Please add some sample data first.")
        exit()

    print(f"Found {len(users)} users and {len(books)} books to use for generation.")

    # 2. Generate and Insert Synthetic Data
    print(f"Generating {NUMBER_OF_TRANSACTIONS} synthetic transaction records...")
    transactions_to_insert = []
    
    for i in range(NUMBER_OF_TRANSACTIONS):
        # Pick a random user and book
        user_id = random.choice(users)
        book_id = random.choice(books)
        
        # Generate realistic dates from the past year
        issue_date = datetime.now() - timedelta(days=random.randint(20, 365))
        due_date = issue_date + timedelta(days=14)
        
        # Decide if the return is late or on-time based on probability
        is_late = random.random() < LATE_RETURN_PROBABILITY
        
        if is_late:
            # Generate a return date that is after the due date
            return_date = due_date + timedelta(days=random.randint(1, 30))
        else:
            # Generate a return date that is before or on the due date
            return_date = issue_date + timedelta(days=random.randint(1, 14))
            
        transactions_to_insert.append((user_id, book_id, issue_date, due_date, return_date))

    # 3. Insert all generated records into the database in a single, efficient operation
    print("Inserting generated records into the 'transactions' table...")
    insert_query = "INSERT INTO transactions (user_id, book_id, issue_date, due_date, return_date) VALUES (%s, %s, %s, %s, %s)"
    cursor.executemany(insert_query, transactions_to_insert)
    conn.commit()

    print(f"\nSUCCESS! Successfully inserted {cursor.rowcount} new transaction records.")
    print("Your database is now ready for training the late return prediction model.")

except Exception as e:
    print(f"\nAn error occurred: {e}")

finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()