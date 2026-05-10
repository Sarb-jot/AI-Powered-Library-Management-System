import joblib
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import difflib
from datetime import datetime, timedelta
import os
import google.generativeai as genai

# --- Model Loading ---
try:
    print("Loading all recommender and prediction models...")
    # --- Recommender System Models ---
    book_embeddings = joblib.load('content_embeddings.joblib')
    content_df_hf = joblib.load('content_dataframe_hf.joblib')
    collaborative_model = joblib.load('collaborative_model.joblib')
    collaborative_pivot = joblib.load('collaborative_pivot_table.joblib')
    RECOMMENDER_READY = True
    print("Recommender models loaded successfully.")

    # --- LATE RETURN MODEL LOADING ---
    late_return_model = joblib.load('late_return_model.joblib')
    late_return_features = joblib.load('late_return_features.joblib')
    LATE_MODEL_READY = True
    print("Late return prediction model loaded successfully.")

except FileNotFoundError as e:
    print(f"CRITICAL ERROR: One or more model files not found: {e}. Please run all training scripts.")
    RECOMMENDER_READY = False
    LATE_MODEL_READY = False

# --- Gemini Model Configuration ---
try:
    # IMPORTANT: Your API key is loaded from an environment variable for security.
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY environment variable not found. General knowledge questions will fail.")
        GEMINI_READY = False
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        GEMINI_READY = True
        print("Gemini model configured successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not configure Gemini model: {e}")
    GEMINI_READY = False


def _get_user_history(db_connection, user_id):
    """Helper function to get all book titles a user has ever borrowed."""
    try:
        cursor = db_connection.cursor(dictionary=True)
        query = "SELECT DISTINCT b.title FROM transactions t JOIN books b ON t.book_id = b.book_id WHERE t.user_id = %s"
        cursor.execute(query, (user_id,))
        history = {row['title'] for row in cursor.fetchall()}
        cursor.close()
        return history
    except Exception:
        return set()


def get_general_recommendations(db_connection, user_id):
    """
    Fetches the most borrowed books. If filtering out already-read books results
    in an empty list, it returns the original popular books list.
    """
    try:
        user_history = _get_user_history(db_connection, user_id)
        cursor = db_connection.cursor(dictionary=True)
        query = "SELECT b.title, b.author, b.book_id, b.`Image-URL-M` as image_url FROM transactions t JOIN books b ON t.book_id = b.book_id GROUP BY t.book_id ORDER BY COUNT(t.book_id) DESC LIMIT 20;"
        cursor.execute(query)
        popular_books = cursor.fetchall()
        cursor.close()

        filtered_popular = [book for book in popular_books if book['title'] not in user_history]
        
        if not filtered_popular and popular_books:
            print("DEBUG: Filtering removed all popular books. Returning original popular list as fallback.")
            return popular_books[:5]

        return filtered_popular[:5]
    except Exception as e:
        print(f"Could not fetch general recommendations: {e}")
        return []


def get_book_recommendations(user_id, book_id, db_connection):
    if not RECOMMENDER_READY: return []
    try:
        user_history = _get_user_history(db_connection, user_id)
        cursor = db_connection.cursor(dictionary=True)
        
        seed_title = None
        if book_id != 'default':
            cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
            live_book = cursor.fetchone()
            if live_book: seed_title = live_book['title']
        else:
            cursor.execute("SELECT b.title FROM transactions t JOIN books b ON t.book_id = b.book_id WHERE t.user_id = %s ORDER BY t.return_date DESC, t.issue_date DESC LIMIT 1", (user_id,))
            last_book = cursor.fetchone()
            if last_book: seed_title = last_book['title']
        
        cursor.close()
        if not seed_title: return []
        
        all_collab_titles = list(collaborative_pivot.index)
        close_matches = difflib.get_close_matches(seed_title, all_collab_titles, n=1, cutoff=0.5)
        if not close_matches: return []
        matched_title = close_matches[0]

        content_recs, collaborative_recs = [], []
        if matched_title in content_df_hf['Title'].values:
            idx = content_df_hf[content_df_hf['Title'] == matched_title].index[0]
            sim_scores = cosine_similarity([book_embeddings[idx]], book_embeddings)[0]
            sim_scores = sorted(list(enumerate(sim_scores)), key=lambda x: x[1], reverse=True)[1:11]
            book_indices = [i[0] for i in sim_scores]
            recs_df = content_df_hf.iloc[book_indices]
            for _, row in recs_df.iterrows():
                content_recs.append({'title': row['Title'], 'author': row['Author'], 'image_url': row['Image_link']})

        if matched_title in collaborative_pivot.index:
            book_index = list(collaborative_pivot.index).index(matched_title)
            _, suggestions = collaborative_model.kneighbors(collaborative_pivot.iloc[book_index,:].values.reshape(1, -1), n_neighbors=11)
            for i in range(1, len(suggestions.flatten())):
                rec_title = collaborative_pivot.index[suggestions.flatten()[i]]
                book_info = content_df_hf[content_df_hf['Title'] == rec_title]
                if not book_info.empty:
                    collaborative_recs.append({'title': rec_title, 'author': book_info['Author'].values[0], 'image_url': book_info['Image_link'].values[0]})
        
        final_recs, seen_titles = [], set()
        for rec in content_recs:
            if rec['title'] not in seen_titles and rec['title'] != matched_title and rec['title'] not in user_history:
                final_recs.append(rec)
                seen_titles.add(rec['title'])
        for rec in collaborative_recs:
            if len(final_recs) < 10 and rec['title'] not in seen_titles and rec['title'] != matched_title and rec['title'] not in user_history:
                final_recs.append(rec)
                seen_titles.add(rec['title'])
        
        return final_recs[:5]
    except Exception as e:
        print(f"CRITICAL DEBUG ERROR in get_book_recommendations: {e}")
        import traceback
        traceback.print_exc()
        return []


