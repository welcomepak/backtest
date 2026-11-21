import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="미국 주식 매수법 백테스터", layout="wide")
st.title("📈 미국 주식 하락시매매 백테스팅 대시보드")

# 1. 첫 화면 입력 칸 (티커, 기간, 하락률 기준)
col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 1.2])
with col1:
    ticker = st.text_input("미국 주식 / ETF 티커", value="TQQQ").strip().upper()
with col2:
    start_date = st.date_input("백테스팅 시작일", value=date(2020, 1, 1))
with col3:
    end_date = st.date_input("백테스팅 종료일", value=date(2026, 11, 7))
with col4:
    drop_pct = st.number_input(
        "매수 기준 (전일 대비 하락률 %)",
        min_value=0.1,
        max_value=50.0,
        value=3.0,
        step=0.5,
        format="%.1f"
    )

if start_date >= end_date:
    st.warning("시작일은 종료일보다 이전 날짜여야 합니다.")
    st.stop()

# 2. 주가 데이터 불러오기
@st.cache_data(ttl=3600, show_spinner="주가 데이터를 불러오는 중입니다...")
def load_stock_data(symbol: str, start: date, end: date) -> pd.DataFrame:
    warmup_start = start - timedelta(days=400)
    raw_df = yf.download(
        symbol,
        start=warmup_start.strftime("%Y-%m-%d"),
        end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False
    )
    if raw_df.empty:
        return pd.DataFrame()
    if isinstance(raw_df.columns, pd.MultiIndex):
        raw_df = raw_df.xs(symbol, level=1, axis=1)
    return raw_df.dropna(subset=['Open', 'High', 'Low', 'Close']).copy()

df = load_stock_data(ticker, start_date, end_date)

if df.empty:
    st.error(f"'{ticker}' 데이터를 불러올 수 없습니다. 티커명 또는 날짜 범위를 확인해 주세요.")
    st.stop()

# 3. 이동평균선 및 매수 시그널 계산
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA120'] = df['Close'].rolling(window=120).mean()
df['MA240'] = df['Close'].rolling(window=240).mean()

df['Prev_Close'] = df['Close'].shift(1)
df['Pct_Change'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
df['Buy_Signal'] = df['Pct_Change'] <= -abs(drop_pct)

df_all = df[(df.index.date >= start_date) & (df.index.date <= end_date)].copy()
if df_all.empty:
    st.warning("선택하신 기간에 해당하는 거래일 데이터가 없습니다.")
    st.stop()

df_all['Date_Str'] = df_all.index.strftime('%Y-%m-%d')

# 누적 평균매수단가(평단선) 계산
df_all['Buy_Price'] = np.where(df_all['Buy_Signal'], df_all['Close'], np.nan)
df_all['Cum_Buy_Count'] = df_all['Buy_Signal'].cumsum()
df_all['Cum_Buy_Sum'] = df_all['Buy_Price'].fillna(0).cumsum()
df_all['Method5_Avg_Price'] = np.where(
    df_all['Cum_Buy_Count'] > 0,
    df_all['Cum_Buy_Sum'] / df_all['Cum_Buy_Count'],
    np.nan
)

# 4. 상단 요약 카드
total_buys = int(df_all['Cum_Buy_Count'].iloc[-1])
last_close = float(df_all['Close'].iloc[-1])
final_avg_price = float(df_all['Method5_Avg_Price'].iloc[-1]) if total_buys > 0 else np.nan

m1, m2, m3, m4 = st.columns(4)
m1.metric("총 매수 횟수 (누적 수량)", f"{total_buys}회 ({total_buys}주)", f"전체 {len(df_all)}거래일 중")
m2.metric("최종 누적 평단가", f"${final_avg_price:.2f}" if total_buys > 0 else "-")
m3.metric(f"{df_all['Date_Str'].iloc[-1]} 종가", f"${last_close:.2f}")
if total_buys > 0:
    profit_pct = ((last_close - final_avg_price) / final_avg_price) * 100
    m4.metric("평단 대비 현재 수익률", f"{profit_pct:+.2f}%", f"${last_close - final_avg_price:+.2f}")
else:
    m4.metric("평단 대비 현재 수익률", "-")

# 5. 드래그 확대/축소 자바스크립트
custom_drag_js = """
(function() {
  var gd = document.getElementById('{plot_id}');
  if (!gd) return;
  var startX = null, preDragRange = null, zoomStack = [], pendingAction = null;

  gd.addEventListener('mousedown', function(e) {
    if (e.button !== 0) return;
    startX = e.clientX;
    var xAuto = gd.layout.xaxis.autorange !== false;
    var yAuto = gd.layout.yaxis.autorange !== false;
    preDragRange = (xAuto && yAuto) ? null : {
      x: gd.layout.xaxis.range ? gd.layout.xaxis.range.slice() : null,
      y: gd.layout.yaxis.range ? gd.layout.yaxis.range.slice() : null
    };
  }, true);

  window.addEventListener('mouseup', function(e) {
    if (startX === null) return;
    var diff = e.clientX - startX;
    startX = null;
    if (Math.abs(diff) <= 10) return;
    if (diff > 10) zoomStack.push(preDragRange);
    else if (diff < -10) pendingAction = 'zoomOut';
  }, true);

  gd.on('plotly_relayout', function() {
    if (pendingAction === 'zoomOut') {
      pendingAction = null;
      var prev = zoomStack.pop();
      if (prev && prev.x && prev.y) {
        Plotly.relayout(gd, {'xaxis.range': prev.x, 'yaxis.range': prev.y});
      } else {
        Plotly.relayout(gd, {'xaxis.autorange': true, 'yaxis.autorange': true});
      }
    }
  });

  gd.on('plotly_doubleclick', function() { zoomStack = []; });
})();
"""

# 6. 봉차트 그리기
price_span = df_all['High'].max() - df_all['Low'].min()
min_body = price_span * 0.003 if price_span > 0 else 0.01
open_plot = np.where(
    np.abs(df_all['Close'] - df_all['Open']) < min_body,
    np.where(df_all['Close'] >= df_all['Open'], df_all['Close'] - min_body, df_all['Close'] + min_body),
    df_all['Open']
)

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df_all['Date_Str'], open=open_plot, high=df_all['High'], low=df_all['Low'], close=df_all['Close'],
    increasing=dict(line=dict(color='#e53935', width=1.4), fillcolor='#e53935'),
    decreasing=dict(line=dict(color='#1e88e5', width=1.4), fillcolor='#1e88e5'),
    whiskerwidth=0.8, name=f'{ticker} 일봉', hoverinfo='skip'
))
fig.add_trace(go.Scatter(x=df_all['Date_Str'], y=df_all['MA20'], mode='lines', name='20일선 (초록)', line=dict(color='#2e7d32', width=1.3), hoverinfo='skip'))
fig.add_trace(go.Scatter(x=df_all['Date_Str'], y=df_all['MA120'], mode='lines', name='120일선 (주황)', line=dict(color='#ff8f00', width=1.4), hoverinfo='skip'))
fig.add_trace(go.Scatter(x=df_all['Date_Str'], y=df_all['MA240'], mode='lines', name='240일선 (보라)', line=dict(color='#8e24aa', width=1.4), hoverinfo='skip'))
fig.add_trace(go.Scatter(x=df_all['Date_Str'], y=df_all['Method5_Avg_Price'], mode='lines', name='하락시매매 평균매수가(평단선)', line=dict(color='#00838f', width=2.0, dash='dash'), hoverinfo='skip'))

