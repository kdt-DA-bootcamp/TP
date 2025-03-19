import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pymysql

# AWS DB 연결 함수


def get_db_connection():
    return pymysql.connect(
        host=st.secrets["db"]["host"],
        port=st.secrets["db"]["port"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# DB에서 중복 제거된 app_id 가져오기
def fetch_app_ids_from_db():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = "SELECT DISTINCT app_id FROM GAME_REVIEW WHERE app_id IS NOT NULL"
            cursor.execute(query)
            result = cursor.fetchall()
            app_ids = [row['app_id'] for row in result]
        connection.close()
        return app_ids
    except Exception as e:
        st.error(f"DB 연결 오류: {str(e)}")
        return []

# 데이터 로드 (CSV는 그대로)
df = pd.read_csv('keyword_sentiment.csv')
df['Keywords'] = df['Keywords'].str.split(', ')
df = df.explode('Keywords')
df['Keywords'] = df['Keywords'].str.strip()

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = 'main'
if 'selected_keyword' not in st.session_state:
    st.session_state.selected_keyword = None
if 'selected_app_id' not in st.session_state:
    st.session_state.selected_app_id = None

st.title('게임 개발 서비스 프로토타입')
st.sidebar.write("두 카테고리를 모두 선택해주세요.")
category1 = st.sidebar.selectbox('장르 1 선택', [''] + ['Indie', 'MOBA'])
category2 = st.sidebar.selectbox('장르 2 선택', [''] + ['Indie', 'MOBA'])

# 메인 페이지
if st.session_state.page == 'main':
    if category1 and category2:
        filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
        if not filtered_df.empty:
            st.markdown(f"<div style='display: flex; justify-content: space-between;'><span>FILTER: {category1} & {category2}</span><span># of title: {len(filtered_df['app_id'].unique()):,}</span></div>", unsafe_allow_html=True)
            
            positive_df = filtered_df[filtered_df['Sentiment'] == 'positive']
            negative_df = filtered_df[filtered_df['Sentiment'] == 'negative']
            positive_keywords = positive_df['Keywords'].value_counts().head(4)
            negative_keywords = negative_df['Keywords'].value_counts().head(4)
            
            if positive_keywords.empty and negative_keywords.empty:
                st.write("키워드 데이터가 부족합니다.")
            else:
                pos_df = pd.DataFrame({'Keyword': positive_keywords.index, 'Count': positive_keywords.values})
                neg_df = pd.DataFrame({'Keyword': negative_keywords.index, 'Count': negative_keywords.values})

                fig1 = go.Figure(data=[go.Pie(labels=pos_df['Keyword'], values=pos_df['Count'], textinfo='label+percent', marker=dict(colors=['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB']), showlegend=False, hoverinfo='none')])
                fig1.update_layout(title="Positive Keyword", font=dict(family="Malgun Gothic", size=14))
                fig2 = go.Figure(data=[go.Pie(labels=neg_df['Keyword'], values=neg_df['Count'], textinfo='label+percent', marker=dict(colors=['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB']), showlegend=False, hoverinfo='none')])
                fig2.update_layout(title="Negative Keyword", font=dict(family="Malgun Gothic", size=14))

                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(fig1, use_container_width=True)
                    selected_pos = st.radio("Select a Positive Keyword", pos_df['Keyword'], key="pos_radio")
                    if st.button("Show Positive App IDs", key="pos_button"):
                        st.session_state.selected_keyword = selected_pos
                        st.session_state.page = 'app_list'
                        st.rerun()
                with col2:
                    st.plotly_chart(fig2, use_container_width=True)
                    selected_neg = st.radio("Select a Negative Keyword", neg_df['Keyword'], key="neg_radio")
                    if st.button("Show Negative App IDs", key="neg_button"):
                        st.session_state.selected_keyword = selected_neg
                        st.session_state.page = 'app_list'
                        st.rerun()

                if st.button("공통 키워드 보기", key="to_keywords"):
                    st.session_state.page = 'keywords'
                    st.rerun()
                if st.button("Title List", key="to_title_list"):
                    st.session_state.page = 'title_list'
                    st.rerun()
        else:
            st.write("조건에 맞는 데이터가 없습니다.")
    else:
        st.write("카테고리를 모두 선택해주세요.")

# 공통 키워드 페이지
elif st.session_state.page == 'keywords':
    if category1 and category2:
        filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
        if not filtered_df.empty:
            st.markdown(f"<div style='display: flex; justify-content: space-between;'><span>FILTER: {category1} & {category2}</span><span># of title: {len(filtered_df['app_id'].unique()):,}</span></div>", unsafe_allow_html=True)
            
            positive_df = filtered_df[filtered_df['Sentiment'] == 'positive']
            negative_df = filtered_df[filtered_df['Sentiment'] == 'negative']
            common_positive_keywords = positive_df['Keywords'].value_counts().head(3)
            common_negative_keywords = negative_df['Keywords'].value_counts().head(3)
            
            if common_positive_keywords.empty and common_negative_keywords.empty:
                st.write("공통 키워드 데이터가 부족합니다.")
            else:
                pos_common_df = pd.DataFrame({'Keyword': common_positive_keywords.index, 'Count': common_positive_keywords.values})
                neg_common_df = pd.DataFrame({'Keyword': common_negative_keywords.index, 'Count': common_negative_keywords.values})

                fig3 = go.Figure(data=[go.Pie(labels=pos_common_df['Keyword'], values=pos_common_df['Count'], textinfo='label+percent', marker=dict(colors=['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB']), showlegend=False, hoverinfo='none')])
                fig3.update_layout(title="Positive Keyword in Common", font=dict(family="Malgun Gothic", size=14))
                fig4 = go.Figure(data=[go.Pie(labels=neg_common_df['Keyword'], values=neg_common_df['Count'], textinfo='label+percent', marker=dict(colors=['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB']), showlegend=False, hoverinfo='none')])
                fig4.update_layout(title="Negative Keyword in Common", font=dict(family="Malgun Gothic", size=14))

                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(fig3, use_container_width=True)
                    selected_pos_common = st.radio("Select a Positive Common Keyword", pos_common_df['Keyword'], key="pos_common_radio")
                    if st.button("Show Positive Common App IDs", key="pos_common_button"):
                        st.session_state.selected_keyword = selected_pos_common
                        st.session_state.page = 'app_list'
                        st.rerun()
                with col2:
                    st.plotly_chart(fig4, use_container_width=True)
                    selected_neg_common = st.radio("Select a Negative Common Keyword", neg_common_df['Keyword'], key="neg_common_radio")
                    if st.button("Show Negative Common App IDs", key="neg_common_button"):
                        st.session_state.selected_keyword = selected_neg_common
                        st.session_state.page = 'app_list'
                        st.rerun()

                if st.button("뒤로 가기", key="back_to_main"):
                    st.session_state.page = 'main'
                    st.rerun()
        else:
            st.write("조건에 맞는 데이터가 없습니다.")
    else:
        st.write("카테고리를 모두 선택해주세요.")

# app_id 목록 페이지
elif st.session_state.page == 'app_list':
    if category1 and category2:
        filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
        if st.session_state.selected_keyword:
            app_list_df = filtered_df[filtered_df['Keywords'] == st.session_state.selected_keyword][['app_id', 'Keywords', 'Sentiment']]
            st.markdown(f"<h3 style='font-weight: bold; font-size: 24px;'>App ID List for Keyword: {st.session_state.selected_keyword}</h3>", unsafe_allow_html=True)
            st.dataframe(app_list_df)
            
            if st.button("뒤로 가기", key="back_to_app_list"):
                st.session_state.page = 'main' if st.session_state.page == 'main' else 'keywords'
                st.session_state.selected_keyword = None
                st.rerun()
        else:
            st.write("키워드를 선택해 주세요.")
    else:
        st.write("카테고리를 모두 선택해주세요.")

# Title List 페이지 (검색 기능 + 스크롤 테이블 추가)
elif st.session_state.page == 'title_list':
    if category1 and category2:
        app_ids_from_db = fetch_app_ids_from_db()
        if app_ids_from_db:
            title_list_df = pd.DataFrame({'app_id': app_ids_from_db})
            title_list_df['app_id'] = title_list_df['app_id'].astype(int)
            filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
            positive_counts = filtered_df[filtered_df['Sentiment'] == 'positive'].groupby('app_id').size().reset_index(name='positive_review')
            negative_counts = filtered_df[filtered_df['Sentiment'] == 'negative'].groupby('app_id').size().reset_index(name='negative_review')
            title_list_df = title_list_df.merge(positive_counts, on='app_id', how='left').merge(negative_counts, on='app_id', how='left')
            title_list_df['positive_review'] = title_list_df['positive_review'].fillna(0).astype(int)
            title_list_df['negative_review'] = title_list_df['negative_review'].fillna(0).astype(int)
            
            st.markdown(f"<div style='display: flex; justify-content: space-between;'><span>FILTER: {category1} & {category2}</span><span># of title: {len(title_list_df):,}</span></div>", unsafe_allow_html=True)
            st.markdown("<h3 style='font-weight: bold; font-size: 24px;'>Title List</h3>", unsafe_allow_html=True)
            
            st.markdown(
                    """
                    <style>
                    .search-container {
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        margin-bottom: 10px;
                    }
                    .stTextInput > div > div > input {
                        height: 38px;
                        width: 70%;
                    }
                    .stButton > button {
                        height: 38px;
                        width: 20%;
                    }
                    .stDataFrame > div > div {
                        max-height: 400px !important;
                        overflow-y: auto !important;
                        border: 1px solid #ccc;
                    }
                    /* 강화된 선택된 행 스타일 */
                    .stDataFrame [data-testid="stTable"] tr[data-selected="true"] {
                        background-color: #ffcc00 !important;  /* 선택된 행의 배경색 */
                        border: 3px solid #ff9900 !important;  /* 선택된 행의 테두리 색 */
                        box-shadow: 0 0 10px rgba(0, 0, 0, 0.4);  /* 선택된 행에 그림자 추가 */
                        color: #000000 !important;  /* 글씨 색상 검정 */
                        font-weight: bold;  /* 글씨 두껍게 */
                    }
                    /* 호버 시 배경색 변화 */
                    .stDataFrame [data-testid="stTable"] tr:hover {
                        background-color: #f0f0f0 !important;  /* 호버 시 더 연한 회색 */
                        cursor: pointer;  /* 커서를 포인터로 변경 */
                    }
                    /* 더 나은 테두리 강조 */
                    .stDataFrame [data-testid="stTable"] th {
                        background-color: #fafafa;  /* 헤더 배경 색상 */
                        font-weight: bold;
                        border: 1px solid #ccc;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )

            
            with st.container():
                st.markdown('<div class="search-container">', unsafe_allow_html=True)
                search_term = st.text_input("App ID 검색 (예: 40320)", "")
                detail_button = st.button("상세정보", key="detail_button")
                st.markdown('</div>', unsafe_allow_html=True)
            
            if search_term:
                title_list_df = title_list_df[title_list_df['app_id'].astype(str).str.contains(search_term, case=False)]
                if title_list_df.empty:
                    st.write("검색 결과가 없습니다.")
            
            st.markdown("<p style='font-weight: bold; color: #d81b60; font-size: 16px;'>👇 아래 표에서 행을 클릭해 선택한 후 상세정보 버튼을 누르세요!</p>", unsafe_allow_html=True)
            selected = st.dataframe(
                title_list_df[['app_id', 'positive_review', 'negative_review']],
                height=400,
                use_container_width=True,
                column_config={
                    "app_id": "App ID",
                    "positive_review": "Positive Keywords",
                    "negative_review": "Negative Keywords"
                },
                selection_mode="single-row",
                on_select="rerun"
            )
            
            if detail_button and selected['selection']['rows']:
                selected_row = selected['selection']['rows'][0]
                st.session_state.selected_app_id = title_list_df.iloc[selected_row]['app_id']
                st.session_state.page = 'app_detail'
                st.rerun()
            
            if st.button("뒤로 가기", key="back_to_title_list"):
                st.session_state.page = 'main'
                st.rerun()
        else:
            st.write("DB에서 데이터를 가져오지 못했습니다.")
    else:
        st.write("카테고리를 모두 선택해주세요.")

# 앱 상세 정보 페이지
elif st.session_state.page == 'app_detail':
    if st.session_state.selected_app_id:
        app_id = st.session_state.selected_app_id
        filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
        app_data = filtered_df[filtered_df['app_id'] == app_id]
        
        if not app_data.empty:
            st.markdown(f"<h2 style='font-weight: bold; font-size: 28px;'>{app_id}</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='font-size: 20px;'>장르: {category1}, {category2}</h3>", unsafe_allow_html=True)
            st.markdown("<p>게임 정보: 이 게임은 플레이어가 다양한 환경에서 모험을 즐길 수 있는 게임입니다. 다양한 캐릭터와 스토리를 경험해보세요.</p>", unsafe_allow_html=True)
            
            positive_data = app_data[app_data['Sentiment'] == 'positive']
            negative_data = app_data[app_data['Sentiment'] == 'negative']
            
            positive_keywords = positive_data['Keywords'].value_counts()
            positive_total = positive_keywords.sum() if not positive_keywords.empty else 0
            negative_keywords = negative_data['Keywords'].value_counts()
            negative_total = negative_keywords.sum() if not negative_keywords.empty else 0
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("<h3 style='font-weight: bold; color: #1E88E5;'>Positive Keywords</h3>", unsafe_allow_html=True)
                if not positive_keywords.empty:
                    pos_df = pd.DataFrame({
                        'Keyword': positive_keywords.index,
                        'Count': positive_keywords.values,
                        'Percentage': (positive_keywords.values / positive_total * 100).round(2)
                    })
                    pos_df['Percentage'] = pos_df['Percentage'].apply(lambda x: f"{x}%")
                    st.dataframe(pos_df)
                    
                    top5_pos = pos_df.head(5)
                    others_pos_count = pos_df['Count'][5:].sum() if len(pos_df) > 5 else 0
                    
                    if others_pos_count > 0:
                        pie_data_pos = pd.concat([
                            top5_pos,
                            pd.DataFrame({
                                'Keyword': ['기타'],
                                'Count': [others_pos_count],
                                'Percentage': [f"{(others_pos_count / positive_total * 100).round(2)}%"]
                            })
                        ])
                    else:
                        pie_data_pos = top5_pos
                    
                    fig_pos = go.Figure(data=[go.Pie(
                        labels=pie_data_pos['Keyword'], 
                        values=pie_data_pos['Count'], 
                        textinfo='label+percent',
                        marker=dict(colors=['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB', '#64B5F6', '#2196F3']),
                        showlegend=False
                    )])
                    fig_pos.update_layout(title="Top 5 Positive Keywords", font=dict(family="Malgun Gothic", size=14))
                    st.plotly_chart(fig_pos, use_container_width=True)
                else:
                    st.write("긍정적 키워드 데이터가 없습니다.")
            
            with col2:
                st.markdown("<h3 style='font-weight: bold; color: #E53935;'>Negative Keywords</h3>", unsafe_allow_html=True)
                if not negative_keywords.empty:
                    neg_df = pd.DataFrame({
                        'Keyword': negative_keywords.index,
                        'Count': negative_keywords.values,
                        'Percentage': (negative_keywords.values / negative_total * 100).round(2)
                    })
                    neg_df['Percentage'] = neg_df['Percentage'].apply(lambda x: f"{x}%")
                    st.dataframe(neg_df)
                    
                    top5_neg = neg_df.head(5)
                    others_neg_count = neg_df['Count'][5:].sum() if len(neg_df) > 5 else 0
                    
                    if others_neg_count > 0:
                        pie_data_neg = pd.concat([
                            top5_neg,
                            pd.DataFrame({
                                'Keyword': ['기타'],
                                'Count': [others_neg_count],
                                'Percentage': [f"{(others_neg_count / negative_total * 100).round(2)}%"]
                            })
                        ])
                    else:
                        pie_data_neg = top5_neg
                    
                    fig_neg = go.Figure(data=[go.Pie(
                        labels=pie_data_neg['Keyword'], 
                        values=pie_data_neg['Count'], 
                        textinfo='label+percent',
                        marker=dict(colors=['#E53935', '#EF5350', '#EF9A9A', '#FFCDD2', '#F44336', '#FF8A80']),
                        showlegend=False
                    )])
                    fig_neg.update_layout(title="Top 5 Negative Keywords", font=dict(family="Malgun Gothic", size=14))
                    st.plotly_chart(fig_neg, use_container_width=True)
                else:
                    st.write("부정적 키워드 데이터가 없습니다.")
            
            if st.button("뒤로 가기", key="back_to_titles"):
                st.session_state.page = 'title_list'
                st.session_state.selected_app_id = None
                st.rerun()
        else:
            st.write("선택한 앱에 대한 데이터가 없습니다.")
            if st.button("뒤로 가기", key="back_no_data"):
                st.session_state.page = 'title_list'
                st.session_state.selected_app_id = None
                st.rerun()
    else:
        st.write("선택된 앱이 없습니다.")
        if st.button("뒤로 가기", key="back_no_selection"):
            st.session_state.page = 'title_list'
            st.rerun()