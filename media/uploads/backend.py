import sqlite3
import hashlib
# import firebase_admin
# from firebase_admin import credentials, firestore
from church_backup import ChurchBackup
import os
import requests
import configparser
import uuid
from PIL import Image
import io
import os
from datetime import datetime

# Load configuration
config = configparser.ConfigParser()
config.read(r'Serenity_Update\config.ini')

# --- Get total remittance for expense calculation ---
def get_total_head_church_remittance(church_id, period=None, date_range=None):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            query = "SELECT SUM(remit_amount) FROM HeadChurchRemittance WHERE church_id = ?"
            params = [church_id]
            if date_range:
                query += " AND date >= ? AND date <= ?"
                params += [date_range[0], date_range[1]]
            elif period == "Monthly":
                query += " AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
            elif period == "Quarterly":
                query += " AND strftime('%Y', date) = strftime('%Y', 'now') AND ((cast(strftime('%m', date) as integer)-1)/3+1)=((cast(strftime('%m', 'now') as integer)-1)/3+1)"
            elif period == "Yearly":
                query += " AND strftime('%Y', date) = strftime('%Y', 'now')"
            cur.execute(query, params)
            result = cur.fetchone()
            return float(result[0]) if result and result[0] is not None else 0.0
    except Exception as e:
        print("Error calculating total remittance:", e)
        return 0.0
# --- Head Church Remittance Backend Functions ---
def insert_head_church_remittance(church_id, period, percentage, category, total_income, remit_amount):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO HeadChurchRemittance (church_id, period, percentage, category, total_income, remit_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (church_id, period, percentage, category, total_income, remit_amount))
            con.commit()
        return True
    except Exception as e:
        print("Error inserting remittance:", e)
        return False
    
