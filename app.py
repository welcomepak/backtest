import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="미국주식 하락시 매매 백테스팅", layout="wide")
st.title("📈 미국주식 하락시 매매 백테스팅")

# 1. 첫 화면 입력 컨트롤 (티커, 기간, 하락 기준)
col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 1.2])
with col1:
    ticker = st.text_input("미국 주식 / ETF 티커", value="TQQQ").strip().upper()
with col2:
    start_date = st.date_input("백테스팅 시작일", value=date(2020, 1, 1))
with col3:
    end_date = st.date_input("백테스팅 종료일", value=date.today())
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

# 2. 주가 데이터 다운로드 함수 (1시간 주기 캐싱으로 최신 주가 자동 반영)
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

# 3. 이동평균선(20일, 120일, 240일) 및 매수 시그널 계산
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

# 누적 평균매수단가선(평단선) 계산
df_all['Buy_Price'] = np.where(df_all['Buy_Signal'], df_all['Close'], np.nan)
df_all['Cum_Buy_Count'] = df_all['Buy_Signal'].cumsum()
df_all['Cum_Buy_Sum'] = df_all['Buy_Price'].fillna(0).cumsum()
df_all['Method5_Avg_Price'] = np.where(
    df_all['Cum_Buy_Count'] > 0,
    df_all['Cum_Buy_Sum'] / df_all['Cum_Buy_Count'],
    np.nan
)

# 4. 상단 핵심 요약 지표 카드
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

# 차트 제목을 차트 바깥 영역에 배치 (모바일 글씨 겹침 방지 + 터치 시 페이지 스크롤 허용)
st.subheader(f"{ticker} — 전일대비 {drop_pct:.1f}% 하락 시 매수 ({start_date} ~ {end_date})")

# 5. 전체 축 범위 고정값 계산 (축소 시 차트가 가운데로 작아지는 현상 방지)
full_x0 = -0.5
full_x1 = float(len(df_all)) - 0.5

y_candidates_low = [df_all['Low'].min()]
if not df_all['Buy_Signal'].empty and df_all['Buy_Signal'].any():
    y_candidates_low.append((df_all.loc[df_all['Buy_Signal'], 'Low'] * 0.96).min())
for ma_col in ['MA20', 'MA120', 'MA240', 'Method5_Avg_Price']:
    if df_all[ma_col].notna().any():
        y_candidates_low.append(df_all[ma_col].min())

y_candidates_high = [df_all['High'].max()]
for ma_col in ['MA20', 'MA120', 'MA240', 'Method5_Avg_Price']:
    if df_all[ma_col].notna().any():
        y_candidates_high.append(df_all[ma_col].max())

y_min_val = float(min(y_candidates_low))
y_max_val = float(max(y_candidates_high))
y_pad = (y_max_val - y_min_val) * 0.05 if y_max_val > y_min_val else 1.0
full_y0 = max(0.0, y_min_val - y_pad)
full_y1 = y_max_val + y_pad

