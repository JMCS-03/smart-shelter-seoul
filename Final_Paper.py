import streamlit as st

# ==========================================
# ★ 중요: Streamlit 페이지 설정은 무조건 최상단에 위치!
# ==========================================
st.set_page_config(page_title="골든타임 커버 응급 쉘터(거점을 클릭하세요)", layout="wide", initial_sidebar_state="collapsed")

import pandas as pd
import numpy as np
# pyrefly: ignore [missing-import]
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import os
import urllib.request
import ssl  
from matplotlib.font_manager import FontProperties

# ==========================================
# 0. 한글 폰트 강제 다운로드 및 주입 (구글 공식 URL로 변경!)
# ==========================================
@st.cache_resource(show_spinner=False)
def get_font_properties():
    font_path = "NanumGothic.ttf"
    
    # 폰트 파일이 없으면 구글 공식 깃허브에서 직접 다운로드 (404 에러 해결)
    if not os.path.exists(font_path):
        font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        
        # Mac 환경 SSL 인증서 에러 우회
        ssl_context = ssl._create_unverified_context()
        with urllib.request.urlopen(font_url, context=ssl_context) as response, open(font_path, 'wb') as out_file:
            out_file.write(response.read())
    
    # 크기별 폰트 객체 생성
    title_font = FontProperties(fname=font_path, size=12)
    label_font = FontProperties(fname=font_path, size=9)
    return title_font, label_font

# 폰트 객체 불러오기 및 마이너스 기호 깨짐 방지
title_font, label_font = get_font_properties()
plt.rcParams['axes.unicode_minus'] = False

# 디자인 테마 개선
st.markdown("""
    <style>
    .info-block { background-color: #ffffff; padding: 22px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); color: #1f2937;}
    .ai-block { background-color: #f8faff; padding: 22px; border-radius: 12px; border-left: 8px solid #4338ca; color: #1f2937; line-height: 1.7;}
    .ai-header { font-weight: 800; color: #3730a3; font-size: 1.25em; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;}
    .highlight { font-weight: 700; color: #dc2626; font-size: 1.1em; }
    .unit { font-size: 0.9em; color: #6b7280; font-weight: normal; }
    </style>
""", unsafe_allow_html=True)

# 1. 최종 데이터 로드
@st.cache_data
def load_data():
    df = pd.read_csv('final_shelter_34.csv')
    if 'id' not in df.columns: df['id'] = range(1, len(df) + 1)
    return df

try:
    df = load_data()
except Exception as e:
    st.error("🚨 'final_shelter_34.csv' 파일을 찾을 수 없습니다.")
    st.stop()

# 세션 상태 관리
if 'selected_loc' not in st.session_state: st.session_state.selected_loc = None
if 'map_center' not in st.session_state: st.session_state.map_center = [37.5500, 126.9800]
if 'map_zoom' not in st.session_state: st.session_state.map_zoom = 11

# 메인 타이틀
st.title("🚨 골든타임 커버 응급 쉘터(거점을 클릭하세요)")

# 레이아웃 구성
if st.session_state.selected_loc is None:
    panel_col, map_col = st.columns([0.01, 9.99])
else:
    panel_col, map_col = st.columns([3.8, 6.2])

# ==========================================
# 🗺️ 지도 섹션
# ==========================================
with map_col:
    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, 
                   tiles='CartoDB positron', attr='CloudFront')
    
    for idx, row in df.iterrows():
        folium.CircleMarker(
            location=[row['위도'], row['경도']], radius=8,
            color='#dc2626', fill=True, fill_color='#dc2626', fill_opacity=0.85,
            tooltip=row['정류장명']
        ).add_to(m)
        
        cov_radius = max(650, row['fin_speed_mean'] * 48)
        folium.Circle(
            location=[row['위도'], row['경도']], radius=cov_radius,
            color='#2563eb', weight=2, dash_array='10, 10',
            fill=True, fill_color='#3b82f6', fill_opacity=0.1
        ).add_to(m)

    map_data = st_folium(m, width="100%", height=800, returned_objects=["last_object_clicked"])
    
    if map_data and map_data.get("last_object_clicked"):
        c_lat, c_lng = map_data["last_object_clicked"]["lat"], map_data["last_object_clicked"]["lng"]
        df['dist'] = np.sqrt((df['위도'] - c_lat)**2 + (df['경도'] - c_lng)**2)
        selected = df.loc[df['dist'].idxmin()]
        
        if selected['dist'] < 0.005:
            if st.session_state.selected_loc is None or st.session_state.selected_loc['id'] != selected['id']:
                st.session_state.selected_loc = selected.to_dict()
                st.session_state.map_center = [selected['위도'], selected['경도']]
                st.session_state.map_zoom = 15
                st.rerun()