def get_head_church_remittances(church_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM HeadChurchRemittance WHERE church_id = ? ORDER BY date DESC", (church_id,))
            return cur.fetchall()
    except Exception as e:
        print("Error fetching remittances:", e)
        return []

def get_income_categories(church_id):
    """Get all income categories including tithe, offerings, and custom categories"""
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            
            # Get distinct offering types
            cur.execute("SELECT DISTINCT offering_type FROM offering WHERE church_id=?", (church_id,))
            offering_types = [row[0] for row in cur.fetchall() if row[0]]
            
            # Check if tithe exists
            cur.execute("SELECT 1 FROM tithing WHERE church_id=? LIMIT 1", (church_id,))
            has_tithe = bool(cur.fetchone())
            
            # Get custom categories
            cur.execute("SELECT name FROM categories WHERE church_id=?", (church_id,))
            custom_categories = [row[0] for row in cur.fetchall() if row[0]]
            
            # Combine all categories
            categories = []
            if has_tithe:
                categories.append("Tithe")
            categories.extend(offering_types)
            categories.extend(custom_categories)
            
            return list(set(categories))  # Remove duplicates
            
    except Exception as e:
        print("Error fetching income categories:", e)
        return ["Tithe", "Offering"]  # Fallback defaults

def get_category_income(church_id, category, period=None, date_range=None):
    """Calculate income for a specific category with time filters"""
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            
            if category == "Tithe":
                query = "SELECT COALESCE(SUM(amount), 0) FROM tithing WHERE church_id=?"
                params = [church_id]
            else:
                query = "SELECT COALESCE(SUM(amount), 0) FROM offering WHERE church_id=? AND offering_type=?"
                params = [church_id, category]
            
            # Add time filtering
            if date_range:
                query += " AND date >= ? AND date <= ?"
                params.extend([date_range[0], date_range[1]])
            elif period == "Monthly":
                query += " AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
            elif period == "Quarterly":
                query += " AND strftime('%Y', date) = strftime('%Y', 'now') AND ((cast(strftime('%m', date) as integer)-1)/3+1)=((cast(strftime('%m', 'now') as integer)-1)/3+1)"
            elif period == "Yearly":
                query += " AND strftime('%Y', date) = strftime('%Y', 'now')"
            
            cur.execute(query, params)
            result = cur.fetchone()
            return float(result[0]) if result else 0.0
    except Exception as e:
        print("Error calculating category income:", e)
        return 0.0

def get_finance_total(church_id, period=None, date_range=None):
    """Get total income for all categories"""
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            
            # Sum all offerings
            offering_query = "SELECT COALESCE(SUM(amount), 0) FROM offering WHERE church_id=?"
            offering_params = [church_id]
            
            # Sum all tithes
            tithe_query = "SELECT COALESCE(SUM(amount), 0) FROM tithing WHERE church_id=?"
            tithe_params = [church_id]
            
            # Add time filtering if provided
            if date_range:
                offering_query += " AND date >= ? AND date <= ?"
                offering_params.extend([date_range[0], date_range[1]])
                tithe_query += " AND date >= ? AND date <= ?"
                tithe_params.extend([date_range[0], date_range[1]])
            elif period == "Monthly":
                offering_query += " AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
                tithe_query += " AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
            elif period == "Quarterly":
                offering_query += " AND strftime('%Y', date) = strftime('%Y', 'now') AND ((cast(strftime('%m', date) as integer)-1)/3+1)=((cast(strftime('%m', 'now') as integer)-1)/3+1)"
                tithe_query += " AND strftime('%Y', date) = strftime('%Y', 'now') AND ((cast(strftime('%m', date) as integer)-1)/3+1)=((cast(strftime('%m', 'now') as integer)-1)/3+1)"
            elif period == "Yearly":
                offering_query += " AND strftime('%Y', date) = strftime('%Y', 'now')"
                tithe_query += " AND strftime('%Y', date) = strftime('%Y', 'now')"
            
            # Execute both queries
            cur.execute(offering_query, offering_params)
            offering_total = float(cur.fetchone()[0]) or 0.0
            
            cur.execute(tithe_query, tithe_params)
            tithe_total = float(cur.fetchone()[0]) or 0.0
            
            return offering_total + tithe_total
    except Exception as e:
        print("Error calculating total income:", e)
        return 0.0
        
def delete_head_church_remittance(remit_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM HeadChurchRemittance WHERE id = ?", (remit_id,))
            con.commit()
        return True
    except Exception as e:
        print("Error deleting remittance:", e)
        return False

def get_finance_total(church_id, period, date_range=None):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            # Default: sum all income for the church
            query = "SELECT SUM(amount) FROM offering WHERE church_id = ?"
            params = [church_id]
            # If period is Monthly, Quarterly, Yearly, or custom range, filter by date
            if date_range:
                query = "SELECT SUM(amount) FROM offering WHERE church_id = ? AND date >= ? AND date <= ?"
                params = [church_id, date_range[0], date_range[1]]
            elif period == "Monthly":
                query = "SELECT SUM(amount) FROM offering WHERE church_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
            elif period == "Quarterly":
                query = "SELECT SUM(amount) FROM offering WHERE church_id = ? AND strftime('%Y', date) = strftime('%Y', 'now') AND ((cast(strftime('%m', date) as integer)-1)/3+1)=((cast(strftime('%m', 'now') as integer)-1)/3+1)"
            elif period == "Yearly":
                query = "SELECT SUM(amount) FROM offering WHERE church_id = ? AND strftime('%Y', date) = strftime('%Y', 'now')"
            cur.execute(query, params)
            result = cur.fetchone()
            return float(result[0]) if result and result[0] is not None else 0.0
    except Exception as e:
        print("Error calculating finance total:", e)
        return 0.0


# Firebase setup
# firebase_cred_path = config['firebase']['credential_path']
# cred = credentials.Certificate(firebase_cred_path)
# firebase_admin.initialize_app(cred)
# db = firestore.client()

# def create_sms_limit_document(church_id, sms_limit=20, sms_sent=0):
#     """Create the sms_limits document for a church in Firestore."""
#     try:
#         doc_ref = db.collection('sms_limits').document(church_id)
#         doc_ref.set({
#             'sms_limit': sms_limit,
#             'sms_sent': sms_sent
#         })
#         print(f"SMS limit document created for Church '{church_id}'.")
#     except Exception as e:
#         print(f"Error creating SMS limit document for Church '{church_id}':", e)

# def check_sms_limit(church_id):
#     try:
#         doc_ref = db.collection('sms_limits').document(church_id)
#         doc = doc_ref.get()
#         if doc.exists:
#             sms_data = doc.to_dict()
#             return sms_data['sms_limit'] > sms_data['sms_sent']
#         else:
#             return False  # If no document exists, disallow sending
#     except Exception as e:
#         print("Error checking SMS limit:", e)
#         return False

# def update_sms_count(church_id):
#     try:
#         doc_ref = db.collection('sms_limits').document(church_id)
#         doc = doc_ref.get()
#         if doc.exists:
#             sms_data = doc.to_dict()
#             new_count = sms_data['sms_sent'] + 1
#             doc_ref.update({'sms_sent': new_count})
#         else:
#             print("SMS limit document not found.")
#     except Exception as e:
#         print("Error updating SMS count:", e)

def get_database_path():
   
    # Get the current working directory
    current_dir = os.getcwd()
    
    # Create the 'Database' folder if it doesn't exist
    database_dir = os.path.join(current_dir, 'Database')
    if not os.path.exists(database_dir):
        os.makedirs(database_dir)
    
    # Return the full path to the SQLite database file inside the 'Database' folder
    return os.path.join(database_dir, "SerenityDatabase.db")

def is_online():
    try:
        # Attempt to connect to a reliable external site
        requests.get('https://www.google.com', timeout=5)
        return True
    except requests.ConnectionError:
        return False

def connect():
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS churches (
                    id INTEGER PRIMARY KEY,
                    church_name TEXT,
                    church_id TEXT UNIQUE,
                    password TEXT,
                    phone TEXT
                )
            """)
    
            cur.execute("""
                CREATE TABLE IF NOT EXISTS New_members (
                    id INTEGER PRIMARY KEY,
                    church_id TEXT,
                    memberID TEXT,
                    fullname TEXT,
                    dob TEXT,
                    pob TEXT,
                    contact TEXT,
                    sex TEXT,
                    marital_status TEXT,
                    occupation TEXT,
                    residential_address TEXT,
                    department TEXT,
                    passport_picture BLOB,
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visitors (
                    id INTEGER PRIMARY KEY,
                    church_id TEXT,
                    fullname TEXT,
                    purpose TEXT,
                    sex TEXT,
                    occupation TEXT,
                    phone_number TEXT,
                    address TEXT,
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tithing (
                    id INTEGER PRIMARY KEY,
                    church_id TEXT,
                    memberID TEXT,
                    fullname TEXT,
                    month TEXT,
                    amount REAL,
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS offering (
                    id INTEGER PRIMARY KEY,
                    church_id TEXT,
                    offering_type TEXT,
                    amount TEXT,
                    service TEXT,
                    date REAL,
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sms_limits (
                    church_id TEXT PRIMARY KEY,
                    sms_limit INTEGER,
                    sms_sent INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Attendance (
                    id INTEGER PRIMARY KEY,
                    church_id TEXT,
                    date_column TEXT,
                    memberID TEXT,
                    status TEXT,
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ManualAttendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    church_id TEXT,
                    date TEXT,
                    men INTEGER,
                    women INTEGER,
                    children INTEGER,
                    youth INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY,
                    church_id TEXT,
                    expense_type TEXT,
                    amount REAL,
                    description TEXT,
                    date TEXT,
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    church_id TEXT,
                    name TEXT,
                    UNIQUE(church_id, name),
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )""")
            
            # CORRECTED: Added category column to HeadChurchRemittance table
            cur.execute("""CREATE TABLE IF NOT EXISTS HeadChurchRemittance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                church_id TEXT,
                period TEXT,
                percentage REAL,
                category TEXT,
                total_income REAL,
                remit_amount REAL,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )""")

            con.commit()
    except sqlite3.Error as e:
        print("Error creating tables:", e)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_church(church_name, church_id, password, phone):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            hashed_password = hash_password(password)
            cur.execute("""
                INSERT INTO churches (church_name, church_id, password, phone)
                VALUES (?, ?, ?, ?)
            """, (church_name, church_id, hashed_password, phone))
            con.commit()
            print(f"Church '{church_name}' registered successfully.")
            
            # Create the SMS limit document in Firestore
            # create_sms_limit_document(church_id, sms_limit=1000, sms_sent=0)

            # # Sync church data with Firestore
            # church_data = {
            #     'church_name': church_name,
            #     'church_id': church_id,
            #     'password': hashed_password,  # Store hashed password
            #     'phone': phone
            # }
            # db.collection('churches').document(church_id).set(church_data)
            # print(f"Church '{church_name}' data synced with Firebase")
    except sqlite3.Error as e:
        print("Error registering church:", e)
    # except firebase_admin.exceptions.FirebaseError as fe:
    #     print("Error syncing to Firebase:", fe)

def verify_church(church_id, password):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            hashed_password = hash_password(password)
            cur.execute("""
                SELECT * FROM churches WHERE church_id = ? AND password = ?
            """, (church_id, hashed_password))
            church = cur.fetchone()
            if church:
                print(f"Church '{church[1]}' verified successfully.")

                # Fetch SMS limit from Firestore and update local database
                # doc_ref = db.collection('sms_limits').document(church_id)
                # doc = doc_ref.get()
                # if doc.exists:
                #     sms_data = doc.to_dict()
                #     cur.execute("""
                #         INSERT OR REPLACE INTO sms_limits (church_id, sms_limit, sms_sent)
                #         VALUES (?, ?, ?)
                #     """, (church_id, sms_data['sms_limit'], sms_data['sms_sent']))
                #     con.commit()
                #     print(f"SMS limit for Church '{church[1]}' synced successfully.")
                # else:
                    # print("No SMS limit found in Firestore.")
                
                return True
            else:
                print("Invalid church_id or password.")
                return False
    except sqlite3.Error as e:
        print("Error verifying church:", e)
        return False

def verify_church_id(church_id):
    """Verify if a church ID exists in the database."""
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT * FROM churches WHERE church_id = ?
            """, (church_id,))
            return cur.fetchone() is not None
    except sqlite3.Error as e:
        print("Error verifying church ID:", e)
        return False

def insert_new_member(church_id, memberID="", fullname="", dob="", pob="", contact="", sex="", marital_status="", occupation="", residential_address="", department="", passport_picture=None):
    try:
        # Verify if the church ID exists
        if not verify_church_id(church_id):
            print("Invalid Church ID. Member not inserted.")
            return
        
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO New_members 
                VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (church_id, memberID, fullname, dob, pob, contact, sex, marital_status, occupation, residential_address, department, passport_picture))
            con.commit()
            print(f"Member '{fullname}' inserted successfully.")
    except sqlite3.Error as e:
        print("Error inserting new member:", e)

def insert_visitor(church_id, fullname="", purpose="", sex="", occupation = "", phone_number="", address=""):
    try:
        # Verify if the church ID exists
        if not verify_church_id(church_id):
            print("Invalid Church ID. Visitor not inserted.")
            return
        
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO visitors (id, church_id, fullname, purpose, sex, occupation, phone_number, address)
                VALUES (NULL,?,?,?,?,?,?,?)
            """, (church_id, fullname, purpose, sex, occupation, phone_number, address))
            con.commit()
            print(f"Visitor '{fullname}' inserted successfully.")
    except sqlite3.Error as e:
        print("Error inserting visitor:", e)

def insert_tithing(church_id, memberID="", fullname="", month="", amount=0.0):
    try:
        # Verify if the church ID exists
        if not verify_church_id(church_id):
            print("Invalid Church ID. Tithing record not inserted.")
            return
        
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO tithing 
                VALUES (NULL,?,?,?,?,?)
            """, (church_id, memberID, fullname, month, amount))
            con.commit()
            print(f"Tithing record for '{fullname}' inserted successfully.")
    except sqlite3.Error as e:
        print("Error inserting tithing record:", e)

def insert_offering(church_id, offering_type="", amount=0.0, service="", date=""):
    try:
        # Verify if the church ID exists
        if not verify_church_id(church_id):
            print("Invalid Church ID. Offering record not inserted.")
            return
        
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO offering 
                VALUES (NULL,?,?,?,?,?)
            """, (church_id, offering_type,amount, service, date))
            con.commit()
            print(f"Offering record of '{amount} for {offering_type}' inserted successfully.")
    except sqlite3.Error as e:
        print("Error inserting Offering record:", e)

def insert_expense(church_id, expense_type="", amount=0.0, description="", date=""):
    try:
        if not verify_church_id(church_id):
            print("Invalid Church ID. Expense record not inserted.") 
            return
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO expenses 
                VALUES (NULL,?,?,?,?,?)
            """, (church_id, expense_type, amount, description, date))
            con.commit()
            print(f"Expense record of '{amount} for {expense_type}' inserted successfully.")
    except sqlite3.Error as e:
        print("Error inserting Expense record:", e)

def delete_new_member(memberID):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM New_members WHERE memberID = ?", (memberID,))
            con.commit()
            print(f"Member with ID '{memberID}' deleted successfully.")
    except sqlite3.Error as e:
        print("Error deleting member:", e)

def delete_visitor(id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM visitors WHERE id = ?", (id,))
            con.commit()
            print(f"Visitor with ID '{id}' deleted successfully.")
    except sqlite3.Error as e:
        print("Error deleting visitor:", e)

def view_new_members(church_id):
    try:
        db_path = get_database_path()
        if not verify_church_id(church_id):
            return
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM New_members WHERE church_id = ?", (church_id,))
            rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        print("Error viewing new members:", e)
        return None


def view_visitors(church_id):
    try:
        db_path = get_database_path()
        if not verify_church_id(church_id):
            return
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM visitors WHERE church_id = ?", (church_id,))
            rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        print("Error viewing visitors:", e)
        return None

def view_tithing(church_id):
    try:
        db_path = get_database_path()
        if not verify_church_id(church_id):
            return
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM tithing WHERE church_id = ?", (church_id,))
            rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        print("Error viewing tithing records:", e)
        return None


def view_offering(church_id):
    try:
        db_path = get_database_path()
        if not verify_church_id(church_id):
            return
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM offering WHERE church_id = ?", (church_id,))
            rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        print("Error viewing offering records:", e)
        return None

def view_expenses(church_id):
    try:
        db_path = get_database_path()
        if not verify_church_id(church_id):
            return
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM expenses WHERE church_id = ?", (church_id,))
            rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        print("Error viewing expense records:", e)
        return None

def get_church_name(church_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                SELECT church_name FROM churches WHERE church_id = ?
            """, (church_id,))
            result = cur.fetchone()
            if result:
                return result[0]  # Return the church name
            else:
                print("Church ID not found.")
                return None
    except sqlite3.Error as e:
        print("Error retrieving church name:", e)
        return None

def get_all_member_phones(church_id):
    # Return a list of all member phone numbers for the church
    # Example:
    db_path = get_database_path()
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT contact FROM New_members WHERE church_id = ?", (church_id,))
        return [row[0] for row in cur.fetchall() if row[0]]

def get_department_phones(church_id, department):
    db_path = get_database_path()
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("SELECT contact FROM New_members WHERE church_id = ? AND department = ?", (church_id, department))
        return [row[0] for row in cur.fetchall() if row[0]]
    
def send_bulk_sms(phone_numbers, message, sender_id):
    """
    Simplified bulk SMS sending function using Arkesel API
    Args:
        phone_numbers: List of phone numbers to send to
        message: Text message to send
        sender_id: Sender ID to display
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Load configuration
        config = configparser.ConfigParser()
        config.read(r'config.ini')
        
        api_url = config['arkesel']['api_url']
        api_key = config['arkesel']['api_key']
        
        # Validate inputs
        if not phone_numbers:
            return False, "No phone numbers provided"
        
        if not message or len(message.strip()) == 0:
            return False, "Message cannot be empty"
        
        if not sender_id or len(sender_id.strip()) == 0:
            return False, "Sender ID cannot be empty"
        
        # Prepare API request
        params = {
            'api_key': api_key,
            'from': sender_id,
            'sms': message,
            'to': ','.join(phone_numbers)  # Send all numbers in one request
        }
        
        # Make API call
        response = requests.get(api_url, params=params)
        
        # Check response
        if response.status_code == 200:
            return True, f"Message sent to {len(phone_numbers)} recipients"
        else:
            return False, f"API error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, f"Error sending SMS: {str(e)}"
def search_member_by_name_or_phone(church_id, query):
    # Return a list of (name, phone) tuples matching the query
    # Example: search by LIKE for name or phone
    import sqlite3
    db_path = get_database_path()
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT full_name, contact FROM New_members
            WHERE church_id = ? AND (full_name LIKE ? OR contact LIKE ?)
        """, (church_id, f"%{query}%", f"%{query}%"))
        return cur.fetchall()

def update_new_member(church_id, memberID, fullname, dob, pob, contact, sex, marital_status, occupation, residential_address, department, passport_picture):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                UPDATE New_members SET
                    fullname = ?, dob = ?, pob = ?, contact = ?, sex = ?, marital_status = ?,
                    occupation = ?, residential_address = ?, department = ?, passport_picture = ?
                WHERE church_id = ? AND memberID = ?
            """, (fullname, dob, pob, contact, sex, marital_status, occupation, residential_address, department, passport_picture, church_id, memberID))
            con.commit()
            print(f"Member '{fullname}' updated successfully.")
    except sqlite3.Error as e:
        print("Error updating member:", e)

def count_all_members(church_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM New_members WHERE church_id = ?", (church_id,))
            return cur.fetchone()[0]
    except Exception as e:
        print("Error counting all members:", e)
        return 0

def count_male_members(church_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM New_members WHERE church_id = ? AND sex = 'Male'", (church_id,))
            return cur.fetchone()[0]
    except Exception as e:
        print("Error counting male members:", e)
        return 0

def count_female_members(church_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM New_members WHERE church_id = ? AND sex = 'Female'", (church_id,))
            return cur.fetchone()[0]
    except Exception as e:
        print("Error counting female members:", e)
        return 0
def insert_attendance(church_id, date_column, memberID, status):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO Attendance (church_id, date_column, memberID, status)
                VALUES (?, ?, ?, ?)
            """, (church_id, date_column, memberID, status))
            con.commit()
    except sqlite3.Error as e:
        print("Error inserting attendance:", e)
def view_attendance(church_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM Attendance WHERE church_id = ?", (church_id,))
            rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        print("Error viewing attendance records:", e)
        return None

def save_manual_attendance(church_id, data):
    import sqlite3
    from datetime import date
    today = date.today().isoformat()
    conn = sqlite3.connect(r"Database/SerenityDatabase.db")
    cur = conn.cursor()
    # Create table if not exists
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ManualAttendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            church_id TEXT,
            date TEXT,
            men INTEGER,
            women INTEGER,
            children INTEGER,
            youth INTEGER
        )
    ''')
    # Upsert for today
    cur.execute('''
        SELECT id FROM ManualAttendance WHERE church_id=? AND date=?
    ''', (church_id, today))
    row = cur.fetchone()
    if row:
        cur.execute('''
            UPDATE ManualAttendance SET men=?, women=?, children=?, youth=? WHERE id=?
        ''', (data['men'], data['women'], data['children'], data['youth'], row[0]))
    else:
        cur.execute('''
            INSERT INTO ManualAttendance (church_id, date, men, women, children, youth)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (church_id, today, data['men'], data['women'], data['children'], data['youth']))
    conn.commit()
    conn.close()

