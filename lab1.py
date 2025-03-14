import streamlit as st
import pandas as pd

# 임의의 데이터 생성
data = {
    '게임 명': ['게임 A', '게임 B', '게임 C', '게임 D', '게임 E'],
    '장르 1': ['액션', '롤플레잉', '액션', '시뮬레이션', '롤플레잉'],
    '장르 2': ['어드벤처', '전략', '어드벤처', '전략', '어드벤처'],
    '긍정 리뷰': ["이 게임 레전드", "개꿀잼", "뭔데 이거 간만에 레전드 나왓네", "몰입감 쩔어쩔어", "강추"],
    '부정 리뷰': ["뭔데 이거 돈 아깝다.", "지루함", "별로임", "노잼", "환불해줘"]
}
df = pd.DataFrame(data)

# Streamlit 앱 제목
st.title('게임 개발 서비스 프로토타입')

# 사이드바에 메시지 먼저 표시
st.sidebar.write("두 카테고리를 모두 선택해주세요.")

# 카테고리 선택
category1 = st.sidebar.selectbox('장르 1 선택', [''] + list(df['장르 1'].unique()))
category2 = st.sidebar.selectbox('장르 2 선택', [''] + list(df['장르 2'].unique()))

# 필터링된 게임 리스트
if category1 and category2:  # 두 카테고리가 모두 선택된 경우
    filtered_df = df[(df['장르 1'] == category1) & (df['장르 2'] == category2)]
    if not filtered_df.empty:
        st.write(f"'{category1}' 및 '{category2}'에 해당하는 게임 리스트:")
        st.dataframe(filtered_df)
    else:
        st.write("조건에 맞는 게임이 없슈")