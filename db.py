import os
import pymysql
from dotenv import load_dotenv
import json
import random
import string

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
            user = cursor.fetchone()
            if user:
                # 將地址字串分割成清單
                if user['address']:
                    user['addresses'] = user['address'].split('/')
                else:
                    user['addresses'] = []
            return user

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

def update_user_mode(line_user_id, mode):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = "UPDATE users SET mode = %s WHERE line_user_id = %s"
            cursor.execute(sql, (mode, line_user_id))
            conn.commit()

def clear_user_mode(line_user_id):
    update_user_mode(line_user_id, None)

def update_temp_value(line_user_id, value):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            sql = "UPDATE users SET temp_value = %s WHERE line_user_id = %s"
            cursor.execute(sql, (value, line_user_id))
            conn.commit()

def clear_temp_value(line_user_id):
    update_temp_value(line_user_id, None)

def append_address(line_user_id, new_address):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # 取得現有的地址字串
            sql = "SELECT address FROM users WHERE line_user_id = %s"
            cursor.execute(sql, (line_user_id,))
            result = cursor.fetchone()
            current_address = result['address'] if result and result['address'] else ""

            # 合併地址
            if current_address:
                updated_address = f"{current_address}/{new_address}"
            else:
                updated_address = new_address
            
            # 更新資料庫
            sql = "UPDATE users SET address = %s WHERE line_user_id = %s"
            cursor.execute(sql, (updated_address, line_user_id))
            conn.commit()


# ============= addresses JSON 資料格式修改 =======================

def generate_new_password(length=4):
    letters = random.choices(string.ascii_letters, k=2)
    digits = random.choices(string.digits, k=2)
    combined = letters + digits
    random.shuffle(combined)
    return ''.join(combined)

def update_address_info(address, new_password):
    addresses_data = load_addresses_data()
    for item in addresses_data:
        if item['address'] == address:
            item['password'] = new_password
            break
    save_addresses_data(addresses_data)

def save_addresses_data(data):
    with open('available_addresses.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_address_info(address):
    addresses_data = load_addresses_data()
    for item in addresses_data:
        if item['address'] == address:
            return item
    return None

def load_addresses_data():
    try:
        with open('available_addresses.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def update_address_warranty_start_date(address, start_date):
    """
    更新指定地址的保固開始日期。
    只有當該地址的 warranty_start_date 欄位為空時，才會寫入新日期。
    """
    addresses_data = load_addresses_data()
    updated = False
    
    for item in addresses_data:
        if item.get('address') == address:
            # 檢查保固開始日期是否已存在且非空
            if not item.get('warranty_start_date'):
                # 首次寫入保固開始日期
                item['warranty_start_date'] = start_date
                updated = True
            break
            
    if updated:
        save_addresses_data(addresses_data)
        return True # 表示已更新
    return False # 表示未更新（因為日期已存在）