buy_days = df_all[df_all['Buy_Signal']].copy()
if not buy_days.empty:
    custom_data = np.stack([buy_days['Date_Str'], buy_days['Close'], buy_days['Pct_Change'], buy_days['Method5_Avg_Price'], buy_days['Cum_Buy_Count']], axis=-1)
    fig.add_trace(go.Scatter(
        x=buy_days['Date_Str'], y=buy_days['Low'] * 0.96, mode='markers',
        marker=dict(symbol='triangle-up', size=10, color='#d93025', line=dict(color='black', width=0.6)),
        name=f'{drop_pct:.1f}% 이상 하락 매수 ({len(buy_days)} / {len(df_all)}일)',
        customdata=custom_data,
        hovertemplate=(
            f"<b>전일대비 {drop_pct:.1f}% 하락 시 매수 (누적 %{{customdata[4]:.0f}}주)</b><br>"
            "매수 날짜: %{customdata[0]}<br>"
            "매수 금액(종가): <b>$%{customdata[1]:.2f}</b><br>"
            "전일 종가 대비 하락률: <b>%{customdata[2]:.2f}%</b><br>"
            "하락시매매 누적 평단가: $%{customdata[3]:.2f}<extra></extra>"
        )
    ))

month_starts = df_all.groupby(df_all.index.to_period('M')).head(1)
if len(df_all) <= 130:
    tick_points = month_starts
elif len(df_all) <= 400:
    tick_points = month_starts[month_starts.index.month.isin([1, 4, 7, 10])]
else:
    tick_points = month_starts[month_starts.index.month.isin([1, 7])]

fig.update_layout(
    title=dict(text=f'<b>{ticker} — 전일대비 {drop_pct:.1f}% 하락 시 매수 ({start_date} ~ {end_date})</b>', font=dict(size=16)),
    xaxis_title='날짜', yaxis_title='주가 (USD)', autosize=True, height=540, template='plotly_white',
    dragmode='zoom', hovermode='closest', hoverdistance=15,
    xaxis=dict(type='category', rangeslider=dict(visible=False), tickmode='array', tickvals=tick_points['Date_Str'], ticktext=tick_points.index.strftime('%Y-%m'), showgrid=True, gridcolor='rgba(0,0,0,0.08)'),
    yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.08)'),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    margin=dict(l=50, r=30, t=75, b=50)
)

html_str = pio.to_html(fig, include_plotlyjs='cdn', full_html=False, config={'responsive': True}, post_script=custom_drag_js)
components.html(html_str, height=560)
st.caption("💡 차트 조작 팁: 마우스를 왼쪽 → 오른쪽으로 드래그하면 확대, 오른쪽 → 왼쪽으로 드래그하면 이전 배율로 축소됩니다.")