# 6. PC(마우스) + 스마트폰(터치 핀치/스와이프 + 경계 고정) 통합 제어 자바스크립트
custom_interaction_js = f"""
(function() {{
  var gd = document.getElementById('{{plot_id}}');
  if (!gd) return;

  var FULL_X0 = {full_x0};
  var FULL_X1 = {full_x1};
  var FULL_X_SPAN = FULL_X1 - FULL_X0;
  var MIN_X_SPAN = Math.min(5.0, FULL_X_SPAN);

  var FULL_Y0 = {full_y0};
  var FULL_Y1 = {full_y1};
  var FULL_Y_SPAN = FULL_Y1 - FULL_Y0;
  var MIN_Y_SPAN = FULL_Y_SPAN * 0.02;

  function clampRanges(x0, x1, y0, y1) {{
    var xSpan = x1 - x0;
    if (xSpan >= FULL_X_SPAN) {{
      x0 = FULL_X0;
      x1 = FULL_X1;
    }} else {{
      if (xSpan < MIN_X_SPAN) {{
        var xMid = (x0 + x1) / 2;
        xSpan = MIN_X_SPAN;
        x0 = xMid - xSpan / 2;
        x1 = xMid + xSpan / 2;
      }}
      if (x0 < FULL_X0) {{ x0 = FULL_X0; x1 = FULL_X0 + xSpan; }}
      if (x1 > FULL_X1) {{ x1 = FULL_X1; x0 = FULL_X1 - xSpan; }}
    }}

    var ySpan = y1 - y0;
    if (ySpan >= FULL_Y_SPAN) {{
      y0 = FULL_Y0;
      y1 = FULL_Y1;
    }} else {{
      if (ySpan < MIN_Y_SPAN) {{
        var yMid = (y0 + y1) / 2;
        ySpan = MIN_Y_SPAN;
        y0 = yMid - ySpan / 2;
        y1 = yMid + ySpan / 2;
      }}
      if (y0 < FULL_Y0) {{ y0 = FULL_Y0; y1 = FULL_Y0 + ySpan; }}
      if (y1 > FULL_Y1) {{ y1 = FULL_Y1; y0 = FULL_Y1 - ySpan; }}
    }}

    return {{ x: [x0, x1], y: [y0, y1] }};
  }}

  // =========================================================================
  // [A] PC(노트북) 마우스 드래그: 좌->우 확대 / 우->좌 이전 배율 축소
  // =========================================================================
  var startX = null;
  var preDragRange = null;
  var zoomStack = [];
  var pendingAction = null;
  var lastTouchEnd = 0;

  gd.addEventListener('mousedown', function(e) {{
    if (Date.now() - lastTouchEnd < 500) return;
    if (e.button !== 0) return;
    startX = e.clientX;
    var curX = gd.layout.xaxis.range ? gd.layout.xaxis.range.slice() : [FULL_X0, FULL_X1];
    var curY = gd.layout.yaxis.range ? gd.layout.yaxis.range.slice() : [FULL_Y0, FULL_Y1];
    var isFull = (Math.abs(curX[0] - FULL_X0) < 0.1 && Math.abs(curX[1] - FULL_X1) < 0.1);
    preDragRange = isFull ? null : {{ x: curX, y: curY }};
  }}, true);

  window.addEventListener('mouseup', function(e) {{
    if (startX === null) return;
    var diff = e.clientX - startX;
    startX = null;
    if (Math.abs(diff) <= 10) return;

    if (diff > 10) {{
      zoomStack.push(preDragRange);
    }} else if (diff < -10) {{
      pendingAction = 'zoomOut';
    }}
  }}, true);

  gd.on('plotly_relayout', function() {{
    if (pendingAction === 'zoomOut') {{
      pendingAction = null;
      var prev = zoomStack.pop();
      if (prev && prev.x && prev.y) {{
        Plotly.relayout(gd, {{
          'xaxis.range': prev.x,
          'yaxis.range': prev.y
        }});
      }} else {{
        Plotly.relayout(gd, {{
          'xaxis.range': [FULL_X0, FULL_X1],
          'yaxis.range': [FULL_Y0, FULL_Y1]
        }});
      }}
    }}
  }});

  gd.on('plotly_doubleclick', function() {{
    zoomStack = [];
    Plotly.relayout(gd, {{
      'xaxis.range': [FULL_X0, FULL_X1],
      'yaxis.range': [FULL_Y0, FULL_Y1]
    }});
  }});

  // =========================================================================
  // [B] 스마트폰 터치 제스처 (안쪽 봉차트 격자 영역 터치 시에만 작동)
  // =========================================================================
  var touchMode = null; // 'pan' | 'pinch'
  var moved = false;
  var lastTapTime = 0;

  var panStartX = 0, panStartY = 0;
  var panInitXRange = null, panInitYRange = null;

  var pinchInitDist = 0;
  var pinchFocalX = 0, pinchFocalY = 0;
  var pinchInitXSpan = 0, pinchInitYSpan = 0;

  var rafPending = false;
  var nextLayoutUpdate = null;

  function scheduleRelayout(updateObj) {{
    nextLayoutUpdate = updateObj;
    if (!rafPending) {{
      rafPending = true;
      requestAnimationFrame(function() {{
        rafPending = false;
        if (nextLayoutUpdate) {{
          Plotly.relayout(gd, nextLayoutUpdate);
          nextLayoutUpdate = null;
        }}
      }});
    }}
  }}

  function getPlotMetrics() {{
    var full = gd._fullLayout;
    if (!full || !full.xaxis || !full.yaxis || !full._size) return null;
    var rect = gd.getBoundingClientRect();
    var left = rect.left + full._size.l;
    var top = rect.top + full._size.t;
    return {{
      xRange: full.xaxis.range.slice(),
      yRange: full.yaxis.range.slice(),
      size: full._size,
      rect: rect,
      plotLeft: left,
      plotRight: left + full._size.w,
      plotTop: top,
      plotBottom: top + full._size.h
    }};
  }}

  function isInsidePlotBox(touch, m) {{
    return (
      touch.clientX >= m.plotLeft &&
      touch.clientX <= m.plotRight &&
      touch.clientY >= m.plotTop &&
      touch.clientY <= m.plotBottom
    );
  }}

  function applyTouchActionPolicy() {{
    var dragLayer = gd.querySelector('.nsewdrag');
    if (dragLayer) {{
      dragLayer.style.touchAction = 'none';
    }}
    gd.style.touchAction = 'pan-y';
  }}
  applyTouchActionPolicy();
  gd.on('plotly_afterplot', applyTouchActionPolicy);

  function initPan(touch) {{
    var m = getPlotMetrics();
    if (!m) return;
    touchMode = 'pan';
    panStartX = touch.clientX;
    panStartY = touch.clientY;
    panInitXRange = m.xRange;
    panInitYRange = m.yRange;
  }}

  function initPinch(t1, t2) {{
    var m = getPlotMetrics();
    if (!m) return;
    touchMode = 'pinch';
    pinchInitDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
    if (pinchInitDist < 10) pinchInitDist = 10;

    var midX = (t1.clientX + t2.clientX) / 2;
    var midY = (t1.clientY + t2.clientY) / 2;
    var relX = (midX - m.plotLeft) / m.size.w;
    var relY = (midY - m.plotTop) / m.size.h;

    pinchInitXSpan = m.xRange[1] - m.xRange[0];
    pinchInitYSpan = m.yRange[1] - m.yRange[0];
    pinchFocalX = m.xRange[0] + relX * pinchInitXSpan;
    pinchFocalY = m.yRange[1] - relY * pinchInitYSpan;
  }}

  gd.addEventListener('touchstart', function(e) {{
    if (!e.touches || e.touches.length === 0) return;
    var m = getPlotMetrics();
    if (!m) return;

    // 범례나 차트 바깥 여백을 터치한 경우 웹페이지 전체 스크롤이 동작하도록 그대로 통과
    if (touchMode === null && !isInsidePlotBox(e.touches[0], m)) {{
      return;
    }}

    e.stopPropagation();

    if (e.touches.length === 1) {{
      moved = false;
      initPan(e.touches[0]);
    }} else if (e.touches.length >= 2) {{
      moved = true;
      e.preventDefault();
      initPinch(e.touches[0], e.touches[1]);
    }}
  }}, {{ passive: false, capture: true }});

  gd.addEventListener('touchmove', function(e) {{
    if (!touchMode || !e.touches || e.touches.length === 0) return;
    var m = getPlotMetrics();
    if (!m) return;

    if (e.touches.length === 1 && touchMode === 'pan') {{
      var t = e.touches[0];
      var dxPx = t.clientX - panStartX;
      var dyPx = t.clientY - panStartY;

      if (!moved && Math.hypot(dxPx, dyPx) < 5) return;
      moved = true;
      e.preventDefault();
      e.stopPropagation();

      var xSpan = panInitXRange[1] - panInitXRange[0];
      var ySpan = panInitYRange[1] - panInitYRange[0];

      var dxData = (dxPx / m.size.w) * xSpan;
      var dyData = (dyPx / m.size.h) * ySpan;

      var clamped = clampRanges(
        panInitXRange[0] - dxData,
        panInitXRange[1] - dxData,
        panInitYRange[0] + dyData,
        panInitYRange[1] + dyData
      );

      scheduleRelayout({{
        'xaxis.range': clamped.x,
        'yaxis.range': clamped.y
      }});
    }} else if (e.touches.length >= 2) {{
      if (touchMode !== 'pinch') {{
        initPinch(e.touches[0], e.touches[1]);
        return;
      }}
      moved = true;
      e.preventDefault();
      e.stopPropagation();

      var t1 = e.touches[0];
      var t2 = e.touches[1];
      var currDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      if (currDist < 10) return;

      var scale = pinchInitDist / currDist;
      var newXSpan = pinchInitXSpan * scale;
      var newYSpan = pinchInitYSpan * scale;

      var midX = (t1.clientX + t2.clientX) / 2;
      var midY = (t1.clientY + t2.clientY) / 2;
      var currRelX = (midX - m.plotLeft) / m.size.w;
      var currRelY = (midY - m.plotTop) / m.size.h;

      var newX0 = pinchFocalX - currRelX * newXSpan;
      var newX1 = newX0 + newXSpan;
      var newY1 = pinchFocalY + currRelY * newYSpan;
      var newY0 = newY1 - newYSpan;

      var clamped = clampRanges(newX0, newX1, newY0, newY1);

      scheduleRelayout({{
        'xaxis.range': clamped.x,
        'yaxis.range': clamped.y
      }});
    }}
  }}, {{ passive: false, capture: true }});

  gd.addEventListener('touchend', function(e) {{
    if (!touchMode) return;
    lastTouchEnd = Date.now();
    e.stopPropagation();

    if (e.touches.length === 1) {{
      initPan(e.touches[0]);
    }} else if (e.touches.length === 0) {{
      if (!moved) {{
        var now = Date.now();
        if (now - lastTapTime < 300) {{
          lastTapTime = 0;
          zoomStack = [];
          Plotly.relayout(gd, {{
            'xaxis.range': [FULL_X0, FULL_X1],
            'yaxis.range': [FULL_Y0, FULL_Y1]
          }});
        }} else {{
          lastTapTime = now;
        }}
      }}
      touchMode = null;
      moved = false;
    }}
  }}, {{ passive: false, capture: true }});
}})();
"""

