import pandas as pd
import mysql.connector
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import os

print("--- Starting Late Return Prediction Model Training ---")

# --- DATABASE CONFIGURATION ---
# Use the same credentials as your app.py file
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '2580', # Use your MySQL password
    'database': 'library_system'
}

try:
    # 1. Fetch data from the database
    print("Connecting to the database and fetching transaction history...")
    conn = mysql.connector.connect(**db_config)
    # We only want transactions that have actually been completed (returned) to learn from them
    query = "SELECT * FROM transactions WHERE return_date IS NOT NULL"
    df = pd.read_sql(query, conn)
    conn.close()
    print(f"Successfully fetched {len(df)} completed transaction records.")

    if len(df) < 20: # We need a minimum amount of data to train a meaningful model
        print("Not enough historical data to train a model. Please run the synthetic data generator script first.")
        exit()

    # 2. Feature Engineering: Creating the inputs for our model
    print("Performing feature engineering...")
    # Convert date columns to pandas datetime objects
    df['issue_date'] = pd.to_datetime(df['issue_date'])
    df['due_date'] = pd.to_datetime(df['due_date'])
    df['return_date'] = pd.to_datetime(df['return_date'])

    # Create the target variable: 'is_late' (1 if it was returned late, 0 if on time)
    df['is_late'] = (df['return_date'] > df['due_date']).astype(int)
    
    # Create features (inputs) from the data
    df['loan_duration_days'] = (df['due_date'] - df['issue_date']).dt.days
    df['day_of_week_borrowed'] = df['issue_date'].dt.dayofweek # Monday=0, Sunday=6

    # In a more advanced model, you could add features like:
    # - A user's personal late return percentage
    # - A book's overall popularity or historical lateness

    features = ['loan_duration_days', 'day_of_week_borrowed']
    target = 'is_late'

    X = df[features]
    y = df[target]

    # 3. Split data and Train the Model
    print("Splitting data and training the RandomForestClassifier model...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # 4. Evaluate the Model (optional but good practice)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel training complete! Accuracy on test set: {accuracy:.2f}")

    # 5. Save the trained model and the list of features it expects
    print("Saving the trained model and feature list to files...")
    joblib.dump(model, 'late_return_model.joblib')
    joblib.dump(features, 'late_return_features.joblib')

    print("\nModel saved as 'late_return_model.joblib'")
    print("Feature list saved as 'late_return_features.joblib'")

except Exception as e:
    print(f"\nAn error occurred: {e}")