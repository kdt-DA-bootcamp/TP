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

# .env 파일 로드
load_dotenv()

# 페이지 설정
st.set_page_config(page_title="스팀게임분석 서비스", layout="wide")

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

# 태그로 타이틀 가져오기
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
            # user_tags를 tag_name으로 변환
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
            # category는 예시로 사용하지 않음
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

# 사이드바 메뉴 선택
st.sidebar.subheader("전체 메뉴")
if "show_menu" not in st.session_state:
    st.session_state["show_menu"] = False

if "selected_menu" not in st.session_state:
    st.session_state["selected_menu"] = "홈 대시보드"
selected_menu = st.session_state["selected_menu"]

toggle_label = "메뉴 닫기" if st.session_state["show_menu"] else "메뉴 열기"
if st.sidebar.button(toggle_label, key="menu_toggle"):
    st.session_state["show_menu"] = not st.session_state["show_menu"]
    st.rerun()

if st.session_state["show_menu"]:
    menu_options = ["홈 대시보드", "태그나 유저 리뷰 키워드 ", "유저 리뷰 키워드 내 타이틀 분포", "타이틀 상세"]
    for option in menu_options:
        if st.sidebar.button(option, key=option):
            st.session_state["selected_menu"] = option
            if option == "태그나 유저 리뷰 키워드 ":
                st.session_state["selected_tag"] = None
            st.rerun()

st.sidebar.subheader("용어 설명")
if st.sidebar.button("용어 정리", key="glossary"):
    st.session_state["selected_menu"] = "용어 정리 (팝업)"
    selected_menu = "용어 정리 (팝업)"

# 장르 선택
st.subheader("장르 선택")
col1, col2, col3, col4 = st.columns(4)
with col1:
    tag1 = st.selectbox("태그 1", ["Indie", "MOBA"], index=0, key="tag1")  # 디폴트: Indie
with col2:
    tag2 = st.selectbox("태그 2", ["없음", "Indie", "MOBA"], index=2, key="tag2")  # 디폴트: MOBA (index=2로 수정)
with col3:
    tag3 = st.selectbox("태그 3", ["없음", "Indie", "MOBA"], index=0, key="tag3")  # 디폴트: 없음
