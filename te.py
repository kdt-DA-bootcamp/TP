import streamlit as st
import mysql.connector
import os
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv()

st.title("RDS 연결 테스트")

host = os.getenv("DB_HOST")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")
port = int(os.getenv("DB_PORT", 3306))

st.write(f"연결 시도: Host={host}, User={user}, DB={database}, Port={port}")

try:
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        charset='utf8mb4',
        collation='utf8mb4_general_ci'  # 이 부분이 반드시 포함되어야 함
    )
    st.success("RDS에 연결 성공!")
    connection.close()
except mysql.connector.Error as err:
    st.error(f"연결 오류: {err.errno} - {err.msg}")