# 7. Plotly 봉차트 생성
price_span = df_all['High'].max() - df_all['Low'].min()
min_body = price_span * 0.003 if price_span > 0 else 0.01
open_plot = np.where(
    np.abs(df_all['Close'] - df_all['Open']) < min_body,
    np.where(df_all['Close'] >= df_all['Open'], df_all['Close'] - min_body, df_all['Close'] + min_body),
    df_all['Open']
)

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df_all['Date_Str'],
    open=open_plot,
    high=df_all['High'],
    low=df_all['Low'],
    close=df_all['Close'],
    increasing=dict(line=dict(color='#e53935', width=1.4), fillcolor='#e53935'),
    decreasing=dict(line=dict(color='#1e88e5', width=1.4), fillcolor='#1e88e5'),
    whiskerwidth=0.8,
    name=f'{ticker} 일봉',
    hoverinfo='skip'
))

fig.add_trace(go.Scatter(
    x=df_all['Date_Str'], y=df_all['MA20'],
    mode='lines', name='20일선',
    line=dict(color='#2e7d32', width=1.3),
    hoverinfo='skip'
))
fig.add_trace(go.Scatter(
    x=df_all['Date_Str'], y=df_all['MA120'],
    mode='lines', name='120일선',
    line=dict(color='#ff8f00', width=1.4),
    hoverinfo='skip'
))
fig.add_trace(go.Scatter(
    x=df_all['Date_Str'], y=df_all['MA240'],
    mode='lines', name='240일선',
    line=dict(color='#8e24aa', width=1.4),
    hoverinfo='skip'
))

