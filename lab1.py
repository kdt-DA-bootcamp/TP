import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 앱 디렉토리의 폰트 경로 설정 (Streamlit Cloud 호환)
font_path = os.path.join(os.getcwd(), "malgun.ttf")  # malgun.ttf 파일이 앱 디렉토리에 있어야 함

if os.path.exists(font_path):
    font_manager.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'Malgun Gothic'  # 한글 폰트 설정
else:
    plt.rcParams['font.family'] = 'DejaVu Sans'  # 기본 폰트로 설정 (Streamlit Cloud 환경에서 사용 가능)

plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 임의의 데이터 생성
data = {
    '게임 명': ['게임 A', '게임 B', '게임 C', '게임 D', '게임 E'],
    '장르 1': ['액션', '롤플레잉', '액션', '시뮬레이션', '롤플레잉'],
    '장르 2': ['어드벤처', '전략', '어드벤처', '전략', '어드벤처'],
    '긍정 리뷰': [120, 80, 150, 90, 110],
    '부정 리뷰': [30, 50, 40, 60, 45]
}
df = pd.DataFrame(data)

# Streamlit 앱 제목
st.title('게임 개발 서비스 프로토타입')

# 사이드바에 메시지 표시
st.sidebar.write("두 카테고리를 모두 선택해주세요.")

# 카테고리 선택
category1 = st.sidebar.selectbox('장르 1 선택', [''] + list(df['장르 1'].unique()))
category2 = st.sidebar.selectbox('장르 2 선택', [''] + list(df['장르 2'].unique()))

# 필터링된 게임 리스트
if category1 and category2:
    filtered_df = df[(df['장르 1'] == category1) & (df['장르 2'] == category2)]
    
    if not filtered_df.empty:
        # FILTER와 # of title을 한 줄에 표시
        st.markdown(
            f"""
            <div style='display: flex; justify-content: space-between;'>
                <span>FILTER: {category1} & {category2}</span>
                <span># of title: {len(filtered_df):,}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 임의의 키워드 빈도 데이터 (사진의 비율을 기반으로 설정)
        positive_keywords = {
            '키워드 4': 34.5,
            '키워드 1': 21.1,
            '키워드 2': 32.7,
            '키워드 3': 10.9
        }
        
        negative_keywords = {
            '키워드 4': 34.5,
            '키워드 1': 21.8,
            '키워드 2': 32.7,
            '키워드 3': 10.9
        }
        
        # 긍정 키워드 데이터 준비
        labels_positive = list(positive_keywords.keys())
        sizes_positive = list(positive_keywords.values())
        
        # 부정 키워드 데이터 준비
        labels_negative = list(negative_keywords.keys())
        sizes_negative = list(negative_keywords.values())
        
        # 색상 설정 (사진과 유사하게)
        colors = ['#1E88E5', '#42A5F5', '#90CAF9', '#BBDEFB', '#FF6347']  # 파란 계열 + 주황
        
        # 파이차트 생성 (Positive Keyword)
        fig1, ax1 = plt.subplots()
        ax1.pie(sizes_positive, labels=labels_positive, autopct='%1.1f%%', colors=colors[:len(labels_positive)], startangle=90, shadow=True)
        ax1.axis('equal')
        
        # 파이차트 생성 (Negative Keyword)
        fig2, ax2 = plt.subplots()
        ax2.pie(sizes_negative, labels=labels_negative, autopct='%1.1f%%', colors=colors[:len(labels_negative)], startangle=90, shadow=True)
        ax2.axis('equal')
        
        # 스트림릿에 제목과 그래프 출력
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<h3 style="font-weight: bold; font-size: 24px;">Positive Keyword</h3>', unsafe_allow_html=True)
            st.pyplot(fig1)
        with col2:
            st.markdown('<h3 style="font-weight: bold; font-size: 24px;">Negative Keyword</h3>', unsafe_allow_html=True)
            st.pyplot(fig2)
    else:
        st.write("조건에 맞는 게임이 없습니다.")
