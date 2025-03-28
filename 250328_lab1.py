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

# .env 파일 로드
load_dotenv()

# 페이지 설정
st.set_page_config(page_title="스팀게임분석 서비스", layout="wide")

# matplotlib 전역 한글 폰트 설정 추가
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows 기본 한글 폰트
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

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
            port=int(os.getenv("DB_PORT", 3306))
        )
        return connection
    except mysql.connector.Error as err:
        st.error(f"데이터베이스 연결 오류: {err}")
        return None

# SIMILAR_GAMES 데이터베이스 연결 함수
@st.cache_data
def fetch_similar_games(base_app_id):
    connection = get_db_connection()
    if not connection:
        return pd.DataFrame()
    try:
        cursor = connection.cursor(dictionary=True)
        # SIMILAR_GAMES에서 데이터 조회
        query = """
        SELECT recommended_app_id, recommended_title, user_tags
        FROM SIMILAR_GAMES
        WHERE base_app_id = %s
        """
        cursor.execute(query, (base_app_id,))
        results = cursor.fetchall()

        # TAGS 테이블에서 tag_id와 tag_name 매핑
        cursor.execute("SELECT tag_id, tag_name FROM TAGS")
        tag_results = cursor.fetchall()
        tag_id_to_name = {tag['tag_id']: tag['tag_name'] for tag in tag_results}

        if results:
            df = pd.DataFrame(results)
            # user_tags를 태그 이름으로 변환
            def map_tags(tag_json):
                try:
                    tag_ids = json.loads(tag_json) if isinstance(tag_json, str) else tag_json
                    return [tag_id_to_name.get(int(tid), str(tid)) for tid in tag_ids]
                except:
                    return []
            df["tags"] = df["user_tags"].apply(map_tags)
            df["link"] = df["recommended_app_id"].apply(lambda x: f"https://store.steampowered.com/app/{x}")
            return df[["recommended_app_id", "recommended_title", "tags", "link"]]
        return pd.DataFrame(columns=["recommended_app_id", "recommended_title", "tags", "link"])
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

# 캐싱된 타이틀 가져오기
@st.cache_data
def fetch_titles_by_tags(selected_tags):
    connection = get_db_connection()
    if not connection:
        return pd.DataFrame()

    try:
        cursor = connection.cursor(dictionary=True)

        # TAGS 테이블에서 모든 tag_id와 tag_name 조회
        cursor.execute("SELECT tag_id, tag_name FROM TAGS")
        tag_results = cursor.fetchall()
        tag_id_to_name = {tag['tag_id']: tag['tag_name'] for tag in tag_results}

        # 선택된 태그 이름에 해당하는 tag_id 조회
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
            return pd.DataFrame()

        # TITLELIST에서 데이터 조회
        query = """
        SELECT app_id, name, user_tags, userScore
        FROM TITLELIST
        WHERE {conditions}
        """
        conditions = " AND ".join([f"JSON_CONTAINS(user_tags, %s)" for _ in selected_tag_ids])
        cursor.execute(query.format(conditions=conditions), [str(id) for id in selected_tag_ids])
        results = cursor.fetchall()

        df = pd.DataFrame(results)
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
            df["positive_keywords"] = [[] for _ in range(len(df))]
            df["negative_keywords"] = [[] for _ in range(len(df))]
            df["reviews"] = [[] for _ in range(len(df))]
            df = df.drop_duplicates(subset=["app_id"]).reset_index(drop=True)
        return df
    except mysql.connector.Error as err:
        st.error(f"쿼리 실행 오류: {err}")
        return pd.DataFrame()
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
menu_options = ["홈 대시보드", "태그나 유저 리뷰 키워드 ", "유저 리뷰 키워드 내 타이틀 분포", "타이틀 상세"]

for option in menu_options:
    is_selected = option == selected_menu
    button_class = "sidebar-button sidebar-button-selected" if is_selected else "sidebar-button sidebar-button-unselected"
    if st.sidebar.button(option, key=option, help=f"{option} 페이지로 이동", use_container_width=True):
        if option != selected_menu:
            st.session_state["page_history"].append(option)
        st.session_state["selected_menu"] = option
        if option == "태그나 유저 리뷰 키워드 ":
            st.session_state["selected_tag"] = None
        st.rerun()  # 메뉴 이동 시 상태 반영
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