fig.add_trace(go.Scatter(
    x=df_all['Date_Str'], y=df_all['Method5_Avg_Price'],
    mode='lines', name='평단선',
    line=dict(color='#00838f', width=2.0, dash='dash'),
    hoverinfo='skip'
))

buy_days = df_all[df_all['Buy_Signal']].copy()
if not buy_days.empty:
    custom_data = np.stack([
        buy_days['Date_Str'],
        buy_days['Close'],
        buy_days['Pct_Change'],
        buy_days['Method5_Avg_Price'],
        buy_days['Cum_Buy_Count']
    ], axis=-1)

    fig.add_trace(go.Scatter(
        x=buy_days['Date_Str'],
        y=buy_days['Low'] * 0.96,
        mode='markers',
        marker=dict(
            symbol='triangle-up',
            size=9,
            color='#d93025',
            line=dict(color='black', width=0.6)
        ),
        name=f'-{drop_pct:.1f}% 매수 ({len(buy_days)}/{len(df_all)}일)',
        customdata=custom_data,
        hovertemplate=(
            f"<b>전일대비 {drop_pct:.1f}% 하락 시 매수 (누적 %{{customdata[4]:.0f}}주)</b><br>"
            "매수 날짜: %{customdata[0]}<br>"
            "매수 금액(종가): <b>$%{customdata[1]:.2f}</b><br>"
            "전일 종가 대비 하락률: <b>%{customdata[2]:.2f}%</b><br>"
            "누적 평단가: $%{customdata[3]:.2f}"
            "<extra></extra>"
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
    autosize=True,
    height=500,
    template='plotly_white',
    dragmode='zoom',
    hovermode='closest',
    hoverdistance=15,
    xaxis=dict(
        type='category',
        range=[full_x0, full_x1],
        autorange=False,
        rangeslider=dict(visible=False),
        tickmode='array',
        tickvals=tick_points['Date_Str'],
        ticktext=tick_points.index.strftime('%Y-%m'),
        showgrid=True,
        gridcolor='rgba(0,0,0,0.08)'
    ),
    yaxis=dict(
        title='주가 (USD)',
        range=[full_y0, full_y1],
        autorange=False,
        showgrid=True,
        gridcolor='rgba(0,0,0,0.08)'
    ),
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='left',
        x=0,
        font=dict(size=11)
    ),
    margin=dict(l=45, r=12, t=55, b=45)
)

html_str = pio.to_html(
    fig,
    include_plotlyjs='cdn',
    full_html=False,
    config={'responsive': True, 'displayModeBar': False},
    post_script=custom_interaction_js
)
components.html(html_str, height=520)
st.caption("💡 PC: 좌→우 드래그 확대 / 우→좌 드래그 축소 | 스마트폰: 봉차트 안쪽을 두 손가락으로 벌려 확대·오므려 축소 / 한 손가락 좌우 이동 / 두 번 탭 전체 복귀")
