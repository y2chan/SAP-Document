# db_connection.py

import mysql.connector

def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',     # 실제 MySQL 사용자 이름으로 변경
        password='root', # 실제 MySQL 비밀번호로 변경
        database='sap_document_system'
    )
    return connection
