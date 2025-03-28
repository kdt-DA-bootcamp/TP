import streamlit as st
import os
from dotenv import load_dotenv

# .env는 로컬에서만 로드 (Streamlit Cloud에서는 무시됨)
if os.path.exists(".env"):
    load_dotenv()

st.title("환경 변수 확인")

st.write(f"DB_HOST: {os.getenv('DB_HOST')}")
st.write(f"DB_USER: {os.getenv('DB_USER')}")
st.write(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")
st.write(f"DB_NAME: {os.getenv('DB_NAME')}")
st.write(f"DB_PORT: {os.getenv('DB_PORT')}")