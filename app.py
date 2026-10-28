import streamlit as st
import pandas as pd
import altair as alt
import plotly.graph_objects as go

# 1. 網頁基本設定
st.set_page_config(page_title="歷次校排與成績查詢系統", page_icon="📊", layout="centered")

st.markdown("<h2 style='font-size: 26px;'>📊 歷次校排與成績查詢系統</h2>", unsafe_allow_html=True)
st.write("請輸入座號與密碼（身分證後四碼）來查詢成績。")

# 2. 讀取資料的函數
@st.cache_data
def load_data():
    dfs = pd.read_excel("midterm score_data.xlsx", sheet_name=None, dtype={"座號": str, "密碼": str})
    return dfs

try:
    dfs = load_data()
except FileNotFoundError:
    st.error("找不到資料庫檔案 (midterm score_data.xlsx)，請確認檔名是否正確。")
    st.stop()

required_sheets = ['校排', '國文', '英語', '數學', '自然', '社會']
for sheet in required_sheets:
    if sheet not in dfs:
        st.error(f"Excel 檔案中缺少名為 '{sheet}' 的工作表！請確認檔案格式。")
        st.stop()

# 3. 建立登入區塊
col1, col2 = st.columns(2)
with col1:
    student_id = st.text_input("座號 (例如: 1, 21)", max_chars=2)
with col2:
    password = st.text_input("密碼 (身分證後4碼)", type="password", max_chars=4)

# 4. 查詢邏輯與畫面顯示
if st.button("查詢", type="primary"):
    if student_id and password:
        df_rank = dfs['校排']
        student_data = df_rank[(df_rank["座號"] == student_id) & (df_rank["密碼"] == password)]
        
        if not student_data.empty:
            student_name = student_data.iloc[0]["姓名"]
            st.success(f"{student_name} 同學，登入成功！")
            
            # --- 處理成績資料 ---
            score_cols = df_rank.columns.drop(["座號", "姓名", "密碼"])
            subjects = ['國文', '英語', '數學', '自然', '社會']
            
            subject_records = []
            for subj in subjects:
                subj_data = dfs[subj][(dfs[subj]["座號"] == student_id) & (dfs[subj]["密碼"] == password)]
                if not subj_data.empty:
                    temp_df = subj_data[score_cols].T.reset_index()
                    temp_df.columns = ["考試名稱", "分數"]
                    temp_df["科目"] = subj
                    temp_df = temp_df.dropna()
                    subject_records.append(temp_df)
            
            all_scores_df = pd.concat(subject_records) if subject_records else pd.DataFrame()

            st.divider()

            # 【圖表一：歷次校排趨勢】
            chart_rank = student_data[score_cols].T.reset_index()
            chart_rank.columns = ["考試名稱", "校排"]
            chart_rank = chart_rank.dropna()
            
            if not chart_rank.empty:
                latest_exam = chart_rank.iloc[-1]["考試名稱"]
                latest_rank = int(chart_rank.iloc[-1]["校排"])
                
                # 💡 修改1：將「最新校排」的字體大小從 22px 改為 20px，避免在手機版折行
                st.markdown(f"<h3 style='font-size: 20px;'>🏆 最新校排 ({latest_exam})：第 {latest_rank} 名</h3>", unsafe_allow_html=True)
                st.markdown("<h3 style='font-size: 20px;'>📈 歷次校排趨勢圖</h3>", unsafe_allow_html=True)
                
                line_chart_rank = alt.Chart(chart_rank).mark_line(point=True).encode(
                    x=alt.X('考試名稱', sort=None, title='考試'), 
                    y=alt.Y('校排', scale=alt.Scale(reverse=True), title='校排名次'), 
                    tooltip=['考試名稱', '校排']
                ).properties(height=350)
                st.altair_chart(line_chart_rank, use_container_width=True)
                
                st.divider()

                # 【圖表二：最新一次考試能力分布 (雷達圖)】
                st.markdown(f"<h3 style='font-size: 20px;'>🎯 最新能力分佈 ({latest_exam})</h3>", unsafe_allow_html=True)
                
                latest_scores = all_scores_df[all_scores_df["考試名稱"] == latest_exam]
                
                if len(latest_scores) == 5:
                    radar_fig = go.Figure(data=go.Scatterpolar(
                        r=latest_scores['分數'].tolist() + [latest_scores['分數'].tolist()[0]],
                        theta=latest_scores['科目'].tolist() + [latest_scores['科目'].tolist()[0]],
                        fill='toself',
                        name=latest_exam
                    ))

                    radar_fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                        showlegend=False,
                        margin=dict(l=40, r=40, t=20, b=20)
                    )
                    st.plotly_chart(radar_fig, use_container_width=True)
                else:
                    st.info("最新一次考試缺少部分科目成績，無法繪製雷達圖。")

                st.divider()

                # 【圖表三：歷次各科成績 (純數據表格)】
                if not all_scores_df.empty:
                    st.markdown("<h3 style='font-size: 20px;'>📋 歷次各科成績</h3>", unsafe_allow_html=True)
                    
                    # 將原本長條狀的資料，轉換為直欄是科目、橫列是考試名稱的表格
                    score_table = all_scores_df.pivot_table(index="考試名稱", columns="科目", values="分數", aggfunc="first")
                    # 固定科目的顯示順序
                    score_table = score_table.reindex(columns=subjects)
                    # 固定考試名稱的顯示順序
                    valid_exams = [exam for exam in score_cols if exam in score_table.index]
                    score_table = score_table.reindex(index=valid_exams)
                    
                    score_table = score_table.reset_index()
                    score_table.columns.name = None
                    
                    # 💡 修改2：注入自訂 CSS，並將 DataFrame 轉為 HTML 表格，確保手機版自動壓縮欄寬、文字置中，且不被切到
                    st.markdown("""
                    <style>
                    .custom-score-table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 10px 0;
                        font-size: 15px;
                    }
                    .custom-score-table th, .custom-score-table td {
                        text-align: center !important;
                        padding: 8px 4px;
                        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
                    }
                    .custom-score-table th {
                        font-weight: 600;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # 生成 HTML 並關閉 Pandas 預設的 index 列
                    html_table = score_table.to_html(index=False, classes="custom-score-table", escape=False)
                    st.markdown(html_table, unsafe_allow_html=True)

            else:
                st.info("目前還沒有任何考試成績紀錄喔！")

        else:
            st.error("座號或密碼錯誤，請確認後重新輸入！")
else:
    st.warning("請完整輸入座號與密碼！")