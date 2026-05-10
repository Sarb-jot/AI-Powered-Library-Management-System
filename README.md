# AI-Powered-Library-Management-System

An advanced smart library management system integrating Artificial Intelligence, Machine Learning, RFID-based authentication, IoT, and automated library operations using Flask, MySQL, and Arduino.

---

# Features

## Smart Library Operations

* Book issue and return system
* User authentication and session management
* Admin dashboard for library management
* Fine calculation and overdue tracking
* PDF receipt generation
* Borrowing history tracking

---

## AI & Machine Learning Features

* Personalized book recommendation system
* Hybrid recommendation engine

  * Content-based filtering
  * Collaborative filtering
* Late return prediction using Machine Learning
* AI-powered chatbot using Gemini API

---

## RFID + IoT Integration

* RFID-based user authentication
* Arduino-powered smart kiosk
* 16x2 LCD display integration
* Real-time RFID verification
* Admin RFID auto-setup utility
* Smart authorization system

---

## Payment Integration

* PayPal Sandbox integration for fine payments
* Automatic fine tracking and payment handling

---

# Tech Stack

## Backend

* Python
* Flask
* MySQL

## Machine Learning

* Scikit-learn
* Pandas
* NumPy
* Joblib

## IoT / Hardware

* Arduino UNO/Nano
* RC522 RFID Module
* 16x2 I2C LCD Display

## APIs

* Gemini API
* PayPal Sandbox API

---

# Project Architecture

```text
RFID Card
    ↓
Arduino RFID Reader
    ↓
kiosk_bridge.py
    ↓
Flask Backend (app.py)
    ↓
MySQL Database
    ↓
ML Recommendation + Prediction Engine
```

---

# Folder Structure

```text
AI-Powered-Library-Management-System/
│
├── app.py
├── kiosk_bridge.py
├── setup_admin_rfid.py
├── ml_models.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── database/
│   └── library_management_demo.sql
│
├── templates/
├── static/
│
├── models/
│   ├── collaborative_model.joblib
│   ├── collaborative_pivot_table.joblib
│   ├── content_dataframe_hf.joblib
│   ├── content_embeddings.joblib
│   └── late_return_model.joblib
│
└── arduino/
    └── library_kiosk_rfid_lcd.ino
```

---

# Installation & Setup

## 1. Clone Repository

```bash
git clone https://github.com/Sarb-jot/AI-Powered-Library-Management-System.git
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Database Setup

## Create Database

```sql
CREATE DATABASE library_system;
```

---

## Import SQL Dump

Import the provided SQL dump file:

```text
database/library_management_demo.sql
```

into MySQL.

---

# Configure Database Credentials

Open `app.py` and update the database configuration according to your local MySQL setup:

```python
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'your_password',
    'database': 'library_system'
}
```

---

# API Keys Setup

Set the following environment variables before running the project:

```env
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_secret
GEMINI_API_KEY=your_gemini_api_key
```

---

# RFID Setup (First Time Only)

Connect the Arduino RFID module and run:

```bash
python setup_admin_rfid.py
```

Scan your RFID card when prompted.

The scanned RFID UID will automatically be assigned to the admin account.

---

# Running the Project

## Start Flask Backend

```bash
python app.py
```

---

## Start RFID Bridge

```bash
python kiosk_bridge.py
```

---

# Arduino Hardware Used

* Arduino UNO/Nano
* RC522 RFID Reader
* 16x2 I2C LCD Display
* RFID Cards/Tags

---

# Machine Learning Models

This project uses:

* Hybrid recommendation system
* Late return prediction model
* Synthetic transaction dataset for ML training

---

# Dataset Information

The transaction history and late-return records included in this project are synthetically generated for educational and demonstration purposes.

---

# Default Admin Credentials

```text
Username: admin
Password: admin123
```

Users are recommended to:

* change credentials
* register their own RFID card
* create new users from the admin dashboard

---

# Screenshots

Add screenshots here for:

* Login page
* User dashboard
* Recommendation system
* RFID kiosk
* Admin panel
* LCD display

---

# Future Improvements

* Email notifications
* QR code integration
* Mobile application
* Cloud deployment
* Real-time analytics dashboard
* Face recognition integration

---

# Author

Sarbjot Singh

---

# License

This project is developed for educational and portfolio purposes.
