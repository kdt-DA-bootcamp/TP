import streamlit as st
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.express as px
import mysql.connector
from dotenv import load_dotenv
import os
import json
from streamlit_elements import elements, mui, nivo
import time

# .env 파일 로드 (로컬에서만)
if os.path.exists(".env"):
    load_dotenv()

# 페이지 설정
st.set_page_config(page_title="스팀게임분석 서비스", layout="wide")

# matplotlib 전역 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 전역 변수 초기화
positive_keywords_set = set()
negative_keywords_set = set()

# 데이터베이스 연결 함수
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT", 3306)),
            charset='utf8mb4',
            collation='utf8mb4_general_ci'
        )
        return connection
    except mysql.connector.Error as err:
        st.error(f"데이터베이스 연결 오류: {err.errno} - {err.msg}")
        return None

# SIMILAR_GAMES 데이터베이스 연결 함수
@st.cache_data
def fetch_similar_games(game_app_id):
    connection = get_db_connection()
    if not connection:
        return pd.DataFrame()
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT recommended_app_id, recommended_title, user_tags
        FROM SIMILAR_GAMES
        WHERE game_app_id = %s
        """
        cursor.execute(query, (game_app_id,))
        results = cursor.fetchall()

        cursor.execute("SELECT tag_id, tag_name FROM TAGS")
        tag_results = cursor.fetchall()
        tag_id_to_name = {tag['tag_id']: tag['tag_name'] for tag in tag_results}

        if results:
            df = pd.DataFrame(results)
            def map_tags(tag_json):
                try:
                    tag_ids = json.loads(tag_json) if isinstance(tag_json, str) else tag_json
                    return [tag_id_to_name.get(int(tid), str(tid)) for tid in tag_ids]
                except:
                    return []
            df["tags"] = df["user_tags"].apply(map_tags)
            df["link"] = df["recommended_app_id"].apply(lambda x: f"https://store.steampowered.com/app/{x}")
            return df[["recommended_title", "recommended_app_id", "tags", "link"]]
        return pd.DataFrame(columns=["recommended_title", "recommended_app_id", "tags", "link"])
    except mysql.connector.Error as err:
        st.error(f"추천 게임 조회 오류: {err}")
        return pd.DataFrame()
    finally:
        cursor.close()
        connection.close()

# 캐싱된 태그 목록 가져오기
@st.cache_data
def fetch_all_tags():
    connection = get_db_connection()
    if not connection:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT tag_name FROM TAGS")
        tags = [row[0] for row in cursor.fetchall()]
        return tags
    except mysql.connector.Error as err:
        st.error(f"태그 조회 오류: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

# REVIEW_TAG 테이블의 열 목록 동적으로 가져오기
@st.cache_data
def fetch_review_categories():
    connection = get_db_connection()
    if not connection:
        return []
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW COLUMNS FROM REVIEW_TAG")
        columns = [row[0] for row in cursor.fetchall()]
        excluded = {'id', 'app_id', 'review_id', 'review_text'}  # review_text 제외
        categories = [col for col in columns if col not in excluded]
        # 'game' 열이 누락되었는지 확인
        if 'game' not in categories and 'game' in columns:
            categories.append('game')
        return categories
    except mysql.connector.Error as err:
        st.error(f"리뷰 카테고리 조회 오류: {err}")
        return []
    finally:
        cursor.close()
        connection.close()

# 타이틀 및 리뷰 가져오기 (캐싱 추가 및 벡터화 최적화)
@st.cache_data(hash_funcs={list: lambda x: tuple(x)})
def fetch_titles_by_tags(selected_tags):
    start_time = time.time()  # 시간 측정은 남겨도 괜찮지만, 출력이 없으니 필요 없으면 이것도 지울 수 있어
    connection = get_db_connection()
    if not connection:
        return pd.DataFrame(), {}, {}
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT tag_id, tag_name FROM TAGS")
        tag_results = cursor.fetchall()
        tag_id_to_name = {tag['tag_id']: tag['tag_name'] for tag in tag_results}

        tag_id_query = """
        SELECT tag_id, tag_name
        FROM TAGS
        WHERE tag_name IN ({})
        """
        tag_placeholders = ','.join(['%s'] * len(selected_tags))
        cursor.execute(tag_id_query.format(tag_placeholders), selected_tags)
        selected_tag_results = cursor.fetchall()
        tag_id_map = {tag['tag_name']: tag['tag_id'] for tag in selected_tag_results}

        selected_tag_ids = [str(tag_id_map[tag]) for tag in selected_tags if tag in tag_id_map]
        if not selected_tag_ids:
            st.warning("선택한 태그에 해당하는 tag_id가 없습니다.")
            return pd.DataFrame(), {}, {}

        query = """
        SELECT app_id, name, user_tags, userScore
        FROM TITLELIST
        WHERE {conditions}
        """
        conditions = " AND ".join([f"JSON_CONTAINS(user_tags, %s)" for _ in selected_tag_ids])
        cursor.execute(query.format(conditions=conditions), [str(id) for id in selected_tag_ids])
        results = cursor.fetchall()

        categories = fetch_review_categories()
        review_query_cols = ", ".join(categories)
        review_query = f"""
        SELECT app_id, review_id, {review_query_cols}
        FROM REVIEW_TAG
        WHERE app_id IN (SELECT app_id FROM TITLELIST WHERE {conditions})
        """
        cursor.execute(review_query.format(conditions=conditions), [str(id) for id in selected_tag_ids])
        review_results = cursor.fetchall()

        df = pd.DataFrame(results)
        review_df = pd.DataFrame(review_results)

        if not df.empty:
            def map_tags(tag_json):
                try:
                    tag_ids = json.loads(tag_json) if isinstance(tag_json, str) else tag_json
                    return [tag_id_to_name.get(int(tid), str(tid)) for tid in tag_ids]
                except:
                    return []
            df["tags"] = df["user_tags"].apply(map_tags)
            df["rating"] = df["userScore"]
            df["link"] = df["app_id"].apply(lambda x: f"https://store.steampowered.com/app/{x}")

            # 모든 카테고리 열을 숫자형으로 변환
            review_df[categories] = review_df[categories].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)

            # 벡터화된 키워드 및 점수 계산
            pos_counts = review_df[categories].eq(1).groupby(review_df['app_id']).sum()
            neg_counts = review_df[categories].eq(-1).groupby(review_df['app_id']).sum()
            total_scores = review_df[categories].groupby(review_df['app_id']).sum().sum(axis=1)

            # 전체 리뷰 기반 빈도수 계산 (타이틀 단위가 아닌 리뷰 단위)
            global_pos_counts = review_df[categories].eq(1).sum().to_dict()
            global_neg_counts = review_df[categories].eq(-1).sum().to_dict()

            # app_id별 긍정/부정 키워드 리스트와 빈도 딕셔너리 생성
            df["positive_keywords"] = df["app_id"].map(lambda x: [cat for cat in categories if pos_counts.loc[x][cat] > 0] if x in pos_counts.index else [])
            df["negative_keywords"] = df["app_id"].map(lambda x: [cat for cat in categories if neg_counts.loc[x][cat] > 0] if x in neg_counts.index else [])
            df["keyword_score"] = df["app_id"].map(lambda x: total_scores[x] if x in total_scores.index else 0)
            df["positive_keyword_counts"] = df["app_id"].map(lambda x: pos_counts.loc[x].to_dict() if x in pos_counts.index else {})
            df["negative_keyword_counts"] = df["app_id"].map(lambda x: neg_counts.loc[x].to_dict() if x in neg_counts.index else {})
            df["reviews"] = df["app_id"].apply(lambda app_id: review_df[review_df["app_id"] == app_id]["review_text"].tolist() if "review_text" in review_df.columns else [])
            df = df.drop_duplicates(subset=["app_id"]).reset_index(drop=True)
            df = df[["name", "app_id", "rating", "tags", "link", "positive_keywords", "negative_keywords", "keyword_score", "positive_keyword_counts", "negative_keyword_counts", "reviews"]]
        
        return df, global_pos_counts, global_neg_counts  # 전체 빈도수 반환
    except mysql.connector.Error as err:
        st.error(f"쿼리 실행 오류: {err}")
        return pd.DataFrame(), {}, {}
    finally:
        cursor.close()
        connection.close()

# 워드 클라우드 색상 함수
def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    if word in positive_keywords_set:
        return "green"
    elif word in negative_keywords_set:
        return "red"
    return "black"

# 워드 클라우드 색상 및 크기 함수 (빈도 데이터를 인자로 받음)
def color_and_size_by_frequency(word, font_size, position, orientation, random_state=None, frequencies=None, **kwargs):
    count = frequencies.get(word, 0) if frequencies else 0
    if not frequencies or not frequencies.values():
        return "black"
    max_count = max(frequencies.values())
    min_count = min(frequencies.values())
    if max_count == min_count:
        return "#003087" if max_count > 0 else "black"
    
    range_size = (max_count - min_count) / 3
    threshold_high = max_count - range_size
    threshold_mid = max_count - 2 * range_size
    
    if count >= threshold_high:
        return "#003087"
    elif count >= threshold_mid:
        return "#005EB8"
    else:
        return "black"

def scale_font_size(word, font_size, frequencies=None, **kwargs):
    count = frequencies.get(word, 0) if frequencies else 0
    if not frequencies or not frequencies.values():
        return font_size
    max_count = max(frequencies.values())
    min_count = min(frequencies.values())
    if max_count == min_count:
        return int(font_size * 1.5) if max_count > 0 else font_size
    
    range_size = (max_count - min_count) / 3
    threshold_high = max_count - range_size
    
    if count >= threshold_high:
        return int(font_size * 1.5)
    return font_size

# 사이드바 메뉴 스타일링을 위한 CSS
st.markdown("""
    <style>
    .sidebar-button {
        width: 100%;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        text-align: left;
        cursor: pointer;
    }
    .sidebar-button-selected {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .sidebar-button-unselected {
        background-color: #f1f1f1;
        color: #333333;
    }
    .sidebar-button:hover {
        background-color: #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "selected_menu" not in st.session_state:
    st.session_state["selected_menu"] = "홈 대시보드"
if "page_history" not in st.session_state:
    st.session_state["page_history"] = ["홈 대시보드"]

# 사이드바 메뉴
st.sidebar.subheader("전체 메뉴")
selected_menu = st.session_state["selected_menu"]
menu_options = ["홈 대시보드", "태그 내 리뷰 키워드 분포 ", "리뷰 키워드 내 타이틀 분포", "타이틀 상세"]

for option in menu_options:
    is_selected = option == selected_menu
    button_class = "sidebar-button sidebar-button-selected" if is_selected else "sidebar-button sidebar-button-unselected"
    if st.sidebar.button(option, key=option, help=f"{option} 페이지로 이동", use_container_width=True):
        if option != selected_menu:
            st.session_state["page_history"].append(option)
        st.session_state["selected_menu"] = option
        if option == "태그 내 리뷰 키워드 분포 ":
            st.session_state["selected_tag"] = None
        st.rerun()
    st.sidebar.markdown(f"""
        <script>
        document.querySelector('button[kind="secondary"][data-testid="stButton"][data-key="{option}"]').className = "{button_class}";
        </script>
    """, unsafe_allow_html=True)

st.sidebar.subheader("용어 설명")
if st.sidebar.button("용어 정리", key="glossary"):
    if "용어 정리 (팝업)" != selected_menu:
        st.session_state["page_history"].append("용어 정리 (팝업)")
    st.session_state["selected_menu"] = "용어 정리 (팝업)"
    st.rerun()

# 데이터베이스에서 태그 목록 가져오기
all_tags = fetch_all_tags()
if not all_tags:
    all_tags = ["Indie", "MOBA"]

# 장르 선택
st.subheader("태그 선택")
col1, col2, col3, col4 = st.columns(4)
with col1:
    tag1 = st.selectbox("태그 1", all_tags, index=all_tags.index("Indie") if "Indie" in all_tags else 0, key="tag1")
with col2:
    options_tag2 = ["없음"] + all_tags
    tag2 = st.selectbox("태그 2", options_tag2, index=options_tag2.index("MOBA") if "MOBA" in options_tag2 else 0, key="tag2")
with col3:
    options_tag3 = ["없음"] + all_tags
    tag3 = st.selectbox("태그 3", options_tag3, index=0, key="tag3")
with col4:
    options_tag4 = ["없음"] + all_tags
    tag4 = st.selectbox("태그 4", options_tag4, index=0, key="tag4")

# 다중 태그 필터링 로직
selected_tags = [tag1]
if tag2 != "없음":
    selected_tags.append(tag2)
if tag3 != "없음":
    selected_tags.append(tag3)
if tag4 != "없음":
    selected_tags.append(tag4)

# 뒤로 가기 함수
def go_back():
    if len(st.session_state["page_history"]) > 1:
        st.session_state["page_history"].pop()
        st.session_state["selected_menu"] = st.session_state["page_history"][-1]
    else:
        st.session_state["selected_menu"] = "홈 대시보드"
        st.session_state["page_history"] = ["홈 대시보드"]
    st.rerun()

# 두 개 이상의 태그가 선택되었는지 확인
if len(selected_tags) < 2:
    st.warning("두 개 이상의 태그를 선택해야 대시보드가 표시됩니다.")
else:
    # 데이터 가져오기 (태그 변경 시 캐시 갱신 확인)
    df_titles, global_pos_counts, global_neg_counts = fetch_titles_by_tags(selected_tags)
    filtered_titles = df_titles.to_dict("records") if not df_titles.empty else []
    st.session_state["filtered_titles"] = filtered_titles
    st.session_state["last_selected_tags"] = selected_tags

    # 메인 제목
    st.markdown("<h1 style='text-align: center;'>스팀게임분석 서비스</h1>", unsafe_allow_html=True)

    # 메뉴에 따라 다른 프레임 렌더링
    if selected_menu == "홈 대시보드":
        if not filtered_titles:
            st.warning("선택한 태그에 해당하는 타이틀이 없습니다.")
        else:
            col5, col6 = st.columns(2)
            tag_counts = {}
            for title in filtered_titles:
                for tag in title["tags"]:
                    if tag not in selected_tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1

            with col5:
                st.subheader("선택한 태그 외 분포 (워드 클라우드)")
                if tag_counts:
                    font_path = "malgunbd.ttf"
                    wordcloud = WordCloud(
                        width=500,
                        height=300,
                        background_color="white",
                        font_path=font_path,
                        color_func=lambda *args, **kwargs: color_and_size_by_frequency(*args, frequencies=tag_counts, **kwargs),
                        prefer_horizontal=0.9,
                        scale=2,
                    ).generate_from_frequencies(tag_counts)
                    wordcloud.recolor(color_func=lambda *args, **kwargs: color_and_size_by_frequency(*args, frequencies=tag_counts, **kwargs))
                    for word in wordcloud.words_:
                        wordcloud.words_[word] = scale_font_size(word, wordcloud.words_[word], frequencies=tag_counts)
                    fig = plt.figure(figsize=(6, 4))
                    plt.imshow(wordcloud.to_array(), interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(fig)
                    plt.close(fig)
                else:
                    st.write("선택한 태그 외에 추가 태그가 없습니다.")

            with col6:
                st.subheader(f"선택한 태그 외 상위 15개 분포 (바 차트)")
                top_n = 15
                sorted_tag_counts = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:top_n])
                chart_data = [{"tag": tag, "count": count} for tag, count in sorted_tag_counts.items()]
                if chart_data and sum(d["count"] for d in chart_data) > 0:
                    with elements("nivo_bar_chart"):
                        with mui.Box(sx={"height": 550}):
                            nivo.Bar(
                                data=chart_data,
                                keys=["count"],
                                indexBy="tag",
                                margin={"top": 40, "right": 40, "bottom": 100, "left": 60},
                                padding={0.3},
                                valueScale={"type": "linear"},
                                indexScale={"type": "band", "round": True},
                                colors={"scheme": "category10"},
                                borderColor={"from": "color", "modifiers": [["darker", 1.6]]},
                                axisBottom={"tickSize": 5, "tickPadding": 5, "tickRotation": -35},
                                axisLeft={"tickSize": 5, "tickPadding": 5, "tickRotation": 0, "legend": "빈도", "legendPosition": "middle", "legendOffset": -50},
                                labelSkipWidth=12,
                                labelSkipHeight=12,
                                labelTextColor={"from": "color", "modifiers": [["darker", 2]]},
                                theme={"axis": {"ticks": {"text": {"fontSize": 14, "fontWeight": "bold"}}, "legend": {"text": {"fontSize": 16, "fontWeight": "bold"}}}, "labels": {"text": {"fontSize": 14, "fontWeight": "bold"}}},
                                animate=True,
                                motionStiffness=90,
                                motionDamping=15
                            )
                else:
                    st.warning("선택한 태그 외에 추가 태그가 없습니다.")

            st.markdown("""
                <style>
                div[data-testid="stHorizontalBlock"] div[data-testid="stTable"] {
                    width: 100% !important;
                    overflow-x: auto !important;
                }
                div[data-testid="stHorizontalBlock"] div[data-testid="stTable"] td:nth-child(1),
                div[data-testid="stHorizontalBlock"] div[data-testid="stTable"] td:nth-child(3),
                div[data-testid="stHorizontalBlock"] div[data-testid="stTable"] td:nth-child(4) {
                    width: 10px !important;
                    min-width: 10px !important;
                    max-width: 10px !important;
                }
                div[data-testid="stHorizontalBlock"] div[data-testid="stTable"] td:nth-child(2) {
                    width: 150px !important;
                    min-width: 150px !important;
                    max-width: 150px !important;
                }
                div[data-testid="stHorizontalBlock"] div[data-testid="stTable"] td:nth-child(5) {
                    min-width: 800px !important;
                    overflow-x: scroll !important;
                    white-space: nowrap !important;
                    padding: 0 !important;
                }
                div[data-testid="stHorizontalBlock"] div[data-testid="stTable"] td:nth-child(5) > div {
                    display: inline-block !important;
                    overflow-x: scroll !important;
                    white-space: nowrap !important;
                }
                </style>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("태그별 타이틀 리스트")
            if not df_titles.empty:
                st.write("**👇체크박스를 선택 후 버튼을 눌러 상세 보기로 이동하세요.**")
                df_titles = df_titles.reset_index(drop=True)
                current_tag_key = ''.join(selected_tags)
                if "last_tag_key" not in st.session_state or st.session_state["last_tag_key"] != current_tag_key:
                    df_titles["선택"] = False
                    st.session_state["edited_titles"] = df_titles[["선택", "name", "app_id", "rating", "tags"]]
                    st.session_state["last_tag_key"] = current_tag_key

                edited_titles = st.data_editor(
                    st.session_state["edited_titles"],
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", default=False, width=100),
                        "name": st.column_config.TextColumn("타이틀", width=150),
                        "app_id": st.column_config.NumberColumn("App ID", width=1),
                        "rating": st.column_config.NumberColumn("유저 점수", width=1),
                        "tags": st.column_config.ListColumn("태그", width=800)
                    },
                    height=400,
                    use_container_width=True,
                    key=f"titles_editor_{current_tag_key}"
                )
                st.session_state["edited_titles"] = edited_titles

                if st.button("상세 보기 (태그별)", key="tag_title_detail_button"):
                    selected_indices = edited_titles[edited_titles["선택"]].index
                    if not selected_indices.empty:
                        st.session_state["selected_title"] = df_titles.iloc[selected_indices[0]].to_dict()
                        st.session_state["page_history"].append("타이틀 상세")
                        st.session_state["selected_menu"] = "타이틀 상세"
                        st.session_state["edited_titles"]["선택"] = False
                        st.rerun()
            else:
                st.warning("선택한 태그에 해당하는 타이틀이 없습니다.")

    elif selected_menu == "태그 내 리뷰 키워드 분포 ":
        selected_tag = st.session_state.get("selected_tag", None)
        if selected_tag:
            st.subheader(f"태그: {selected_tag} - 리뷰 키워드 분석")
            tag_titles = [title for title in filtered_titles if selected_tag in title["tags"]]
        else:
            st.subheader("전체 리뷰 키워드 분석")
            tag_titles = filtered_titles

        if not tag_titles:
            st.warning(f"선택된 태그 '{selected_tag}'에 해당하는 타이틀이 없습니다.")
        else:
            categories = fetch_review_categories()

            # 전체 리뷰 기반 빈도수 사용 (Indie, MOBA 선택 시 수천 개 수준 복원)
            pos_counts = global_pos_counts
            neg_counts = global_neg_counts

            # 선택된 태그에 따라 필터링
            if selected_tag:
                pos_counts = {}
                neg_counts = {}
                for title in tag_titles:
                    for keyword, count in title["positive_keyword_counts"].items():
                        pos_counts[keyword] = pos_counts.get(keyword, 0) + count
                    for keyword, count in title["negative_keyword_counts"].items():
                        neg_counts[keyword] = neg_counts.get(keyword, 0) + count

            keyword_df = pd.DataFrame({
                "키워드": categories,
                "긍정 빈도": [pos_counts.get(cat, 0) for cat in categories],
                "부정 빈도": [neg_counts.get(cat, 0) for cat in categories]
            })
            keyword_df["유형"] = keyword_df.apply(lambda row: "긍정" if row["긍정 빈도"] > row["부정 빈도"] else "부정" if row["부정 빈도"] > row["긍정 빈도"] else "중립", axis=1)
            keyword_df["빈도"] = keyword_df.apply(lambda row: row["긍정 빈도"] if row["유형"] == "긍정" else row["부정 빈도"] if row["유형"] == "부정" else 0, axis=1)

            positive_keywords_set.clear()
            positive_keywords_set.update(keyword_df[keyword_df["유형"] == "긍정"]["키워드"])
            negative_keywords_set.clear()
            negative_keywords_set.update(keyword_df[keyword_df["유형"] == "부정"]["키워드"])

            filter_option = st.multiselect("유형 선택", options=["긍정", "부정"], default=["긍정", "부정"])
            filtered_df = keyword_df[keyword_df["유형"].isin(filter_option)]

            col10, col11 = st.columns(2)
            with col10:
                st.markdown("### 리뷰 전체에 대한 워드 클라우드")
                if not filtered_df.empty:
                    filtered_counts = filtered_df.set_index("키워드")["빈도"].to_dict()
                    wordcloud = WordCloud(
                        width=500,
                        height=200,
                        background_color="white",
                        font_path="malgunbd.ttf",
                        color_func=color_func
                    ).generate_from_frequencies(filtered_counts)
                    plt.figure(figsize=(6, 4))
                    plt.imshow(wordcloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("워드 클라우드를 생성할 키워드가 없습니다.")

            with col11:
                st.markdown("### 키워드 데이터 표")
                if not filtered_df.empty:
                    st.dataframe(
                        filtered_df[["키워드", "긍정 빈도", "부정 빈도", "유형"]].style.format({"긍정 빈도": "{:.0f}", "부정 빈도": "{:.0f}"}),
                        height=300,
                        use_container_width=True
                    )
                else:
                    st.write("표시할 키워드 데이터가 없습니다.")

            if "zoom_level" not in st.session_state:
                st.session_state.zoom_level = 7

            st.markdown("### 버블 차트")
            if not filtered_df.empty:
                fig = px.scatter(
                    filtered_df,
                    x="키워드",
                    y="유형",
                    size="빈도",
                    color="유형",
                    color_discrete_map={"긍정": "green", "부정": "red"},
                    hover_data=["긍정 빈도", "부정 빈도"],
                    size_max=200,
                    title="키워드 빈도 분석"
                )
                fig.update_layout(
                    xaxis=dict(range=[-st.session_state.zoom_level, len(filtered_df) + st.session_state.zoom_level]),
                    yaxis=dict(range=[-st.session_state.zoom_level, 2 + st.session_state.zoom_level]),
                    height=500,
                    width=800
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("표시할 키워드 데이터가 없습니다.")

            col_left, col_right = st.columns([3, 1])
            with col_right:
                if st.button("리뷰 키워드 내 타이틀 분포 페이지로 이동", key="to_title_distribution"):
                    st.session_state["page_history"].append("리뷰 키워드 내 타이틀 분포")
                    st.session_state["selected_menu"] = "리뷰 키워드 내 타이틀 분포"
                    st.rerun()

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_keywords"):
                go_back()

    elif selected_menu == "리뷰 키워드 내 타이틀 분포":
        st.subheader("리뷰 키워드 내 타이틀 분포")
        st.write(f"선택된 태그: {', '.join(selected_tags)}")

        all_positive_keywords = []
        all_negative_keywords = []
        for title in filtered_titles:
            unique_pos_keywords = list(set(title["positive_keywords"]))
            unique_neg_keywords = list(set(title["negative_keywords"]))
            all_positive_keywords.extend(unique_pos_keywords)
            all_negative_keywords.extend(unique_neg_keywords)
        unique_keywords = list(set(all_positive_keywords + all_negative_keywords))

        positive_keywords_set.clear()
        positive_keywords_set.update(all_positive_keywords)
        negative_keywords_set.clear()
        negative_keywords_set.update(all_negative_keywords)

        st.write("### 키워드 유형 선택")
        type_category = st.multiselect("유형 카테고리", options=["전체", "긍정", "부정"], default=["전체"])
        st.write("### 키워드 선택")
        selected_keywords = st.multiselect("리뷰 키워드 선택", options=unique_keywords, default=[])

        keyword_titles = []
        seen_app_ids = set()
        for title in filtered_titles:
            if title["app_id"] in seen_app_ids:
                continue

            relevant_keywords = []
            if "전체" in type_category:
                relevant_keywords = list(set(title["positive_keywords"] + title["negative_keywords"]))
            elif "긍정" in type_category and "부정" not in type_category:
                relevant_keywords = list(set(title["positive_keywords"]))
            elif "부정" in type_category and "긍정" not in type_category:
                relevant_keywords = list(set(title["negative_keywords"]))
            elif "긍정" in type_category and "부정" in type_category:
                relevant_keywords = list(set(title["positive_keywords"] + title["negative_keywords"]))

            include_title = False
            if selected_keywords:
                if relevant_keywords and all(kw in relevant_keywords for kw in selected_keywords):
                    include_title = True
            else:
                if relevant_keywords or title["keyword_score"] == 0:
                    include_title = True

            if include_title:
                keyword_count = title["keyword_score"] if not selected_keywords else len(selected_keywords)
                keyword_titles.append({
                    "name": title["name"],
                    "app_id": title["app_id"],
                    "link": title["link"],
                    "rating": title["rating"],
                    "tags": title["tags"],
                    "positive_keywords": list(set(title["positive_keywords"])),
                    "negative_keywords": list(set(title["negative_keywords"])),
                    "keyword_score": keyword_count,
                    "positive_keyword_counts": title["positive_keyword_counts"],
                    "negative_keyword_counts": title["negative_keyword_counts"]
                })
                seen_app_ids.add(title["app_id"])

        if not keyword_titles:
            st.warning(f"선택된 태그 '{', '.join(selected_tags)}'와 조건 '{', '.join(type_category)}', 키워드 '{', '.join(selected_keywords)}'에 해당하는 타이틀이 없습니다.")
        else:
            sorted_titles = sorted(keyword_titles, key=lambda x: x["keyword_score"], reverse=True)
            df = pd.DataFrame(sorted_titles).reset_index(drop=True)
            current_filter_key = f"{','.join(type_category)}_{','.join(selected_keywords)}_{''.join(selected_tags)}"
            if "edited_keyword_titles" not in st.session_state or st.session_state.get("last_filter_key") != current_filter_key:
                df["선택"] = False
                st.session_state["edited_keyword_titles"] = df[["선택", "name", "app_id", "link", "rating", "tags", "positive_keywords", "negative_keywords", "keyword_score"]]
                st.session_state["last_filter_key"] = current_filter_key
            
            edited_df = st.data_editor(
                st.session_state["edited_keyword_titles"],
                column_config={
                    "선택": st.column_config.CheckboxColumn("선택", default=False, width=50),
                    "name": "타이틀",
                    "app_id": "App ID",
                    "link": st.column_config.LinkColumn("링크"),
                    "rating": "점수",
                    "tags": "태그",
                    "positive_keywords": "긍정 키워드",
                    "negative_keywords": "부정 키워드",
                    "keyword_score": "키워드 점수"
                },
                height=300,
                use_container_width=True,
                key=f"keyword_titles_editor_{current_filter_key}"
            )
            st.session_state["edited_keyword_titles"] = edited_df

            if st.button("상세 보기 (키워드 분포)", key="keyword_dist_detail_button"):
                selected_indices = edited_df[edited_df["선택"]].index
                if not selected_indices.empty:
                    st.session_state["selected_title"] = df.iloc[selected_indices[0]].to_dict()
                    st.session_state["page_history"].append("타이틀 상세")
                    st.session_state["selected_menu"] = "타이틀 상세"
                    st.session_state["edited_keyword_titles"]["선택"] = False
                    st.rerun()

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_keyword_dist"):
                go_back()

    elif selected_menu == "타이틀 상세":
        st.subheader("타이틀 상세")
        st.write(f"🔎검색결과: '{len(filtered_titles)}' 개의 타이틀이 검색 되었습니다.")

        st.markdown("""
            <style>
            .stSelectbox [data-baseweb="select"] > div {
                max-width: 300px;
                overflow-x: auto;
            }
            </style>
        """, unsafe_allow_html=True)

        if filtered_titles:
            col1, col2 = st.columns([1, 3])
            with col1:
                title_options = {title["name"]: title for title in filtered_titles}
                selected_title_name = st.selectbox(
                    "타이틀 선택",
                    options=list(title_options.keys()),
                    index=0 if "selected_title" not in st.session_state else list(title_options.keys()).index(st.session_state["selected_title"]["name"]) if st.session_state["selected_title"]["name"] in title_options else 0,
                    key="title_dropdown"
                )
                title_info = title_options[selected_title_name]
                st.session_state["selected_title"] = title_info
        else:
            title_info = st.session_state.get("selected_title", None)
            if not title_info:
                st.warning("선택 가능한 타이틀이 없습니다.")
                st.stop()

        if title_info:
            table_data = {
                "타이틀": [title_info["name"]],
                "App ID": [title_info["app_id"]],
                "링크": [title_info["link"]],
                "평점": [title_info["rating"]],
                "태그": [", ".join(title_info["tags"])],
                "주요 리뷰 키워드 (긍정)": [", ".join(list(set(title_info["positive_keywords"])))],
                "주요 리뷰 키워드 (부정)": [", ".join(list(set(title_info["negative_keywords"])))],
                "키워드 점수": [title_info["keyword_score"]]
            }
            df_table = pd.DataFrame(table_data)
            st.dataframe(
                df_table,
                column_config={
                    "타이틀": "타이틀",
                    "App ID": "App ID",
                    "링크": st.column_config.LinkColumn("링크"),
                    "평점": "평점",
                    "태그": "태그",
                    "주요 리뷰 키워드 (긍정)": "주요 리뷰 키워드 (긍정)",
                    "주요 리뷰 키워드 (부정)": "주요 리뷰 키워드 (부정)",
                    "키워드 점수": "키워드 점수"
                },
                use_container_width=True
            )

            st.subheader("추천 게임 목록")
            similar_games_df = fetch_similar_games(title_info["app_id"])
            if not similar_games_df.empty:
                st.dataframe(
                    similar_games_df,
                    column_config={
                        "recommended_title": "추천 타이틀",
                        "recommended_app_id": "추천 App ID",
                        "tags": "태그",
                        "link": st.column_config.LinkColumn("링크")
                    },
                    height=300,
                    use_container_width=True
                )
            else:
                st.write("이 게임에 대한 추천 게임이 없습니다.")

            connection = get_db_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                categories = fetch_review_categories()
                review_query_cols = ", ".join(categories)
                review_query = f"""
                SELECT review_text, {review_query_cols}
                FROM REVIEW_TAG
                WHERE app_id = %s
                """
                cursor.execute(review_query, (title_info["app_id"],))
                reviews = cursor.fetchall()
                cursor.close()
                connection.close()

                positive_reviews = []
                negative_reviews = []
                score_categories = [cat for cat in categories if cat != "review_text"]
                for review in reviews:
                    score = sum([int(review[cat]) for cat in score_categories])
                    review_entry = {"text": review["review_text"], "keyword_count": abs(score)}
                    if score > 0:
                        positive_reviews.append(review_entry)
                    elif score < 0:
                        negative_reviews.append(review_entry)

                positive_reviews = sorted(positive_reviews, key=lambda x: x["keyword_count"], reverse=True)
                negative_reviews = sorted(negative_reviews, key=lambda x: x["keyword_count"], reverse=True)
            else:
                positive_reviews = []
                negative_reviews = []

            col7, col8 = st.columns(2)
            with col7:
                st.write("### 긍정 키워드 워드 클라우드")  # <h3> 또는 CSS 대신 ### 사용
                if title_info["positive_keywords"]:
                    positive_tag_counts = title_info["positive_keyword_counts"]
                    font_path = "malgunbd.ttf"
                    positive_cloud = WordCloud(
                        width=400,
                        height=200,
                        background_color="white",
                        font_path=font_path,
                        color_func=lambda *args, **kwargs: color_and_size_by_frequency(*args, frequencies=positive_tag_counts, **kwargs),
                        prefer_horizontal=0.9,
                        scale=2,
                    ).generate_from_frequencies(positive_tag_counts)
                    positive_cloud.recolor(color_func=lambda *args, **kwargs: color_and_size_by_frequency(*args, frequencies=positive_tag_counts, **kwargs))
                    for word in positive_cloud.words_:
                        positive_cloud.words_[word] = scale_font_size(word, positive_cloud.words_[word], frequencies=positive_tag_counts)
                    plt.figure(figsize=(5, 3))
                    plt.imshow(positive_cloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("긍정 키워드가 없습니다.")
            with col8:
                st.write("### 부정 키워드 워드 클라우드")  # <h3> 또는 CSS 대신 ### 사용
                if title_info["negative_keywords"]:
                    negative_tag_counts = title_info["negative_keyword_counts"]
                    font_path = "malgunbd.ttf"
                    negative_cloud = WordCloud(
                        width=400,
                        height=200,
                        background_color="white",
                        font_path=font_path,
                        color_func=lambda *args, **kwargs: color_and_size_by_frequency(*args, frequencies=negative_tag_counts, **kwargs),
                        prefer_horizontal=0.9,
                        scale=2,
                    ).generate_from_frequencies(negative_tag_counts)
                    negative_cloud.recolor(color_func=lambda *args, **kwargs: color_and_size_by_frequency(*args, frequencies=negative_tag_counts, **kwargs))
                    for word in negative_cloud.words_:
                        negative_cloud.words_[word] = scale_font_size(word, negative_cloud.words_[word], frequencies=negative_tag_counts)
                    plt.figure(figsize=(5, 3))
                    plt.imshow(negative_cloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("부정 키워드가 없습니다.")

            st.subheader("실제 리뷰 텍스트 원문 (키워드 빈도순)")
            col9, col10 = st.columns(2)
            with col9:
                st.write("### 긍정 리뷰")
                if positive_reviews:
                    positive_df = pd.DataFrame(positive_reviews, columns=["text", "keyword_count"])
                    positive_df.columns = ["리뷰 텍스트", "키워드 빈도"]
                    st.dataframe(
                        positive_df,
                        column_config={
                            "리뷰 텍스트": st.column_config.TextColumn("리뷰 텍스트", width="large"),
                            "키워드 빈도": st.column_config.NumberColumn("키워드 빈도", width="small")
                        },
                        height=300,
                        use_container_width=True
                    )
                else:
                    st.write("긍정 리뷰가 없습니다.")
            with col10:
                st.write("### 부정 리뷰")
                if negative_reviews:
                    negative_df = pd.DataFrame(negative_reviews, columns=["text", "keyword_count"])
                    negative_df.columns = ["리뷰 텍스트", "키워드 빈도"]
                    st.dataframe(
                        negative_df,
                        column_config={
                            "리뷰 텍스트": st.column_config.TextColumn("리뷰 텍스트", width="large"),
                            "키워드 빈도": st.column_config.NumberColumn("키워드 빈도", width="small")
                        },
                        height=300,
                        use_container_width=True
                    )
                else:
                    st.write("부정 리뷰가 없습니다.")

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_title_detail"):
                go_back()

    elif selected_menu == "용어 정리 (팝업)":
        st.subheader("용어를 선택하세요")
        glossary = [
            "게임에 붙어있는 태그로, 개발사가 지정한 태그가 아닌 유저가 지정한 태그입니다.",
            "유저가 남긴 리뷰에서 추출한 키워드로, 특정 게임에 대해 유저들이 장단점으로 인지하는 부분을 나타냅니다.",
            "선택한 태그들을 모두 가지고 있는 타이틀들에 대한 리뷰 키워드의 분포(전체, 필터링 된)를 나타냅니다.",
            "특정 리뷰 키워드를 가진 타이틀들을 모두 보여줍니다.",
            "특정 타이틀에 대한 상세 정보를 보여줍니다.\n \n 키워드 빈도란? 카테고리(Game,Story,Graphics,Sound,Content,Originality,Stability,ConvenienceGame) 리뷰 텍스트의 긍정/부정 점수를 계산하는 데 사용됩니다. \n \n 그 합계의 절대값이 '키워드 빈도'로 반영되어 리뷰를 빈도순으로 정렬됩니다. 이를 통해 유저가 어떤 측면을 많이 언급했는지 강조됩니다. \n \n •(긍정)score = 1 → keyword_count = 1 \n \n •(부정)score = -3 → keyword_count = 3 \n \n Game: 1, Story: 0, Graphics: -1, Sound: 1이라면, score = 1 + 0 + (-1) + 1 = 1. 이 합계가 양수면 긍정 리뷰, 음수면 부정 리뷰로 분류됩니다."]
        selected_term = st.selectbox("👇", ["태그", "리뷰 키워드", "태그 내 리뷰 키워드 분포", "리뷰 키워드 내 타이틀 분포", "타이틀 상세"])
        st.markdown(f"{glossary[list(['태그', '리뷰 키워드', '태그 내 리뷰 키워드 분포', '리뷰 키워드 내 타이틀 분포', '타이틀 상세']).index(selected_term)]}")

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_glossary"):
                go_back()
