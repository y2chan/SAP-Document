import streamlit as st
from user_auth import login, logout
from db_connection import get_db_connection

def create_document():
    st.header("문서 생성")
    if 'user_id' not in st.session_state:
        st.warning("로그인이 필요합니다.")
        return

    user_id = st.session_state['user_id']
    document_type = st.selectbox("문서 유형", ["매출", "매입", "지급"])
    company_code = st.text_input("회사 코드")
    document_date = st.date_input("문서 일자")
    posting_date = st.date_input("전기 일자")
    currency = st.text_input("통화 코드", value="KRW")
    reference = st.text_input("참조 번호")
    header_text = st.text_area("헤더 텍스트")

    # 문서 항목 입력
    st.subheader("문서 항목")
    item_data = []
    item_number = 1
    while True:
        st.write(f"항목 {item_number}")
        gl_account = st.text_input(f"계정 코드 ({item_number})", key=f"gl_account_{item_number}")
        debit_credit_indicator = st.selectbox(f"차변/대변 ({item_number})", ["D", "C"], key=f"d_c_{item_number}")
        amount = st.number_input(f"금액 ({item_number})", min_value=0.0, key=f"amount_{item_number}")
        text = st.text_input(f"항목 텍스트 ({item_number})", key=f"text_{item_number}")
        cost_center = st.text_input(f"코스트 센터 ({item_number})", key=f"cost_center_{item_number}")
        profit_center = st.text_input(f"프로핏 센터 ({item_number})", key=f"profit_center_{item_number}")
        assignment = st.text_input(f"지정 ({item_number})", key=f"assignment_{item_number}")

        item_data.append({
            "item_number": item_number,
            "gl_account": gl_account,
            "debit_credit_indicator": debit_credit_indicator,
            "amount": amount,
            "text": text,
            "cost_center": cost_center,
            "profit_center": profit_center,
            "assignment": assignment
        })

        add_more = st.checkbox("항목 추가", key=f"add_more_{item_number}")
        if not add_more:
            break
        item_number += 1

    if st.button("문서 제출"):
        connection = get_db_connection()
        cursor = connection.cursor()

        # 문서 헤더 저장
        document_sql = """
            INSERT INTO document_header 
            (document_type, company_code, document_date, posting_date, currency, reference, header_text, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        document_data = (document_type, company_code, document_date, posting_date, currency, reference, header_text, user_id)
        cursor.execute(document_sql, document_data)
        document_id = cursor.lastrowid

        # 문서 항목 저장
        for item in item_data:
            item_sql = """
                INSERT INTO document_item
                (document_id, item_number, gl_account, debit_credit_indicator, amount, text, cost_center, profit_center, assignment)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            item_values = (
                document_id, item['item_number'], item['gl_account'], item['debit_credit_indicator'],
                item['amount'], item['text'], item['cost_center'], item['profit_center'], item['assignment']
            )
            cursor.execute(item_sql, item_values)

        # CTS에 문서 추가
        cts_sql = "INSERT INTO cts (document_id) VALUES (%s)"
        cursor.execute(cts_sql, (document_id,))
        connection.commit()
        cursor.close()
        connection.close()

        st.success("문서가 성공적으로 제출되었습니다. 승인 대기 중입니다.")

# 문서 승인 함수
def approve_document():
    st.header("문서 승인")
    if 'user_id' not in st.session_state:
        st.warning("로그인이 필요합니다.")
        return

    user_id = st.session_state['user_id']

    # 관리자 권한 확인
    if user_id != 'admin':
        st.error("권한이 없습니다. 관리자만 문서를 승인할 수 있습니다.")
        return

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT cts.cts_id, document_header.*, user.name
        FROM cts
        JOIN document_header ON cts.document_id = document_header.document_id
        JOIN user ON document_header.created_by = user.user_id
        WHERE cts.status = 'Pending'
    """)
    documents = cursor.fetchall()

    if documents:
        for document in documents:
            st.subheader(f"문서 ID: {document['document_id']}")
            st.write(f"문서 유형: {document['document_type']}")
            st.write(f"생성자: {document['name']} ({document['created_by']})")
            st.write(f"문서 일자: {document['document_date']}")
            st.write(f"전기 일자: {document['posting_date']}")
            st.write(f"통화: {document['currency']}")
            st.write(f"헤더 텍스트: {document['header_text']}")

            # 문서 항목 표시
            cursor.execute("SELECT * FROM document_item WHERE document_id = %s", (document['document_id'],))
            items = cursor.fetchall()
            for item in items:
                st.write(f"- 항목 번호: {item['item_number']}, 계정 코드: {item['gl_account']}, 금액: {item['amount']}, 차변/대변: {item['debit_credit_indicator']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"승인 (ID: {document['document_id']})"):
                    approval_sql = """
                        UPDATE cts SET status = 'Approved', approver_id = %s, approval_date = NOW()
                        WHERE document_id = %s
                    """
                    cursor.execute(approval_sql, (user_id, document['document_id']))
                    document_status_sql = "UPDATE document_header SET status = 'Approved' WHERE document_id = %s"
                    cursor.execute(document_status_sql, (document['document_id'],))
                    connection.commit()
                    st.success(f"문서 ID {document['document_id']}가 승인되었습니다.")
                    st.experimental_rerun()
            with col2:
                if st.button(f"반려 (ID: {document['document_id']})"):
                    rejection_sql = """
                        UPDATE cts SET status = 'Rejected', approver_id = %s, approval_date = NOW()
                        WHERE document_id = %s
                    """
                    cursor.execute(rejection_sql, (user_id, document['document_id']))
                    document_status_sql = "UPDATE document_header SET status = 'Rejected' WHERE document_id = %s"
                    cursor.execute(document_status_sql, (document['document_id'],))
                    connection.commit()
                    st.warning(f"문서 ID {document['document_id']}가 반려되었습니다.")
                    st.experimental_rerun()
    else:
        st.info("대기 중인 문서가 없습니다.")
    cursor.close()
    connection.close()

# 메인 함수
def main():
    st.title("SAP Web 전표 시스템")

    # 세션 상태에서 로그인 확인
    if 'user_id' not in st.session_state:
        login()  # 로그인 화면
    else:
        # 로그인 후 사이드바에 사용자 정보 및 로그아웃 버튼 표시
        st.sidebar.write(f"로그인 사용자: {st.session_state['user_id']}")
        logout()

        # 사이드바 메뉴
        st.sidebar.title("메뉴")
        menu = ["문서 생성", "문서 승인"]
        choice = st.sidebar.radio("옵션을 선택하세요", menu)

        # 선택된 메뉴에 따라 화면 표시
        if choice == "문서 생성":
            create_document()
        elif choice == "문서 승인":
            approve_document()

if __name__ == '__main__':
    main()