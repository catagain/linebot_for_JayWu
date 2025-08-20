import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def user_exists(line_user_id):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE line_user_id = %s"
            cursor.execute(sql, (line_user_id,))
            return cursor.fetchone() is not None

def add_user(line_user_id):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = "INSERT INTO users (line_user_id) VALUES (%s)"
            cursor.execute(sql, (line_user_id,))
            conn.commit()

def update_identity(line_user_id, identity):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = """
            UPDATE users
            SET identity = %s, is_identified = TRUE
            WHERE line_user_id = %s
            """
            cursor.execute(sql, (identity, line_user_id))
            conn.commit()

def get_user(line_user_id):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE line_user_id = %s"
            cursor.execute(sql, (line_user_id,))
            return cursor.fetchone()

def update_user_step(line_user_id, step):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = "UPDATE users SET step = %s WHERE line_user_id = %s"
            cursor.execute(sql, (step, line_user_id))
            conn.commit()

def update_user_field(line_user_id, field_name, value):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = f"UPDATE users SET {field_name} = %s WHERE line_user_id = %s"
            cursor.execute(sql, (value, line_user_id))
            conn.commit()

def update_temp_value(line_user_id, value):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = "UPDATE users SET temp_value = %s WHERE line_user_id = %s"
            cursor.execute(sql, (value, line_user_id))
            conn.commit()

def clear_temp_value(line_user_id):
    update_temp_value(line_user_id, None)

