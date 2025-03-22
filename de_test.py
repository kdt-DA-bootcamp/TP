import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pymysql

# 페이지 설정
st.set_page_config(layout="centered")

# CSS 스타일 (변경 없음)
st.markdown("""
    <style>
        html { scroll-behavior: smooth; }
        .fade-in { animation: fadeIn 2s ease-in forwards; opacity: 0; }
        @keyframes fadeIn { 0% { opacity: 0; } 100% { opacity: 1; } }
        .content { margin-top: 50px; padding: 20px; background-color: #f0f0f0; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); max-width: 800px; margin-left: auto; margin-right: auto; }
        .intro { text-align: center; padding: 50px; background-color: #e0e7ff; margin-bottom: 20px; border-radius: 10px; max-width: 800px; margin-left: auto; margin-right: auto; }
        .stButton>button { width: 100%; margin-top: 10px; transition: all 0.3s ease; }
        .stButton>button:hover { background-color: #1E88E5; color: white; }
    </style>
""", unsafe_allow_html=True)

# DB 연결 함수 (변경 없음)
def get_db_connection():
    try:
        return pymysql.connect(
            host=st.secrets["db"]["host"],
            port=st.secrets["db"]["port"],
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        st.error(f"DB 연결 오류: {str(e)}")
        return None

# DB에서 게임 타이틀 가져오기 (app_id를 문자열로 처리)
def fetch_game_titles_from_db():
    connection = get_db_connection()
    if connection is None:
        return []
    try:
        with connection.cursor() as cursor:
            query = "SELECT DISTINCT app_id, name FROM TITLELIST WHERE name IS NOT NULL AND app_id IS NOT NULL"
            cursor.execute(query)
            result = cursor.fetchall()
            # app_id를 문자열로 변환
            game_data = [{'app_id': str(row['app_id']), 'Title': row['name']} for row in result]
        return game_data
    except Exception as e:
        st.error(f"DB 쿼리 오류: {str(e)}")
        return []
    finally:
        connection.close()

# CSV 데이터 로드 (app_id를 문자열로 처리하고 소수점 제거)
try:
    df = pd.read_csv('keyword_sentiment.csv')
    df['Keywords'] = df['Keywords'].str.split(', ')
    df = df.explode('Keywords')
    df['Keywords'] = df['Keywords'].str.strip()
    # app_id를 문자열로 변환하고 소수점 제거
    df['app_id'] = df['app_id'].astype(str).str.replace('.0', '', regex=False)
except FileNotFoundError:
    df = pd.DataFrame()

# 세션 상태 초기화 (변경 없음)
if 'page' not in st.session_state:
    st.session_state.page = 'intro'
if 'selected_keyword' not in st.session_state:
    st.session_state.selected_keyword = None
if 'selected_title' not in st.session_state:
    st.session_state.selected_title = None
if 'title_list_df' not in st.session_state:
    st.session_state.title_list_df = None

# 페이지 제목 (변경 없음)
st.title('게임 개발 서비스 프로토타입')

# 사이드바에 전체 메뉴 추가 (변경 없음)
with st.sidebar:
    st.title("전체 메뉴")
    if st.button("전체 메뉴"):
        st.session_state.show_menu = not st.session_state.get('show_menu', False)
    
    if st.session_state.get('show_menu', False):
        st.subheader("Sprint 1: 키워드 분석")
        if st.button("긍정/부정 키워드"):
            st.session_state.page = 'main'
            st.rerun()
        if st.button("공통 키워드"):
            st.session_state.page = 'keywords'
            st.rerun()
        
        st.subheader("Sprint 2: (예정)")
        st.subheader("Sprint 3: (예정)")
        st.subheader("Sprint 4: (예정)")

# 소개 페이지 (변경 없음)
if st.session_state.page == 'intro':
    st.markdown("""
    <div class="intro fade-in">
        <h1>Trend Analysis via Steam Review</h1>
        <p>Steam 마켓을 분석하여 게임 시장/장르의 트렌드를 파악합니다</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="content fade-in">
        <h2>프로젝트 목표</h2>
        <p>- <b>Steam 마켓 분석</b>: Steam DB와 Steam API를 주 활용하여 데이터를 수집하며, 크롤링은 최소화.</p>
        <p>- <b>게임 시장/장르</b>: 특정 장르의 트렌드에 초점을 맞춰 분석.</p>
        <p>- <b>트렌드 파악</b>: 현재 트렌드와 변화 경향을 도출.</p>
        <h3>왜 Steam DB와 API인가?</h3>
        <p>- Steam DB로 메타데이터(장르, 타이틀 등)를 효율적으로 수집.</p>
        <p>- Steam API로 리뷰 데이터를 보완, 키워드 분석 수행.</p>
    </div>
    """, unsafe_allow_html=True)
    
    fig_intro = go.Figure(data=[go.Bar(
        x=['Steam DB', 'Steam API', '크롤링'],
        y=[70, 25, 5],
        marker_color=['#1E88E5', '#42A5F5', '#90CAF9']
    )])
    fig_intro.update_layout(title="데이터 소스 비율 (예시)", font=dict(family="Malgun Gothic", size=14), height=300)
    st.plotly_chart(fig_intro, use_container_width=True)

    st.markdown("""
    <div class="content fade-in">
        <h2>분석 방안</h2>
        <p>1. <b>타이틀 강점/약점 분석</b><br> - 리뷰에서 긍정/부정 키워드 추출 (Sprint 1 완료).</p>
        <p>2. <b>장르별 확장</b><br> - 유사 장르 게임 추천 시스템 개발 중 (Sprint 2 진행 중).</p>
        <p>3. <b>시장 트렌드</b><br> - 장르 간 비교로 전체 트렌드 파악 (예정).</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="content fade-in">
        <h2>타겟 사용자</h2>
        <p>- <b>개발자</b>: 게임 강점/약점 분석으로 개발 인사이트 제공.</p>
        <p>- <b>플레이어</b>: 유사 장르 게임 추천으로 즐길 게임 제안.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="content fade-in">
        <h2>고민</h2>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("분석 페이지로 이동"):
        st.session_state.page = 'main'
        st.rerun()

    st.markdown("""
    <div style="height: 1000px;"></div>
    <a href="#top">위로 돌아가기</a>
    """, unsafe_allow_html=True)

# 메인 페이지 (변경 없음)
elif st.session_state.page == 'main':
    st.write("두 카테고리를 모두 선택해주세요.")
    col1, col2 = st.columns(2)
    with col1:
        category1 = st.selectbox('장르 1 선택', [''] + ['Indie', 'MOBA'], key='category1')
    with col2:
        category2 = st.selectbox('장르 2 선택', [''] + ['Indie', 'MOBA'], key='category2')

    if category1 and category2:
        if not df.empty:
            filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
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
                    if st.button("Show Positive Titles", key="pos_button"):
                        st.session_state.selected_keyword = selected_pos
                        st.session_state.page = 'app_list'
                        st.rerun()
                with col2:
                    st.plotly_chart(fig2, use_container_width=True)
                    selected_neg = st.radio("Select a Negative Keyword", neg_df['Keyword'], key="neg_radio")
                    if st.button("Show Negative Titles", key="neg_button"):
                        st.session_state.selected_keyword = selected_neg
                        st.session_state.page = 'app_list'
                        st.rerun()

                if st.button("Title List", key="to_title_list"):
                    st.session_state.page = 'title_list'
                    st.rerun()
        else:
            st.write("예시 키워드 데이터(CSV)가 없습니다.")
            if st.button("Title List", key="to_title_list_no_csv"):
                st.session_state.page = 'title_list'
                st.rerun()
    else:
        st.write("상단에서 카테고리를 모두 선택해주세요.")

# 공통 키워드 페이지 (변경 없음)
elif st.session_state.page == 'keywords':
    st.write("두 카테고리를 모두 선택해주세요.")
    col1, col2 = st.columns(2)
    with col1:
        category1 = st.selectbox('장르 1 선택', [''] + ['Indie', 'MOBA'], key='category1')
    with col2:
        category2 = st.selectbox('장르 2 선택', [''] + ['Indie', 'MOBA'], key='category2')

    if category1 and category2:
        if not df.empty:
            filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
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
                    if st.button("Show Positive Common Titles", key="pos_common_button"):
                        st.session_state.selected_keyword = selected_pos_common
                        st.session_state.page = 'app_list'
                        st.rerun()
                with col2:
                    st.plotly_chart(fig4, use_container_width=True)
                    selected_neg_common = st.radio("Select a Negative Common Keyword", neg_common_df['Keyword'], key="neg_common_radio")
                    if st.button("Show Negative Common Titles", key="neg_common_button"):
                        st.session_state.selected_keyword = selected_neg_common
                        st.session_state.page = 'app_list'
                        st.rerun()

                if st.button("뒤로 가기", key="back_to_main"):
                    st.session_state.page = 'main'
                    st.rerun()
                if st.button("홈으로 가기", key="home_from_keywords"):
                    st.session_state.page = 'main'
                    st.session_state.selected_keyword = None
                    st.session_state.selected_title = None
                    st.rerun()
                if st.button("Title List", key="to_title_list_from_keywords"):
                    st.session_state.page = 'title_list'
                    st.rerun()
        else:
            st.write("예시 키워드 데이터(CSV)가 없습니다.")
            if st.button("뒤로 가기", key="back_to_main_no_csv"):
                st.session_state.page = 'main'
                st.rerun()
            if st.button("홈으로 가기", key="home_from_keywords_no_csv"):
                st.session_state.page = 'main'
                st.session_state.selected_keyword = None
                st.session_state.selected_title = None
                st.rerun()
            if st.button("Title List", key="to_title_list_no_csv_from_keywords"):
                st.session_state.page = 'title_list'
                st.rerun()
    else:
        st.write("상단에서 카테고리를 모두 선택해주세요.")

# Title 목록 페이지 (변경 없음)
elif st.session_state.page == 'app_list':
    st.write("두 카테고리를 모두 선택해주세요.")
    col1, col2 = st.columns(2)
    with col1:
        category1 = st.selectbox('장르 1 선택', [''] + ['Indie', 'MOBA'], key='category1')
    with col2:
        category2 = st.selectbox('장르 2 선택', [''] + ['Indie', 'MOBA'], key='category2')

    if category1 and category2:
        if not df.empty and st.session_state.selected_keyword:
            filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
            app_list_df = filtered_df[filtered_df['Keywords'] == st.session_state.selected_keyword][['app_id', 'Keywords', 'Sentiment']]
            st.markdown(f"<h3 style='font-weight: bold; font-size: 24px;'>Title List for Keyword: {st.session_state.selected_keyword}</h3>", unsafe_allow_html=True)
            st.dataframe(app_list_df)
            
            if st.button("뒤로 가기", key="back_to_app_list"):
                st.session_state.page = 'main' if st.session_state.page == 'main' else 'keywords'
                st.session_state.selected_keyword = None
                st.rerun()
            if st.button("홈으로 가기", key="home_from_app_list"):
                st.session_state.page = 'main'
                st.session_state.selected_keyword = None
                st.session_state.selected_title = None
                st.rerun()
        else:
            st.write("키워드를 선택해 주세요." if not df.empty else "예시 키워드 데이터(CSV)가 없습니다.")
    else:
        st.write("상단에서 카테고리를 모두 선택해주세요.")

# 전체 Title 리스트 페이지 (app_id 타입 일치 수정)
elif st.session_state.page == 'title_list':
    st.write("두 카테고리를 모두 선택해주세요.")
    col1, col2 = st.columns(2)
    with col1:
        category1 = st.selectbox('장르 1 선택', [''] + ['Indie', 'MOBA'], key='category1')
    with col2:
        category2 = st.selectbox('장르 2 선택', [''] + ['Indie', 'MOBA'], key='category2')

    if category1 and category2:
        game_data_from_db = fetch_game_titles_from_db()
        if game_data_from_db:
            st.session_state.title_list_df = pd.DataFrame(game_data_from_db)
            if not df.empty:
                filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
                positive_counts = filtered_df[filtered_df['Sentiment'] == 'positive'].groupby('app_id').size().reset_index(name='positive_keywords')
                negative_counts = filtered_df[filtered_df['Sentiment'] == 'negative'].groupby('app_id').size().reset_index(name='negative_keywords')
                # app_id를 문자열로 유지
                positive_counts['app_id'] = positive_counts['app_id'].astype(str)
                negative_counts['app_id'] = negative_counts['app_id'].astype(str)
                st.session_state.title_list_df['app_id'] = st.session_state.title_list_df['app_id'].astype(str)
                st.session_state.title_list_df = st.session_state.title_list_df.merge(positive_counts, on='app_id', how='left').merge(negative_counts, on='app_id', how='left')
                st.session_state.title_list_df['positive_keywords'] = st.session_state.title_list_df['positive_keywords'].fillna(0).astype(int)
                st.session_state.title_list_df['negative_keywords'] = st.session_state.title_list_df['negative_keywords'].fillna(0).astype(int)
            else:
                st.session_state.title_list_df['positive_keywords'] = 0
                st.session_state.title_list_df['negative_keywords'] = 0
            
            st.markdown(f"<div style='display: flex; justify-content: space-between;'><span>FILTER: {category1} & {category2}</span><span># of title: {len(st.session_state.title_list_df):,}</span></div>", unsafe_allow_html=True)
            st.markdown("<h3 style='font-weight: bold; font-size: 24px;'>Title List</h3>", unsafe_allow_html=True)
            
            search_term = st.text_input("Title 또는 App ID 검색 (예시 데이터 572220을 검색하셔요)", "")
            detail_button = st.button("상세정보", key="detail_button")
            
            display_df = st.session_state.title_list_df
            if search_term:
                display_df = display_df[
                    display_df['Title'].str.contains(search_term, case=False, na=False) |
                    display_df['app_id'].str.contains(search_term, case=False, na=False)
                ]
                if display_df.empty:
                    st.write("검색 결과가 없습니다.")
            
            st.write("👇 아래 표에서 행을 클릭해 선택한 후 상세정보 버튼을 누르세요!")
            selected = st.dataframe(
                display_df[['app_id', 'Title', 'positive_keywords', 'negative_keywords']],
                height=400,
                use_container_width=True,
                column_config={
                    "app_id": "App ID",
                    "Title": "Title",
                    "positive_keywords": "Positive Keywords",
                    "negative_keywords": "Negative Keywords"
                },
                selection_mode="single-row",
                on_select="rerun"
            )
            
            if detail_button and selected['selection']['rows']:
                selected_row = selected['selection']['rows'][0]
                st.session_state.selected_title = display_df.iloc[selected_row]['Title']
                st.session_state.page = 'app_detail'
                st.rerun()
            
            if st.button("뒤로 가기", key="back_to_title_list"):
                st.session_state.page = 'main'
                st.rerun()
            if st.button("홈으로 가기", key="home_from_title_list"):
                st.session_state.page = 'main'
                st.session_state.selected_keyword = None
                st.session_state.selected_title = None
                st.rerun()
        else:
            st.write("DB에서 데이터를 가져오지 못했습니다.")
    else:
        st.write("상단에서 카테고리를 모두 선택해주세요.")

# Title 상세 정보 페이지 (app_id 타입 일치 수정)
elif st.session_state.page == 'app_detail':
    st.write("두 카테고리를 모두 선택해주세요.")
    col1, col2 = st.columns(2)
    with col1:
        category1 = st.selectbox('장르 1 선택', [''] + ['Indie', 'MOBA'], key='category1')
    with col2:
        category2 = st.selectbox('장르 2 선택', [''] + ['Indie', 'MOBA'], key='category2')

    if category1 and category2:
        if st.session_state.selected_title:
            title = st.session_state.selected_title
            st.markdown(f"<h2 style='font-weight: bold; font-size: 28px;'>{title}</h2>", unsafe_allow_html=True)

            connection = get_db_connection()
            additional_info = {}
            recommended_games = []
            if connection:
                try:
                    with connection.cursor() as cursor:
                        query = """
                            SELECT user_tags, price_us, releaseYear, userScore 
                            FROM TITLELIST 
                            WHERE name = %s AND app_id = %s
                        """
                        selected_app_id = st.session_state.title_list_df[st.session_state.title_list_df['Title'] == title]['app_id'].iloc[0]
                        cursor.execute(query, (title, selected_app_id))
                        result = cursor.fetchone()
                        if result:
                            user_tags = result['user_tags']
                            if user_tags and user_tags.startswith('[') and user_tags.endswith(']'):
                                user_tags = user_tags.strip('[]').replace('"', '').replace("'", "")
                            else:
                                user_tags = "정보 없음"

                            additional_info = {
                                'user_tags': user_tags,
                                'price_us': f"${result['price_us']:.2f}" if result['price_us'] is not None else "정보 없음",
                                'releaseYear': result['releaseYear'] if result['releaseYear'] else "정보 없음",
                                'userScore': f"{result['userScore']:.1f}" if result['userScore'] is not None else "정보 없음"
                            }
                        else:
                            additional_info = {
                                'user_tags': "정보 없음",
                                'price_us': "정보 없음",
                                'releaseYear': "정보 없음",
                                'userScore': "정보 없음"
                            }

                        query_recommend = """
                            SELECT recommended_title 
                            FROM SIMILAR_GAMES 
                            WHERE base_app_id = %s
                        """
                        cursor.execute(query_recommend, (selected_app_id,))
                        recommend_result = cursor.fetchall()
                        recommended_games = [row['recommended_title'] for row in recommend_result if row['recommended_title']]

                except Exception as e:
                    st.error(f"DB 쿼리 오류: {str(e)}")
                finally:
                    connection.close()

            st.markdown(f"<h3 style='font-size: 20px;'>장르: {additional_info['user_tags']}</h3>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='font-size: 20px;'>가격: {additional_info['price_us']}</h3>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='font-size: 20px;'>출시 연도: {additional_info['releaseYear']}</h3>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='font-size: 20px;'>유저 점수: {additional_info['userScore']}</h3>", unsafe_allow_html=True)

            st.markdown("<h3 style='font-size: 20px;'>비슷한 추천 게임:</h3>", unsafe_allow_html=True)
            if recommended_games:
                recommended_df = pd.DataFrame(recommended_games, columns=["추천 게임"])
                st.dataframe(
                    recommended_df,
                    use_container_width=True,
                    height=200,
                    hide_index=True
                )
            else:
                st.markdown("<p>추천 게임이 없습니다.</p>", unsafe_allow_html=True)

            if not df.empty and st.session_state.title_list_df is not None:
                selected_app_id = st.session_state.title_list_df[st.session_state.title_list_df['Title'] == title]['app_id'].iloc[0]
                filtered_df = df[df['Sentiment'].isin(['positive', 'negative'])]
                # app_id를 문자열로 매핑
                app_data = filtered_df[filtered_df['app_id'] == str(selected_app_id)]

                if not app_data.empty:
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
           
            else:
                st.write("현재 키워드 데이터(CSV)가 없거나 Title 목록이 로드되지 않았습니다.")

            if st.button("뒤로 가기", key="back_to_titles"):
                st.session_state.page = 'title_list'
                st.session_state.selected_title = None
                st.rerun()
            if st.button("홈으로 가기", key="home_from_app_detail"):
                st.session_state.page = 'main'
                st.session_state.selected_keyword = None
                st.session_state.selected_title = None
                st.rerun()
        else:
            st.write("선택된 타이틀이 없습니다.")
            if st.button("뒤로 가기", key="back_no_selection"):
                st.session_state.page = 'title_list'
                st.rerun()
            if st.button("홈으로 가기", key="home_from_app_detail_no_selection"):
                st.session_state.page = 'main'
                st.session_state.selected_keyword = None
                st.session_state.selected_title = None
                st.rerun()
    else:
        st.write("상단에서 카테고리를 모두 선택해주세요.")