def get_manual_attendance_totals(church_id):
    import sqlite3
    conn = sqlite3.connect(r"Database/SerenityDatabase.db")
    cur = conn.cursor()
    cur.execute('''
        SELECT date, men, women, children, youth FROM ManualAttendance WHERE church_id=? ORDER BY date
    ''', (church_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_categories(church_id):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT name FROM categories WHERE church_id = ? ORDER BY name", (church_id,))
            rows = cur.fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error as e:
        print("Error loading categories:", e)
        return []

def add_category(church_id, name):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("INSERT OR IGNORE INTO categories (church_id, name) VALUES (?, ?)", (church_id, name))
            con.commit()
    except sqlite3.Error as e:
        print("Error adding category:", e)

def delete_category(church_id, name):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM categories WHERE church_id = ? AND name = ?", (church_id, name))
            con.commit()
    except sqlite3.Error as e:
        print("Error deleting category:", e)

def update_category(church_id, old_name, new_name):
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("UPDATE categories SET name = ? WHERE church_id = ? AND name = ?", (new_name, church_id, old_name))
            con.commit()
    except sqlite3.Error as e:
        print("Error updating category:", e)
# Main execution


def create_church_backup(church_id):
    """Create a backup for a specific church"""
    backup = ChurchBackup(church_id)
    return backup.create_backup()

def restore_church_backup(church_id, backup_path):
    """Restore a church from backup"""
    backup = ChurchBackup(church_id)
    return backup.restore_backup(backup_path)

def list_church_backups(church_id):
    """List all backups for a church"""
    backup = ChurchBackup(church_id)
    return backup.list_backups()

def get_backup_settings():
    """Get backup configuration"""
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini')
        return config['Backup'] if 'Backup' in config else None
    return None

def save_backup_settings(auto_backup, location):
    """Save backup preferences"""
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini')
    
    if 'Backup' not in config:
        config['Backup'] = {}
    
    config['Backup']['auto_backup'] = auto_backup
    config['Backup']['location'] = location
    
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


# ----------------- Receipts (Image BLOB) -----------------
def save_receipt(church_id, reference_type, reference_id, amount, description, image_data, receipt_number=None):
    """Saves a receipt with validation. Accepts church_id as str or int; stored as TEXT."""
    try:
        if not church_id:
            raise ValueError("Invalid church ID")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Amount must be positive")
        if not description or len(description.strip()) < 5:
            raise ValueError("Description too short")
        if not image_data:
            raise ValueError("No image data provided")

        # Process/validate image
        try:
            image = Image.open(io.BytesIO(image_data))
            if image.format not in ('PNG', 'JPEG', 'JPG'):
                raise ValueError("Unsupported image format")
            if max(image.size) > 2000:
                image.thumbnail((2000, 2000))
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            image_data = img_bytes.getvalue()
        except Exception as img_error:
            raise ValueError(f"Invalid image: {str(img_error)}") from img_error

        db_path = get_database_path()
        os.makedirs(os.path.join(os.path.dirname(db_path), "receipts"), exist_ok=True)

        if not receipt_number:
            receipt_number = f"RCPT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            # Table already created in connect(), but keep safe
            cur.execute("""
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    church_id TEXT NOT NULL,
                    reference_type TEXT,
                    reference_id TEXT,
                    receipt_number TEXT UNIQUE NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT NOT NULL,
                    image_data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (church_id) REFERENCES churches(church_id)
                )
            """)

            cur.execute("""
                INSERT INTO receipts (church_id, reference_type, reference_id, receipt_number, amount, description, image_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (str(church_id), reference_type, reference_id, receipt_number, float(amount), description, image_data))
            con.commit()
            return receipt_number

    except sqlite3.Error as db_error:
        print(f"Database error saving receipt: {db_error}")
        raise Exception("Database operation failed") from db_error
    except Exception as e:
        print(f"Error saving receipt: {e}")
        raise


def update_receipt(receipt_number, amount=None, description=None):
    """Update receipt amount/description (supports inline editing from UI)."""
    if amount is None and (description is None or description.strip() == ""):
        return False
    try:
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            if amount is not None and description is not None:
                cur.execute("UPDATE receipts SET amount=?, description=? WHERE receipt_number=?",
                            (float(amount), description.strip(), receipt_number))
            elif amount is not None:
                cur.execute("UPDATE receipts SET amount=? WHERE receipt_number=?", (float(amount), receipt_number))
            else:
                cur.execute("UPDATE receipts SET description=? WHERE receipt_number=?", (description.strip(), receipt_number))
            con.commit()
        return True
    except Exception as e:
        print("Error updating receipt:", e)
        return False


def get_receipts(church_id, reference_type=None, reference_id=None):
    """Return tuples for UI compatibility: (id, church_id, reference_type, reference_id, receipt_number, amount, description, date)"""
    try:
        if not church_id:
            raise ValueError("Invalid church ID")
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            query = """
                SELECT id, church_id, reference_type, reference_id, 
                       receipt_number, amount, description, 
                       datetime(created_at, 'localtime') as date
                FROM receipts 
                WHERE church_id = ?
            """
            params = [str(church_id)]
            if reference_type and reference_id:
                query += " AND reference_type = ? AND reference_id = ?"
                params.extend([reference_type, reference_id])
            query += " ORDER BY created_at DESC"
            cur.execute(query, params)
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching receipts: {e}")
        raise


def get_receipt_image(receipt_number):
    """Gets receipt image data with validation"""
    try:
        if not receipt_number or not isinstance(receipt_number, str):
            raise ValueError("Invalid receipt number")
        db_path = get_database_path()
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT image_data FROM receipts WHERE receipt_number = ?", (receipt_number,))
            result = cur.fetchone()
            if result and result[0]:
                return result[0]
            return None
    except Exception as e:
        print(f"Error getting receipt image: {e}")
        raise

if __name__ == "__main__":
    connect()