# ==========================================
# 📊 상세 정보 및 차트 섹션
# ==========================================
if st.session_state.selected_loc is not None:
    with panel_col:
        sel = st.session_state.selected_loc
        if st.button("⬅️ 전체 지도 보기", use_container_width=True):
            st.session_state.selected_loc = None
            st.session_state.map_center = [37.5500, 126.9800]; st.session_state.map_zoom = 11
            st.rerun()
            
        st.subheader(f"📍 {sel['정류장명']}")
        
        # 차트 영역
        ch1, ch2 = st.columns(2)
        with ch1:
            labels = ['의료기관거리', '혼잡도', '고령자', '1인가구', '경사도']
            stats = [sel['HubDist_scaled'], sel['fin_speed_mean_scaled'], sel['fin_senior_scaled'], sel['fin_single_scaled'], sel['_mean_scaled']]
            angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
            stats += stats[:1]; angles += angles[:1]
            fig1, ax1 = plt.subplots(figsize=(3,3), subplot_kw=dict(polar=True))
            ax1.plot(angles, stats, color='#dc2626', linewidth=2.5)
            ax1.fill(angles, stats, color='#ef4444', alpha=0.3)
            ax1.set_xticks(angles[:-1])
            ax1.set_xticklabels(labels, fontproperties=label_font)
            ax1.set_yticks([])
            plt.title("위험도 밸런스 분석", fontproperties=title_font, pad=15)
            st.pyplot(fig1)
            
        with ch2:
            sizes = [sel['fin_senior'], sel['fin_single'], max(5000, sel['fin_senior'] + sel['fin_single'])]
            fig2, ax2 = plt.subplots(figsize=(3,3))
            ax2.pie(sizes, colors=['#dc2626', '#f59e0b', '#e5e7eb'], startangle=90, wedgeprops=dict(width=0.45), 
                    labels=['고령자', '1인가구', '기타'], textprops={'fontproperties': label_font})
            plt.title("취약 계층 구성 비율", fontproperties=title_font, pad=15)
            st.pyplot(fig2)

        sp = sel['fin_speed_mean']
        traffic_status = "심각 정체" if sp<15 else "정체" if sp<20 else "보통"
        real_dist_km = sel['HubDist'] / 1000 if sel['HubDist'] > 100 else sel['HubDist']

        st.markdown(f"""
        <div class='info-block'>
        <b>📍 거점 명칭</b>: {sel['정류장명']}<br>
        <b>🏥 최인접 응급의료기관</b>: {sel['HubName']}<br>
        <b>📏 거점 간 물리적 거리</b>: <span class='highlight'>{real_dist_km:.2f}km</span> <span class='unit'>(직선거리)</span><br><br>
        <b>👥 수혜 예측 인구</b><br>
        - 고령자 밀집도: {sel['fin_senior']:,}명<br>
        - 1인 가구 밀집도: {sel['fin_single']:,}명<br><br>
        <b>🚗 인프라 환경</b><br>
        - 평균 통행 속도: {sp:.1f}km/h <span class='highlight'>({traffic_status})</span><br>
        - 지형 경사도: {sel['_mean']:.1f}도
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class='ai-block'>
            <div class='ai-header'>🤖 AI 입지 타당성 분석 리포트</div>
            <div class='ai-content'>{sel['ai_report']}</div>
        </div>
        """, unsafe_allow_html=True)