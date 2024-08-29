import datetime
import time
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
app = Flask(__name__, template_folder='./templates', static_folder='./static')
app.secret_key = os.getenv("SECRET")

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        RotatingFileHandler('app.log', maxBytes=10000, backupCount=1),
                        logging.StreamHandler()
                    ])

driver = os.getenv("DB_DRIVER")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_cluster = os.getenv("DB_CLUSTER")

db_string = f"{driver}://{db_user}:{db_password}@{db_cluster}"

client = MongoClient(db_string)
db = client['reflections']
collection = db['qr_codes']

CREDENTIALS = {"dede@kdiid": "ddd"}


@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        if email in CREDENTIALS and CREDENTIALS[email] == password:
            session['user'] = email
            print(f'User {email} logged in successfully.')
            return redirect(url_for('scan_qr'))
        else:
            app.logger.warning(f'Failed login attempt for username: {email}')
            flash('Login Failed. Check your username and/or password.')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/scan_qr')
def scan_qr():
    if 'user' not in session:
        app.logger.warning('Unauthorized access attempt to /scan_qr.')
        flash('You need to log in first.')
        return redirect(url_for('login'))
    app.logger.info(f'User {session["user"]} accessed the scan QR page.')
    return render_template('scanQR.html')


@app.route('/scan-result', methods=['POST'])
def scan_result():
    data = request.get_json()
    qr_code = data.get('qr_code')
    app.logger.info(f"Scanned QR Code: {qr_code}")
    if qr_code:
        data_to_db = {
            'attendance': True,
            'entry_time': datetime.datetime.now()
        }
        filter = {'unique_value': qr_code}

        # Example update operation: Replace the document or update specific fields
        update_operation = {
            "$set": data_to_db  # This updates the document by setting the fields specified in `data_to_db`
        }
        user_data = collection.find_one(filter)
        if user_data:
            logging.info(f"user details{user_data}")
            if user_data.get('attendance') is True:
                return jsonify({"message": "Already Registered!"})

        result = collection.update_one(filter, update_operation)
        app.logger.info(f"Scanned QR Code: {qr_code} added to database with ID: {result}")
        updated_result = collection.find_one(filter)
        if updated_result is None:
            logging.info(updated_result)
            return jsonify({"message": "User not found"})
        return jsonify({"message": "QR Code data added to database!"}), 201
    else:
        app.logger.warning('QR Code data was missing from the request.')
        return jsonify({"error": "No QR code data provided."}), 400


# get all users
@app.route('/get-all-users', methods=['GET'])
def get_users():
    filters = {}
    emp_id = request.args.get("ID")
    attendance = request.args.get("attendance")
    if emp_id:
        filters.update({'ID': emp_id})
    if attendance:
        if attendance.lower() == 'true':
            filters.update({'attendance': True})
        elif attendance.lower() == 'false':
            filters.update({'attendance': False})
    result = collection.find(filters)
    if result:
        app.logger.info(f"API to get all users {result}")
        users = []
        for user in result:
            user['_id'] = str(user['_id'])  # Convert ObjectId to string
            users.append(user)

        # Return the result as JSON
        return jsonify(users)
    else:
        return jsonify({"message": "User(s) not found"})



if __name__ == "__main__":
    app.run(debug=True)
