import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os

# 폰트 로직: 프로젝트 디렉토리의 폰트 파일 참조
font_path = os.path.join(os.path.dirname(__file__), "malgun.ttf")
font_manager.fontManager.addfont(font_path)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 임의의 데이터 생성
data = {
    '게임 명': ['게임 A', '게임 B', '게임 C', '게임 D', '게임 E'],
    '장르 1': ['Indie', 'MOBA', 'Indie', 'MOBA', 'Indie'],
    '장르 2': ['MOBA', 'Indie', 'MOBA', 'Indie', 'MOBA'],
    '긍정 리뷰': [120, 80, 150, 90, 110],
    '부정 리뷰': [30, 50, 40, 60, 45]
}
df = pd.DataFrame(data)

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = 'main'

# Streamlit 앱 제목
st.title('게임 개발 서비스 프로토타입')

# 사이드바에 메시지 표시
st.sidebar.write("두 카테고리를 모두 선택해주세요.")

# 카테고리 선택
category1 = st.sidebar.selectbox('장르 1 선택', [''] + ['Indie', 'MOBA'])
category2 = st.sidebar.selectbox('장르 2 선택', [''] + ['Indie', 'MOBA'])

# 메인 페이지
if st.session_state.page == 'main':
    if category1 and category2:
        filtered_df = df[(df['장르 1'] == category1) & (df['장르 2'] == category2)]
        
        if not filtered_df.empty:
            st.markdown(
                f"""
                <div style='display: flex; justify-content: space-between;'>
                    <span>FILTER: {category1} & {category2}</span>
                    <span># of title: {len(filtered_df):,}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # 전체 데이터 기반 키워드
            positive_keywords = {'게임사 4': 34.5, '게임사 1': 21.1, '게임사 2': 32.7, '게임사 3': 10.9}
            negative_keywords = {'게임사 4': 34.5, '게임사 1': 21.8, '게임사 2': 32.7, '게임사 3': 10.9}
            
            labels_positive = list(positive_keywords.keys())
            sizes_positive = list(positive_keywords.values())
            labels_negative = list(negative_keywords.keys())
            sizes_negative = list(negative_keywords.values())
            
            colors = ['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB', '#FF6347']
            
            fig1, ax1 = plt.subplots()
            ax1.pie(sizes_positive, labels=labels_positive, autopct='%1.1f%%', colors=colors[:len(labels_positive)], startangle=90, shadow=False)
            ax1.axis('equal')
            
            fig2, ax2 = plt.subplots()
            ax2.pie(sizes_negative, labels=labels_negative, autopct='%1.1f%%', colors=colors[:len(labels_negative)], startangle=90, shadow=False)
            ax2.axis('equal')
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<h3 style="font-weight: bold; font-size: 24px;">Positive Keyword</h3>', unsafe_allow_html=True)
                st.pyplot(fig1)
            with col2:
                st.markdown('<h3 style="font-weight: bold; font-size: 24px;">Negative Keyword</h3>', unsafe_allow_html=True)
                st.pyplot(fig2)
            
            if st.button("공통 키워드 보기", key="to_keywords"):
                st.session_state.page = 'keywords'
                st.rerun()
        else:
            st.write("조건에 맞는 게임이 없습니다.")
    else:
        st.write("카테고리를 모두 선택해주세요.")

# 공통 키워드 페이지
elif st.session_state.page == 'keywords':
    filtered_df = df[(df['장르 1'] == category1) & (df['장르 2'] == category2)]
    
    if not filtered_df.empty:
        # 첫 번째 페이지와 동일한 FILTER와 # of title 표시
        st.markdown(
            f"""
            <div style='display: flex; justify-content: space-between;'>
                <span>FILTER: {category1} & {category2}</span>
                <span># of title: {len(filtered_df):,}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 공통 키워드 데이터
        common_positive_keywords = {'게임성': 50, '그래픽': 30, '스토리': 20}
        common_negative_keywords = {'버그': 40, '최적화': 35, '서버': 25}
        
        labels_positive_common = list(common_positive_keywords.keys())
        sizes_positive_common = list(common_positive_keywords.values())
        labels_negative_common = list(common_negative_keywords.keys())
        sizes_negative_common = list(common_negative_keywords.values())
        
        colors = ['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB', '#FF6347']
        
        fig3, ax3 = plt.subplots()
        ax3.pie(sizes_positive_common, labels=labels_positive_common, autopct='%1.1f%%', colors=colors[:len(labels_positive_common)], startangle=90, shadow=False)
        ax3.axis('equal')
        
        fig4, ax4 = plt.subplots()
        ax4.pie(sizes_negative_common, labels=labels_negative_common, autopct='%1.1f%%', colors=colors[:len(labels_negative_common)], startangle=90, shadow=False)
        ax4.axis('equal')
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<h3 style="font-weight: bold; font-size: 24px;">Positive Keyword in common</h3>', unsafe_allow_html=True)
            st.pyplot(fig3)
        with col2:
            st.markdown('<h3 style="font-weight: bold; font-size: 24px;">Negative Keyword in common</h3>', unsafe_allow_html=True)
            st.pyplot(fig4)
        
        if st.button("뒤로 가기", key="back_to_main"):
            st.session_state.page = 'main'
            st.rerun()
    else:
        st.write("조건에 맞는 게임이 없습니다.")
