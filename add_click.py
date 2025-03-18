'''
일단! 현재는 제가 AI한테 긍정, 부정 분류 오더 > 임의로 나눈 데이터 형태로 작업했습니다.
파이차트에서 키워드 클릭 상호작용 버튼을 여러번 시도했는데, 잘 되지 않았습니다.
임시로 파이차트 아래 버튼 기능을 추가하여 구성을 했습니다. 

'''
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 데이터 로드
df = pd.read_csv('keyword_sentiment.csv')
df['Keywords'] = df['Keywords'].str.split(', ')
df = df.explode('Keywords')
df['Keywords'] = df['Keywords'].str.strip()

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = 'main'
if 'selected_keyword' not in st.session_state:
    st.session_state.selected_keyword = None

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