# 예시 데이터 (트렌딩/핫)
example_trending = [
    {"name": "Dota 2", "app_id": 570, "link": "https://store.steampowered.com/app/570", "rating": 90.5, "tags": ["MOBA", "Strategy"]},
    {"name": "League of Legends", "app_id": 99999, "link": "https://store.steampowered.com/app/99999", "rating": 88.0, "tags": ["MOBA", "Action"]}
]
example_hot = [
    {"name": "Stardew Valley", "app_id": 413150, "link": "https://store.steampowered.com/app/413150", "rating": 95.0, "tags": ["Indie", "RPG"]},
    {"name": "Among Us", "app_id": 945360, "link": "https://store.steampowered.com/app/945360", "rating": 92.0, "tags": ["Indie", "Multiplayer"]}
]

# 뒤로 가기 함수
def go_back():
    if len(st.session_state["page_history"]) > 1:
        st.session_state["page_history"].pop()
        st.session_state["selected_menu"] = st.session_state["page_history"][-1]
    else:
        st.session_state["selected_menu"] = "홈 대시보드"
        st.session_state["page_history"] = ["홈 대시보드"]

# 두 개 이상의 태그가 선택되었는지 확인
if len(selected_tags) < 2:
    st.warning("두 개 이상의 태그를 선택해야 대시보드가 표시됩니다.")