def predict_late_return(user_id, book_id, issue_date):
    """
    Predicts if a new loan is at high risk of being returned late.
    """
    if not LATE_MODEL_READY:
        return {"prediction": "N/A", "message": "Prediction model not available.", "prob_percent": 0}

    try:
        features_data = {
            'loan_duration_days': 14,
            'day_of_week_borrowed': issue_date.weekday()
        }
        
        live_df = pd.DataFrame([features_data], columns=late_return_features)
        prediction = late_return_model.predict(live_df)[0]
        prediction_proba = late_return_model.predict_proba(live_df)[0]
        late_prob_percent = int(prediction_proba[1] * 100)

        if prediction == 1:
            return {"prediction": "High Risk", "message": f"High risk of being late ({late_prob_percent}%)", "prob_percent": late_prob_percent}
        else:
            return {"prediction": "Low Risk", "message": f"Low risk of being late ({late_prob_percent}%)", "prob_percent": late_prob_percent}

    except Exception as e:
        print(f"Error during late return prediction: {e}")
        return {"prediction": "Error", "message": "Prediction Error", "prob_percent": 0}


def get_gemini_fallback_response(message):
    """
    Handles general knowledge questions by calling the Gemini API.
    """
    if not GEMINI_READY:
        return "I can help with library hours and book availability. For other questions, my advanced features are currently offline."

    try:
        # Provide context to the model to guide its personality
        prompt = f"""You are a friendly and helpful library assistant.
        A user has asked a question that is not about book availability or library hours.
        Answer the user's question concisely and helpfully. User question: "{message}" """
        
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API call failed: {e}")
        return "Sorry, I'm having trouble accessing my general knowledge base right now."


# --- FINAL, INTELLIGENT CHATBOT FUNCTION ---
def get_chatbot_response(message, db_connection):
    """
    Parses a user's message to determine intent and provide an intelligent response.
    It first tries to answer based on local rules and falls back to Gemini for general queries.
    """
    message_lower = message.lower()
    
    # --- Intent 1: Check Book Availability (Fast and Specific) ---
    if ('available' in message_lower or 'is ' in message_lower or 'do you have' in message_lower) and ('"' in message or "'" in message):
        try:
            start_quote = message.find("'") if "'" in message else message.find('"')
            end_quote = message.rfind("'") if "'" in message else message.rfind('"')
            
            if start_quote == end_quote:
                return "Please put the book title in single or double quotes for me to search."

            book_title_query = message[start_quote + 1 : end_quote]
            if not book_title_query:
                return "You asked about a book but didn't provide a title in quotes."

            cursor = db_connection.cursor(dictionary=True)
            query = "SELECT title, status FROM books WHERE title LIKE %s LIMIT 1"
            cursor.execute(query, (f"%{book_title_query}%",))
            book = cursor.fetchone()
            cursor.close()

            if book:
                return f"Yes, '{book['title']}' is currently {book['status']}!" if book['status'] == 'Available' else f"Sorry, '{book['title']}' is currently Issued."
            else:
                return f"I could not find a book with a title similar to '{book_title_query}'."

        except Exception as e:
            print(f"Chatbot DB query failed: {e}")
            return "Sorry, I had trouble searching my records."

    # --- Intent 2: General FAQs (Fast and Specific) ---
    elif "hours" in message_lower:
        return "The library is open from 9 AM to 8 PM, Monday to Saturday."
    elif "fine" in message_lower:
        return "The fine for overdue books is $0.1 per day."
    
    # --- Intent 3: General Knowledge Fallback to Gemini ---
    else:
        return get_gemini_fallback_response(message)