with col4:
    tag4 = st.selectbox("태그 4", ["없음", "Indie", "MOBA"], index=0, key="tag4")  # 디폴트: 없음

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
                # 예시 데이터(trending + hot)에서 태그 추출
                trending_df = pd.DataFrame(example_trending)
                hot_df = pd.DataFrame(example_hot)
                example_df = pd.concat([trending_df, hot_df], ignore_index=True)
                all_tags = example_df["tags"].explode().dropna()
                tag_counts = all_tags.value_counts()
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

                selected_trending = st.dataframe(
                    df_trending[["name", "app_id", "link", "rating", "tags"]],
                    column_config={
                        "name": "타이틀",
                        "app_id": "App ID",
                        "link": st.column_config.LinkColumn("링크"),
                        "rating": "점수",
                        "tags": "태그"
                    },
                    height=200,
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun"
                )

                if st.button("상세정보 (Trending)", key="trending_detail"):
                    selected_rows = selected_trending.selection["rows"]
                    if selected_rows:
                        selected_title = df_trending.iloc[selected_rows[0]]
                        st.session_state["selected_title"] = selected_title.to_dict()
                        st.session_state["selected_menu"] = "타이틀 상세"
                        st.rerun()
                    else:
                        st.warning("타이틀을 선택해 주세요.")

            with col7:
                st.subheader("Hot Game (예시)")
                df_hot = pd.DataFrame(example_hot)

                search_term_hot = st.text_input("제목 또는 App ID로 검색 (핫)", "")
                if search_term_hot:
                    df_hot = df_hot[
                        df_hot["name"].str.contains(search_term_hot, case=False, na=False) |
                        df_hot["app_id"].astype(str).str.contains(search_term_hot, na=False)
                    ]

                selected_hot = st.dataframe(
                    df_hot[["name", "app_id", "link", "rating", "tags"]],
                    column_config={
                        "name": "타이틀",
                        "app_id": "App ID",
                        "link": st.column_config.LinkColumn("링크"),
                        "rating": "점수",
                        "tags": "태그"
                    },
                    height=200,
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun"
                )

                if st.button("상세정보 (Hot)", key="hot_detail"):
                    selected_rows = selected_hot.selection["rows"]
                    if selected_rows:
                        selected_title = df_hot.iloc[selected_rows[0]]
                        st.session_state["selected_title"] = selected_title.to_dict()
                        st.session_state["selected_menu"] = "타이틀 상세"
                        st.rerun()
                    else:
                        st.warning("타이틀을 선택해 주세요.")

            st.markdown("---")
            col8, col9 = st.columns([1, 1])

            with col8:
                st.subheader("장르별 총 합계 바 차트")
                chart_data = pd.DataFrame({
                    "태그": ["Indie", "MOBA"],
                    "작품 수": [fetch_titles_by_tags(["Indie"]).shape[0], fetch_titles_by_tags(["MOBA"]).shape[0]]
                })
                st.bar_chart(chart_data.set_index("태그"))

            with col9:
                st.subheader("선택한 장르별 타이틀 리스트")
                if not df_titles.empty:
                    st.write("**👇빈 칸을 눌러 선택 하세요. (미 선택시 전체통계)**")
                    selected_tag_title = st.dataframe(
                        df_titles[["name", "app_id", "rating", "tags"]],
                        column_config={
                            "name": "타이틀",
                            "app_id": "App ID",
                            "rating": "점수",
                            "tags": "태그"
                        },
                        height=200,
                        use_container_width=True,
                        selection_mode="single-row",
                        on_select="rerun"
                    )
                    
                    if st.button("선택한 장르 세부정보 보러가기", key="keyword_dist_all"):
                        st.session_state["selected_tag"] = None
                        st.session_state["selected_menu"] = "태그나 유저 리뷰 키워드 "
                        st.rerun()
                else:
                    st.write("선택한 장르에 해당하는 타이틀이 없습니다.")

    elif selected_menu == "태그나 유저 리뷰 키워드 ":
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False

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
                global positive_keywords_set, negative_keywords_set
                positive_keywords_set = set(all_positive_keywords)
                negative_keywords_set = set(all_negative_keywords)

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
                        st.session_state["selected_menu"] = "유저 리뷰 키워드 내 타이틀 분포"
                        st.rerun()

    elif selected_menu == "유저 리뷰 키워드 내 타이틀 분포":
        st.subheader("리뷰 키워드 내 타이틀 분포")

        all_positive_keywords = []
        all_negative_keywords = []
        for title in filtered_titles:
            all_positive_keywords.extend(title["positive_keywords"])
            all_negative_keywords.extend(title["negative_keywords"])
        unique_keywords = list(set(all_positive_keywords + all_negative_keywords))

        positive_keywords_set = set(all_positive_keywords)
        negative_keywords_set = set(all_negative_keywords)

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
        if "전체" in type_category and not selected_keywords:
            keyword_titles = [
                {
                    "name": title["name"],
                    "app_id": title["app_id"],
                    "link": title["link"],
                    "rating": title["rating"],
                    "tags": title["tags"],
                    "positive_keywords": title["positive_keywords"],
                    "negative_keywords": title["negative_keywords"],
                    "keyword_score": len(title["positive_keywords"]) + len(title["negative_keywords"])
                } for title in filtered_titles
            ]
        else:
            for title in filtered_titles:
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

        if not keyword_titles:
            st.warning(f"선택된 조건 '{', '.join(type_category)}'와 키워드 '{', '.join(selected_keywords)}'에 해당하는 타이틀이 없습니다.")
        else:
            sorted_titles = sorted(keyword_titles, key=lambda x: x["keyword_score"], reverse=True)
            df = pd.DataFrame(sorted_titles)

            st.subheader(f"'{', '.join(type_category)}' 유형 및 '{', '.join(selected_keywords)}' 키워드를 포함한 타이틀 목록")
            selected_title_df = st.dataframe(
                df[["name", "app_id", "link", "rating", "tags", "positive_keywords", "negative_keywords", "keyword_score"]],
                column_config={
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
                selection_mode="single-row",
                on_select="rerun"
            )

            if st.button("상세정보"):
                selected_rows = selected_title_df.selection["rows"]
                if selected_rows:
                    selected_title = df.iloc[selected_rows[0]]
                    st.session_state["selected_title"] = selected_title.to_dict()
                    st.session_state["selected_menu"] = "타이틀 상세"
                    st.rerun()
                else:
                    st.warning("타이틀을 선택해 주세요.")

    elif selected_menu == "타이틀 상세":
        title_info = st.session_state.get("selected_title", filtered_titles[0] if filtered_titles else None)
        if title_info:
            st.subheader("타이틀 상세")
            st.markdown(f"#### {title_info['name']} 상세 (App ID: {title_info['app_id']})")
            st.write(f"- **링크**: [{title_info['link']}]({title_info['link']})")
            st.write(f"- **점수**: {title_info['rating']}")
            st.write(f"- **태그**: {', '.join(title_info['tags'])}")
            st.write(f"- **주요 키워드 (긍정)**: {', '.join(title_info['positive_keywords'])}")
            st.write(f"- **주요 키워드 (부정)**: {', '.join(title_info['negative_keywords'])}")
            st.write("실제 리뷰 텍스트 원문:")
            for review in title_info["reviews"]:
                st.write(f"- {review}")

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
        else:
            st.write("타이틀을 선택해 주세요.")

    elif selected_menu == "용어 정리 (팝업)":
        with st.expander("용어 정리 (클릭하여 열기)", expanded=True):
            st.subheader("용어 정리")
            glossary = {
                "태그": "게임에 붙어있는 태그로, 개발사가 지정한 태그가 아닌 유저가 지정한 태그입니다.",
                "리뷰 키워드": "유저가 남긴 리뷰에서 추출한 키워드로, 특정 게임에 대해 유저들이 장단점으로 인지하는 부분을 나타냅니다.",
                "태그 분포": "특정 태그를 가진 타이틀들이 그 외에 어떤 태그를 가지고 있는지를 보여줍니다.",
                "태그 내 리뷰 키워드 분포": "정해진 태그들을 모두 가지고 있는 타이틀들에 대한 리뷰 키워드의 분포를 나타냅니다.",
                "리뷰 키워드 내 타이틀 분포": "특정 리뷰 키워드를 가진 타이틀들을 모두 보여줍니다.",
                "타이틀 상세": "특정 타이틀에 대한 상세 정보를 보여줍니다."
            }
            selected_term = st.selectbox("용어를 선택하세요", list(glossary.keys()))
            st.markdown(f"**{selected_term}**: {glossary[selected_term]}")