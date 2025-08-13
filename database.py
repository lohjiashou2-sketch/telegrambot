import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
import boto3
import json
from cryptography.fernet import Fernet

load_dotenv()

def get_encryption_key():

    secret_name = os.getenv("SECRET_NAME")
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    return secret["encrypt_key"]

def encrypt_password(password):
    key = get_encryption_key()
    cipher = Fernet(key.encode())
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    key = get_encryption_key()
    cipher = Fernet(key.encode())
    return cipher.decrypt(encrypted_password.encode()).decode()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def save_future_booking(username, password, facility, date, time, status):
    encrypted_pw = encrypt_password(password)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings (username, encrypted_password, facility, booking_date, booking_time, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        username,
        encrypted_pw,
        facility,
        datetime.strptime(date, "%d/%m/%Y").date(),
        time,
        status
    ))
    conn.commit()
    cur.close()
    conn.close()
