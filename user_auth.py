import streamlit as st
import hashlib
from db_connection import get_db_connection

# 비밀번호 해시화 함수
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 사용자 인증 함수
def authenticate_user(user_id, password):
    hashed_pw = hash_password(password)
    connection = get_db_connection()
    cursor = connection.cursor()
    sql = "SELECT * FROM user WHERE user_id = %s AND password = %s"
    cursor.execute(sql, (user_id, hashed_pw))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result is not None

# 로그인 함수
def login():
    st.sidebar.subheader("로그인")
    user_id = st.sidebar.text_input("사용자 ID")
    password = st.sidebar.text_input("비밀번호", type='password')

    if st.sidebar.button("로그인"):
        if authenticate_user(user_id, password):
            st.session_state['user_id'] = user_id  # 로그인 상태를 세션에 저장
            st.success(f"{user_id}님, 환영합니다!")
            st.rerun()  # 로그인 후 페이지 새로고침
        else:
            st.error("로그인 정보가 올바르지 않습니다.")

# 로그아웃 함수
def logout():
    if st.sidebar.button("로그아웃"):
        st.session_state.pop('user_id', None)  # 세션에서 user_id 삭제
        st.success("로그아웃되었습니다.")
        st.rerun()  # 로그아웃 후 페이지 새로고침