else:
    # 데이터 가져오기
    df_titles = fetch_titles_by_tags(selected_tags)
    filtered_titles = df_titles.to_dict("records") if not df_titles.empty else []

    # 메인 제목
    st.markdown("<h1 style='text-align: center;'>스팀게임분석 서비스</h1>", unsafe_allow_html=True)

    # 메뉴에 따라 다른 프레임 렌더링
    if selected_menu == "홈 대시보드":
        if not filtered_titles:
            st.warning("선택한 태그에 해당하는 타이틀이 없습니다.")
        else:
            col5, col6, col7 = st.columns([1, 1, 1])

            with col5:
                st.subheader("인기 게임의 태그 분포")
                trending_df = pd.DataFrame(example_trending)
                hot_df = pd.DataFrame(example_hot)
                example_df = pd.concat([trending_df, hot_df], ignore_index=True)
                all_tags_example = example_df["tags"].explode().dropna()
                tag_counts = all_tags_example.value_counts()
                if not tag_counts.empty:
                    tag_cloud = WordCloud(width=400, height=200, background_color="white").generate_from_frequencies(tag_counts)
                    plt.figure(figsize=(5, 3))
                    plt.imshow(tag_cloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("태그 데이터가 없습니다.")

            with col6:
                st.subheader("Trending Game (예시)")
                df_trending = pd.DataFrame(example_trending)
                search_term = st.text_input("제목 또는 App ID로 검색 (트렌딩)", "")
                if search_term:
                    df_trending = df_trending[
                        df_trending["name"].str.contains(search_term, case=False, na=False) |
                        df_trending["app_id"].astype(str).str.contains(search_term, na=False)
                    ]
                # 세션 상태 초기화
                if "edited_trending" not in st.session_state:
                    df_trending["선택"] = False
                    st.session_state["edited_trending"] = df_trending[["선택", "name", "app_id", "link", "rating", "tags"]]
                # 편집 가능한 데이터프레임
                edited_trending = st.data_editor(
                    st.session_state["edited_trending"],
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", default=False),
                        "name": "타이틀",
                        "app_id": "App ID",
                        "link": st.column_config.LinkColumn("링크"),
                        "rating": "유저 점수",
                        "tags": "태그"
                    },
                    height=200,
                    use_container_width=True,
                    key="trending_editor"
                )
                st.session_state["edited_trending"] = edited_trending
                if st.button("상세 보기 (트렌딩)", key="trending_detail_button"):
                    selected_indices = edited_trending[edited_trending["선택"]].index
                    if not selected_indices.empty:
                        selected_title = edited_trending.iloc[selected_indices[0]]
                        st.session_state["selected_title"] = df_trending.iloc[selected_indices[0]].to_dict()
                        st.session_state["page_history"].append("타이틀 상세")
                        st.session_state["selected_menu"] = "타이틀 상세"
                        # 체크 상태 초기화
                        st.session_state["edited_trending"]["선택"] = False
                        st.rerun()

            with col7:
                st.subheader("Hot Game (예시)")
                df_hot = pd.DataFrame(example_hot)
                search_term_hot = st.text_input("제목 또는 App ID로 검색 (핫)", "")
                if search_term_hot:
                    df_hot = df_hot[
                        df_hot["name"].str.contains(search_term_hot, case=False, na=False) |
                        df_hot["app_id"].astype(str).str.contains(search_term_hot, na=False)
                    ]
                # 세션 상태 초기화
                if "edited_hot" not in st.session_state:
                    df_hot["선택"] = False
                    st.session_state["edited_hot"] = df_hot[["선택", "name", "app_id", "link", "rating", "tags"]]
                # 편집 가능한 데이터프레임
                edited_hot = st.data_editor(
                    st.session_state["edited_hot"],
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택", default=False),
                        "name": "타이틀",
                        "app_id": "App ID",
                        "link": st.column_config.LinkColumn("링크"),
                        "rating": "유저 점수",
                        "tags": "태그"
                    },
                    height=200,
                    use_container_width=True,
                    key="hot_editor"
                )
                st.session_state["edited_hot"] = edited_hot
                if st.button("상세 보기 (핫)", key="hot_detail_button"):
                    selected_indices = edited_hot[edited_hot["선택"]].index
                    if not selected_indices.empty:
                        selected_title = edited_hot.iloc[selected_indices[0]]
                        st.session_state["selected_title"] = df_hot.iloc[selected_indices[0]].to_dict()
                        st.session_state["page_history"].append("타이틀 상세")
                        st.session_state["selected_menu"] = "타이틀 상세"
                        # 체크 상태 초기화
                        st.session_state["edited_hot"]["선택"] = False
                        st.rerun()

            st.markdown("---")
            col8, col9 = st.columns([1, 1])

            with col8:
                st.subheader("태그별 작품 수 총합계 (Nivo Pie 차트)")
                chart_data = [
                    {"id": tag, "label": tag, "value": fetch_titles_by_tags([tag]).shape[0]}
                    for tag in selected_tags
                ]
                if sum(item["value"] for item in chart_data) > 0:
                    with elements("nivo_pie_chart"):
                        with mui.Box(sx={"height": 450}):
                            nivo.Pie(
                                data=chart_data,
                                margin={"top": 40, "right": 100, "bottom": 100, "left": 100},
                                innerRadius=0.4,
                                padAngle=1.0,
                                cornerRadius=5,
                                activeOuterRadiusOffset=10,
                                borderWidth=2,
                                borderColor={"from": "color", "modifiers": [["darker", 0.3]]},
                                arcLinkLabelsSkipAngle=8,
                                arcLinkLabelsTextColor="#333333",
                                arcLinkLabelsThickness=3,
                                arcLinkLabelsColor={"from": "color", "modifiers": [["darker", 0.5]]},
                                arcLinkLabel="label",
                                arcLabelsSkipAngle=8,
                                arcLabelsTextColor="#ffffff",
                                arcLabel=lambda d: f"{d.value}",
                                colors={"scheme": "category10"},
                                # 텍스트 크기 조정 시도
                                theme={
                                    "labels": {"text": {"fontSize": 18}},  # 파이 조각 안 텍스트 크기
                                    "arcLinkLabels": {"text": {"fontSize": 16}},  # 링크 라벨 텍스트 크기
                                    "legends": {"text": {"fontSize": 16}}  # 범례 텍스트 크기
                                },
                                legends=[
                                    {
                                        "anchor": "bottom",
                                        "direction": "row",
                                        "justify": False,
                                        "translateX": 0,
                                        "translateY": 70,
                                        "itemsSpacing": 10,
                                        "itemWidth": 120,
                                        "itemHeight": 20,
                                        "itemTextColor": "#333333",
                                        "symbolSize": 20,
                                        "symbolShape": "circle",
                                        "effects": [
                                            {"on": "hover", "style": {"itemTextColor": "#000000"}}
                                        ]
                                    }
                                ]
                            )
                else:
                    st.warning("선택한 태그에 해당하는 작품이 없습니다.")

            with col9:
                st.subheader("선택한 장르별 타이틀 리스트")
                if not df_titles.empty:
                    st.write("**👇체크박스를 선택 후 버튼을 눌러 상세 보기로 이동하세요.**")
                    df_titles = df_titles.reset_index(drop=True)
                    # 태그 변경 시 세션 상태 업데이트
                    if "edited_titles" not in st.session_state or st.session_state.get("last_selected_tags") != selected_tags:
                        df_titles["선택"] = False
                        st.session_state["edited_titles"] = df_titles[["선택", "name", "app_id", "rating", "tags"]]
                        st.session_state["last_selected_tags"] = selected_tags
                    # 편집 가능한 데이터프레임
                    edited_titles = st.data_editor(
                        st.session_state["edited_titles"],
                        column_config={
                            "선택": st.column_config.CheckboxColumn("선택", default=False),
                            "name": "타이틀",
                            "app_id": "App ID",
                            "rating": "유저 점수",
                            "tags": "태그"
                        },
                        height=200,
                        use_container_width=True,
                        key="titles_editor"
                    )
                    st.session_state["edited_titles"] = edited_titles
                    if st.button("상세 보기 (태그별)", key="tag_title_detail_button"):
                        selected_indices = edited_titles[edited_titles["선택"]].index
                        if not selected_indices.empty:
                            selected_title = df_titles.iloc[selected_indices[0]]
                            st.session_state["selected_title"] = selected_title.to_dict()
                            st.session_state["page_history"].append("타이틀 상세")
                            st.session_state["selected_menu"] = "타이틀 상세"
                            # 체크 상태 초기화
                            st.session_state["edited_titles"]["선택"] = False
                            st.rerun()

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_home"):
                go_back()
                st.rerun()

    elif selected_menu == "태그나 유저 리뷰 키워드 ":
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
            all_positive_keywords = []
            all_negative_keywords = []
            for title in tag_titles:
                all_positive_keywords.extend(title["positive_keywords"])
                all_negative_keywords.extend(title["negative_keywords"])

            if not all_positive_keywords and not all_negative_keywords:
                st.warning(f"선택된 태그 '{selected_tag}'에 해당하는 리뷰 키워드가 없습니다.")
            else:
                # 전역 변수 업데이트
                positive_keywords_set.clear()
                positive_keywords_set.update(all_positive_keywords)
                negative_keywords_set.clear()
                negative_keywords_set.update(all_negative_keywords)

                all_keywords = all_positive_keywords + all_negative_keywords
                keyword_counts = pd.Series(all_keywords).value_counts()

                keyword_df = pd.DataFrame({
                    "키워드": keyword_counts.index,
                    "빈도": keyword_counts.values,
                    "유형": ["긍정" if kw in positive_keywords_set and kw not in negative_keywords_set else "부정" for kw in keyword_counts.index]
                })

                st.write("### 키워드 필터링")
                filter_option = st.multiselect(
                    "유형 선택",
                    options=["긍정", "부정"],
                    default=["긍정", "부정"]
                )

                filtered_df = keyword_df[keyword_df["유형"].isin(filter_option)]

                col10, col11 = st.columns(2)

                with col10:
                    st.markdown("### 리뷰 전체에 대한 워드 클라우드")
                    if not filtered_df.empty:
                        filtered_counts = filtered_df.set_index("키워드")["빈도"].to_dict()
                        wordcloud = WordCloud(
                            width=500,
                            height=300,
                            background_color="white",
                            color_func=color_func,
                            font_path="C:/Windows/Fonts/malgun.ttf"
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
                            filtered_df.style.format({"빈도": "{:.0f}"}),
                            height=300,
                            use_container_width=True
                        )
                    else:
                        st.write("표시할 키워드 데이터가 없습니다.")

                st.markdown("### 키워드 버블 차트")
                if not filtered_df.empty:
                    fig = px.scatter(
                        filtered_df,
                        x="키워드",
                        y="유형",
                        size="빈도",
                        color="유형",
                        color_discrete_map={"긍정": "green", "부정": "red"},
                        hover_data=["빈도"],
                        size_max=60,
                        title="키워드 빈도 분석"
                    )
                    fig.update_layout(
                        xaxis_title="키워드",
                        yaxis_title="유형",
                        height=400,
                        width=1000
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("표시할 키워드 데이터가 없습니다.")

                col_left, col_right = st.columns([3, 1])
                with col_right:
                    if st.button("각 리뷰 타이틀 분포 보기", key="to_title_distribution"):
                        st.session_state["page_history"].append("유저 리뷰 키워드 내 타이틀 분포")
                        st.session_state["selected_menu"] = "유저 리뷰 키워드 내 타이틀 분포"
                        st.rerun()

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_keywords"):
                go_back()
                st.rerun()

    elif selected_menu == "유저 리뷰 키워드 내 타이틀 분포":
        st.subheader("리뷰 키워드 내 타이틀 분포")

        all_positive_keywords = []
        all_negative_keywords = []
        for title in filtered_titles:
            all_positive_keywords.extend(title["positive_keywords"])
            all_negative_keywords.extend(title["negative_keywords"])
        unique_keywords = list(set(all_positive_keywords + all_negative_keywords))

        positive_keywords_set.clear()
        positive_keywords_set.update(all_positive_keywords)
        negative_keywords_set.clear()
        negative_keywords_set.update(all_negative_keywords)

        st.write("### 키워드 유형 선택")
        type_category = st.multiselect(
            "유형 카테고리",
            options=["전체", "긍정", "부정"],
            default=["전체"]
        )

        st.write("### 키워드 선택")
        selected_keywords = st.multiselect(
            "리뷰 키워드 선택",
            options=unique_keywords,
            default=[]
        )

        keyword_titles = []
        seen_app_ids = set()
        if "전체" in type_category and not selected_keywords:
            for title in filtered_titles:
                if title["app_id"] not in seen_app_ids:
                    keyword_titles.append({
                        "name": title["name"],
                        "app_id": title["app_id"],
                        "link": title["link"],
                        "rating": title["rating"],
                        "tags": title["tags"],
                        "positive_keywords": title["positive_keywords"],
                        "negative_keywords": title["negative_keywords"],
                        "keyword_score": len(title["positive_keywords"]) + len(title["negative_keywords"])
                    })
                    seen_app_ids.add(title["app_id"])
        else:
            for title in filtered_titles:
                if title["app_id"] in seen_app_ids:
                    continue
                relevant_keywords = []
                if "전체" in type_category or ("긍정" in type_category and "부정" in type_category):
                    relevant_keywords = title["positive_keywords"] + title["negative_keywords"]
                elif "긍정" in type_category:
                    relevant_keywords = title["positive_keywords"]
                elif "부정" in type_category:
                    relevant_keywords = title["negative_keywords"]

                if selected_keywords:
                    if all(kw in relevant_keywords for kw in selected_keywords):
                        keyword_count = sum(relevant_keywords.count(kw) for kw in selected_keywords)
                        keyword_titles.append({
                            "name": title["name"],
                            "app_id": title["app_id"],
                            "link": title["link"],
                            "rating": title["rating"],
                            "tags": title["tags"],
                            "positive_keywords": title["positive_keywords"],
                            "negative_keywords": title["negative_keywords"],
                            "keyword_score": keyword_count
                        })
                        seen_app_ids.add(title["app_id"])
                else:
                    keyword_count = len(relevant_keywords)
                    if keyword_count > 0:
                        keyword_titles.append({
                            "name": title["name"],
                            "app_id": title["app_id"],
                            "link": title["link"],
                            "rating": title["rating"],
                            "tags": title["tags"],
                            "positive_keywords": title["positive_keywords"],
                            "negative_keywords": title["negative_keywords"],
                            "keyword_score": keyword_count
                        })
                        seen_app_ids.add(title["app_id"])

        if not keyword_titles:
            st.warning(f"선택된 조건 '{', '.join(type_category)}'와 키워드 '{', '.join(selected_keywords)}'에 해당하는 타이틀이 없습니다.")
        else:
            sorted_titles = sorted(keyword_titles, key=lambda x: x["keyword_score"], reverse=True)
            df = pd.DataFrame(sorted_titles).reset_index(drop=True)
            # 세션 상태 초기화
            if "edited_keyword_titles" not in st.session_state:
                df["선택"] = False
                st.session_state["edited_keyword_titles"] = df[["선택", "name", "app_id", "link", "rating", "tags", "positive_keywords", "negative_keywords", "keyword_score"]]
            # 편집 가능한 데이터프레임
            edited_df = st.data_editor(
                st.session_state["edited_keyword_titles"],
                column_config={
                    "선택": st.column_config.CheckboxColumn("선택", default=False),
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
                key="keyword_titles_editor"
            )
            st.session_state["edited_keyword_titles"] = edited_df

            st.subheader(f"'{', '.join(type_category)}' 유형 및 '{', '.join(selected_keywords)}' 키워드를 포함한 타이틀 목록")
            if st.button("상세 보기 (키워드 분포)", key="keyword_dist_detail_button"):
                selected_indices = edited_df[edited_df["선택"]].index
                if not selected_indices.empty:
                    selected_title = edited_df.iloc[selected_indices[0]]
                    st.session_state["selected_title"] = df.iloc[selected_indices[0]].to_dict()
                    st.session_state["page_history"].append("타이틀 상세")
                    st.session_state["selected_menu"] = "타이틀 상세"
                    # 체크 상태 초기화
                    st.session_state["edited_keyword_titles"]["선택"] = False
                    st.rerun()

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_title_dist"):
                go_back()
                st.rerun()

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
                "링크": [title_info["link"]],
                "평점": [title_info["rating"]],
                "태그": [", ".join(title_info["tags"])],
                "주요 리뷰 키워드 (긍정)": [", ".join(title_info["positive_keywords"])],
                "주요 리뷰 키워드 (부정)": [", ".join(title_info["negative_keywords"])]
            }
            df_table = pd.DataFrame(table_data)

            st.dataframe(
                df_table,
                column_config={
                    "타이틀": "타이틀",
                    "링크": st.column_config.LinkColumn("링크"),
                    "평점": "평점",
                    "태그": "태그",
                    "주요 리뷰 키워드 (긍정)": "주요 리뷰 키워드 (긍정)",
                    "주요 리뷰 키워드 (부정)": "주요 리뷰 키워드 (부정)"
                },
                use_container_width=True
            )

            # 추천 게임 표 추가
            st.subheader("추천 게임 목록")
            similar_games_df = fetch_similar_games(title_info["app_id"])
            if not similar_games_df.empty:
                st.dataframe(
                    similar_games_df,
                    column_config={
                        "recommended_app_id": "추천 App ID",
                        "recommended_title": "추천 타이틀",
                        "tags": "태그",
                        "link": st.column_config.LinkColumn("링크")
                    },
                    height=300,
                    use_container_width=True
                )
            else:
                st.write("이 게임에 대한 추천 게임이 없습니다.")

            positive_reviews = []
            negative_reviews = []
            for review in title_info["reviews"]:
                review_lower = review.lower()
                positive_count = sum(review_lower.count(kw.lower()) for kw in title_info["positive_keywords"])
                negative_count = sum(review_lower.count(kw.lower()) for kw in title_info["negative_keywords"])
                if positive_count > negative_count:
                    positive_reviews.append({"text": review, "keyword_count": positive_count})
                elif negative_count > positive_count:
                    negative_reviews.append({"text": review, "keyword_count": negative_count})

            positive_reviews = sorted(positive_reviews, key=lambda x: x["keyword_count"], reverse=True)
            negative_reviews = sorted(negative_reviews, key=lambda x: x["keyword_count"], reverse=True)

            st.subheader("리뷰 키워드 워드 클라우드")
            col7, col8 = st.columns(2)
            with col7:
                st.write("긍정 키워드 워드 클라우드")
                if title_info["positive_keywords"]:
                    positive_cloud = WordCloud(width=400, height=200, background_color="white").generate(" ".join(title_info["positive_keywords"]))
                    plt.figure(figsize=(5, 3))
                    plt.imshow(positive_cloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("긍정 키워드가 없습니다.")
            with col8:
                st.write("부정 키워드 워드 클라우드")
                if title_info["negative_keywords"]:
                    negative_cloud = WordCloud(width=400, height=200, background_color="white").generate(" ".join(title_info["negative_keywords"]))
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
                st.rerun()

    elif selected_menu == "용어 정리 (팝업)":
        st.subheader("용어를 선택하세요")
        glossary = [
            "게임에 붙어있는 태그로, 개발사가 지정한 태그가 아닌 유저가 지정한 태그입니다.",
            "유저가 남긴 리뷰에서 추출한 키워드로, 특정 게임에 대해 유저들이 장단점으로 인지하는 부분을 나타냅니다.",
            "특정 태그를 가진 타이틀들이 그 외에 어떤 태그를 가지고 있는지를 보여줍니다.",
            "정해진 태그들을 모두 가지고 있는 타이틀들에 대한 리뷰 키워드의 분포를 나타냅니다.",
            "특정 리뷰 키워드를 가진 타이틀들을 모두 보여줍니다.",
            "특정 타이틀에 대한 상세 정보를 보여줍니다."
        ]
        selected_term = st.selectbox("👇", ["태그", "리뷰 키워드", "태그 분포", "태그 내 리뷰 키워드 분포", "리뷰 키워드 내 타이틀 분포", "타이틀 상세"])
        st.markdown(f"{glossary[list(['태그', '리뷰 키워드', '태그 분포', '태그 내 리뷰 키워드 분포', '리뷰 키워드 내 타이틀 분포', '타이틀 상세']).index(selected_term)]}")

        st.markdown("---")
        col_back, col_empty = st.columns([1, 4])
        with col_back:
            if st.button("뒤로 가기", key="back_glossary"):
                go_back()
                st.rerun()