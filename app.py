import inspect
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

# 주요 미국 주식 및 ETF 데이터베이스 (티커, 한글명/별칭, 영문명)
US_STOCKS = [
    # 주요 지수 & 레버리지 ETF
    ("TQQQ", "나스닥100 3배 레버리지", "ProShares UltraPro QQQ"),
    ("SQQQ", "나스닥100 3배 인버스 숏", "ProShares UltraPro Short QQQ"),
    ("QLD", "나스닥100 2배 레버리지", "ProShares Ultra QQQ"),
    ("QQQ", "나스닥100 지수 추종", "Invesco QQQ Trust"),
    ("QQQM", "나스닥100 미니 ETF", "Invesco NASDAQ 100 ETF"),
    ("SOXL", "반도체 3배 레버리지", "Direxion Daily Semiconductor Bull 3X"),
    ("SOXS", "반도체 3배 인버스 숏", "Direxion Daily Semiconductor Bear 3X"),
    ("SOXX", "미국 반도체 지수 ETF", "iShares Semiconductor ETF"),
    ("SMH", "반도체 대형주 ETF", "VanEck Semiconductor ETF"),
    ("SPY", "S&P500 지수 스파이", "SPDR S&P 500 ETF Trust"),
    ("VOO", "S&P500 뱅가드 ETF", "Vanguard S&P 500 ETF"),
    ("IVV", "S&P500 블랙록 ETF", "iShares Core S&P 500 ETF"),
    ("SPLG", "S&P500 저보수 ETF", "SPDR Portfolio S&P 500 ETF"),
    ("SSO", "S&P500 2배 레버리지", "ProShares Ultra S&P500"),
    ("UPRO", "S&P500 3배 레버리지", "ProShares UltraPro S&P500"),
    ("SPXL", "S&P500 3배 레버리지 디렉시온", "Direxion Daily S&P 500 Bull 3X"),
    ("SPXU", "S&P500 3배 인버스 숏", "ProShares UltraPro Short S&P500"),
    ("DIA", "다우존스30 지수 ETF", "SPDR Dow Jones Industrial Average"),
    ("UDOW", "다우존스 3배 레버리지", "ProShares UltraPro Dow30"),
    ("IWM", "러셀2000 중소형주 ETF", "iShares Russell 2000 ETF"),
    ("TNA", "러셀2000 3배 레버리지", "Direxion Daily Small Cap Bull 3X"),
    ("VTI", "미국 전체 주식시장 ETF", "Vanguard Total Stock Market ETF"),
    ("VT", "전세계 주식시장 ETF", "Vanguard Total World Stock ETF"),
    ("FNGU", "빅테크 FANG+ 3배 레버리지", "MicroSectors FANG+ Index 3X"),
    ("BULZ", "빅테크 혁신기업 3배 레버리지", "MicroSectors Solactive FANG & Innovation 3X"),
    ("TECL", "미국 기술주 3배 레버리지", "Direxion Daily Technology Bull 3X"),
    ("XLK", "미국 기술주 섹터 ETF", "Technology Select Sector SPDR"),
    ("LABU", "미국 바이오 3배 레버리지", "Direxion Daily S&P Biotech Bull 3X"),
    ("XBI", "미국 바이오테크 ETF", "SPDR S&P Biotech ETF"),
    ("FAS", "미국 금융주 3배 레버리지", "Direxion Daily Financial Bull 3X"),
    ("XLF", "미국 금융 섹터 ETF", "Financial Select Sector SPDR"),
    ("DPST", "미국 지역은행 3배 레버리지", "Direxion Daily Regional Banks Bull 3X"),
    ("ARKK", "아크 이노베이션 혁신 ETF", "ARK Innovation ETF"),
    ("YINN", "중국 대형주 3배 레버리지", "Direxion Daily FTSE China Bull 3X"),
    ("KWEB", "중국 인터넷 빅테크 ETF", "KraneShares CSI China Internet"),
    ("EWY", "한국 MSCI 지수 ETF", "iShares MSCI South Korea ETF"),
    ("KORU", "한국 MSCI 3배 레버리지", "Direxion Daily South Korea Bull 3X"),
    ("UVXY", "공포지수 VIX 1.5배 레버리지", "ProShares Ultra VIX Short-Term Futures"),
    ("SVIX", "공포지수 VIX 인버스 숏", "Volatility Shares -1x Short VIX"),

    # 배당 & 채권 & 원자재 & 암호화폐 ETF
    ("SCHD", "미국 배당다우존스 슈드", "Schwab US Dividend Equity ETF"),
    ("JEPI", "JP모건 S&P500 커버드콜 배당", "JPMorgan Equity Premium Income ETF"),
    ("JEPQ", "JP모건 나스닥 커버드콜 배당", "JPMorgan Nasdaq Equity Premium Income"),
    ("SPYI", "S&P500 고배당 커버드콜", "NEOS S&P 500 High Income ETF"),
    ("QQQI", "나스닥100 고배당 커버드콜", "NEOS Nasdaq-100 High Income ETF"),
    ("DGRO", "미국 배당성장 ETF", "iShares Core Dividend Growth ETF"),
    ("VIG", "뱅가드 배당성장 ETF", "Vanguard Dividend Appreciation ETF"),
    ("VYM", "뱅가드 고배당 ETF", "Vanguard High Dividend Yield ETF"),
    ("DIVO", "배당성장 커버드콜 ETF", "Amplify CWP Enhanced Dividend Income"),
    ("QYLD", "나스닥100 커버드콜", "Global X NASDAQ 100 Covered Call"),
    ("TSLY", "테슬라 초고배당 커버드콜", "YieldMax TSLA Option Income Strategy"),
    ("NVDY", "엔비디아 초고배당 커버드콜", "YieldMax NVDA Option Income Strategy"),
    ("CONY", "코인베이스 초고배당 커버드콜", "YieldMax COIN Option Income Strategy"),
    ("MSTY", "마이크로스트래티지 초고배당", "YieldMax MSTR Option Income Strategy"),
    ("ULTY", "일드맥스 초고배당 울티", "YieldMax Ultra Option Income Strategy"),
    ("TLT", "미국 20년 이상 장기국채", "iShares 20+ Year Treasury Bond ETF"),
    ("TMF", "미국 장기국채 3배 레버리지", "Direxion Daily 20+ Year Treasury Bull 3X"),
    ("TMV", "미국 장기국채 3배 인버스", "Direxion Daily 20+ Year Treasury Bear 3X"),
    ("SGOV", "미국 초단기 국채 파킹 ETF", "iShares 0-3 Month Treasury Bond ETF"),
    ("BIL", "미국 1-3개월 초단기 국채", "SPDR Bloomberg 1-3 Month T-Bill ETF"),
    ("AGG", "미국 종합채권 ETF", "iShares Core U.S. Aggregate Bond ETF"),
    ("BND", "뱅가드 미국 전체채권 ETF", "Vanguard Total Bond Market ETF"),
    ("GLD", "금 현물 추종 골드 ETF", "SPDR Gold Shares"),
    ("IAU", "금 현물 저보수 ETF", "iShares Gold Trust"),
    ("SLV", "은 현물 추종 실버 ETF", "iShares Silver Trust"),
    ("USO", "미국 원유 WTI ETF", "United States Oil Fund"),
    ("UNG", "미국 천연가스 ETF", "United States Natural Gas Fund"),
    ("BOIL", "천연가스 2배 레버리지", "ProShares Ultra Bloomberg Natural Gas"),
    ("KOLD", "천연가스 2배 인버스 숏", "ProShares UltraShort Bloomberg Natural Gas"),
    ("IBIT", "블랙록 비트코인 현물 ETF", "iShares Bitcoin Trust ETF"),
    ("FBTC", "피델리티 비트코인 현물 ETF", "Fidelity Wise Origin Bitcoin Fund"),
    ("BITO", "비트코인 선물 ETF", "ProShares Bitcoin ETF"),
    ("BITX", "비트코인 2배 레버리지", "2x Bitcoin Strategy ETF"),
    ("ETHA", "블랙록 이더리움 현물 ETF", "iShares Ethereum Trust ETF"),
    ("ETHU", "이더리움 2배 레버리지", "2x Ether ETF"),

    # 단일 종목 레버리지 ETF
    ("NVDL", "엔비디아 2배 레버리지", "GraniteShares 2x Long NVDA Daily ETF"),
    ("NVDX", "엔비디아 2배 레버리지 티렉스", "T-Rex 2X Long NVIDIA Daily Target ETF"),
    ("TSLL", "테슬라 2배 레버리지", "Direxion Daily TSLA Bull 2X Shares"),
    ("TSLT", "테슬라 2배 레버리지 티렉스", "T-Rex 2X Long Tesla Daily Target ETF"),
    ("CONL", "코인베이스 2배 레버리지", "GraniteShares 2x Long COIN Daily ETF"),
    ("MSTX", "마이크로스트래티지 2배 레버리지", "Defiance Daily Target 2X Long MSTR"),
    ("MSTU", "마이크로스트래티지 2배 티렉스", "T-Rex 2X Long MSTR Daily Target ETF"),
    ("AAPU", "애플 2배 레버리지", "Direxion Daily AAPL Bull 2X Shares"),
    ("MSFU", "마이크로소프트 2배 레버리지", "Direxion Daily MSFT Bull 2X Shares"),
    ("AMZU", "아마존 2배 레버리지", "Direxion Daily AMZN Bull 2X Shares"),
    ("GGLL", "구글 알파벳 2배 레버리지", "Direxion Daily GOOGL Bull 2X Shares"),
    ("METU", "메타 2배 레버리지", "Direxion Daily META Bull 2X Shares"),

    # 미국 주요 개별 주식 (빅테크 / 반도체 / AI / 소프트웨어)
    ("NVDA", "엔비디아", "NVIDIA Corporation"),
    ("AAPL", "애플", "Apple Inc."),
    ("MSFT", "마이크로소프트", "Microsoft Corporation"),
    ("AMZN", "아마존", "Amazon.com, Inc."),
    ("GOOGL", "구글 알파벳 A", "Alphabet Inc. Class A"),
    ("GOOG", "구글 알파벳 C", "Alphabet Inc. Class C"),
    ("META", "메타 페이스북", "Meta Platforms, Inc."),
    ("TSLA", "테슬라", "Tesla, Inc."),
    ("AVGO", "브로드컴", "Broadcom Inc."),
    ("AMD", "AMD 에이엠디", "Advanced Micro Devices, Inc."),
    ("INTC", "인텔", "Intel Corporation"),
    ("MU", "마이크론 테크놀로지", "Micron Technology, Inc."),
    ("QCOM", "퀄컴", "Qualcom Incorporated"),
    ("ARM", "ARM 홀딩스 암", "Arm Holdings plc"),
    ("TSM", "TSMC 대만반도체", "Taiwan Semiconductor Manufacturing"),
    ("ASML", "ASML 홀딩", "ASML Holding N.V."),
    ("AMAT", "어플라이드 머티어리얼즈", "Applied Materials, Inc."),
    ("LRCX", "램리서치", "Lam Research Corporation"),
    ("KLAC", "KLA 코퍼레이션", "KLA Corporation"),
    ("TXN", "텍사스 인스트루먼트", "Texas Instruments Incorporated"),
    ("MRVL", "마벨 테크놀로지", "Marvell Technology, Inc."),
    ("ON", "온세미컨덕터", "ON Semiconductor Corporation"),
    ("SMCI", "슈퍼마이크로컴퓨터", "Super Micro Computer, Inc."),
    ("DELL", "델 테크놀로지스", "Dell Technologies Inc."),
    ("ORCL", "오라클", "Oracle Corporation"),
    ("PLTR", "팔란티어 테크놀로지스", "Palantir Technologies Inc."),
    ("CRM", "세일즈포스", "Salesforce, Inc."),
    ("ADBE", "어도비", "Adobe Inc."),
    ("NOW", "서비스나우", "ServiceNow, Inc."),
    ("SNOW", "스노우플레이크", "Snowflake Inc."),
    ("CRWD", "크라우드스트라이크", "CrowdStrike Holdings, Inc."),
    ("PANW", "팔로알토 네트웍스", "Palo Alto Networks, Inc."),
    ("NET", "클라우드플레어", "Cloudflare, Inc."),
    ("DDOG", "데이터독", "Datadog, Inc."),
    ("MDB", "몽고DB", "MongoDB, Inc."),
    ("IBM", "IBM 아이비엠", "International Business Machines"),
    ("CSCO", "시스코 시스템즈", "Cisco Systems, Inc."),
    ("ACN", "액센츄어", "Accenture plc"),
    ("APP", "앱러빈", "AppLovin Corporation"),
    ("SOUN", "사운드하운드 AI", "SoundHound AI, Inc."),
    ("BBAI", "빅베어 AI", "BigBear.ai Holdings, Inc."),

    # 양자컴퓨터 & 우주항공 & 방산 & 원전
    ("IONQ", "아이온큐 양자컴퓨터", "IonQ, Inc."),
    ("RGTI", "리게티 컴퓨팅 양자", "Rigetti Computing, Inc."),
    ("QBTS", "디웨이브 퀀텀 양자", "D-Wave Quantum Inc."),
    ("QUBT", "퀀텀 컴퓨팅 양자", "Quantum Computing Inc."),
    ("RKLB", "로켓랩 우주항공", "Rocket Lab USA, Inc."),
    ("ASTS", "AST 스페이스모바일 위성", "AST SpaceMobile, Inc."),
    ("LUNR", "인튜이티브 머신스 달탐사", "Intuitive Machines, Inc."),
    ("BA", "보잉 항공우주", "The Boeing Company"),
    ("LMT", "록히드마틴 방산", "Lockheed Martin Corporation"),
    ("RTX", "RTX 레이시온 방산", "RTX Corporation"),
    ("NOC", "노스롭그루먼 방산", "Northrop Grumman Corporation"),
    ("GD", "제너럴 다이내믹스 방산", "General Dynamics Corporation"),
    ("GE", "GE 에어로스페이스", "GE Aerospace"),
    ("OKLO", "오클로 소형원전 SMR", "Oklo Inc."),
    ("SMR", "뉴스케일파워 소형원전", "NuScale Power Corporation"),
    ("CEG", "컨스텔레이션 에너지 원전", "Constellation Energy Corporation"),
    ("VST", "비스트라 에너지 전력", "Vistra Corp."),
    ("CCJ", "카메코 우라늄 원전", "Cameco Corporation"),
    ("NEE", "넥스트에라 에너지", "NextEra Energy, Inc."),

    # 금융 & 핀테크 & 암호화폐 관련주
    ("BRK-B", "버크셔 해서웨이 B", "Berkshire Hathaway Inc. Class B"),
    ("JPM", "JP모건 체이스", "JPMorgan Chase & Co."),
    ("BAC", "뱅크오브아메리카", "Bank of America Corporation"),
    ("WFC", "웰스파고", "Wells Fargo & Company"),
    ("GS", "골드만삭스", "The Goldman Sachs Group, Inc."),
    ("MS", "모건스탠리", "Morgan Stanley"),
    ("C", "씨티그룹", "Citigroup Inc."),
    ("BLK", "블랙록", "BlackRock, Inc."),
    ("SCHW", "찰스슈왑", "The Charles Schwab Corporation"),
    ("V", "비자", "Visa Inc."),
    ("MA", "마스터카드", "Mastercard Incorporated"),
    ("AXP", "아메리칸 익스프레스", "American Express Company"),
    ("PYPL", "페이팔", "PayPal Holdings, Inc."),
    ("XYZ", "블록 스퀘어", "Block, Inc."),
    ("SOFI", "소파이 테크놀로지스", "SoFi Technologies, Inc."),
    ("HOOD", "로빈후드", "Robinhood Markets, Inc."),
    ("COIN", "코인베이스", "Coinbase Global, Inc."),
    ("MSTR", "마이크로스트래티지 스트래티지", "Strategy (MicroStrategy)"),
    ("MARA", "마라 홀딩스 비트코인 채굴", "MARA Holdings, Inc."),
    ("RIOT", "라이엇 플랫폼스 비트코인", "Riot Platforms, Inc."),
    ("NU", "누 홀딩스 누뱅크", "Nu Holdings Ltd."),

    # 헬스케어 & 제약 & 바이오
    ("LLY", "일라이 릴리 비만치료제", "Eli Lilly and Company"),
    ("NVO", "노보 노디스크 위고비", "Novo Nordisk A/S"),
    ("UNH", "유나이티드헬스 그룹", "UnitedHealth Group Incorporated"),
    ("JNJ", "존슨앤존슨", "Johnson & Johnson"),
    ("ABBV", "애브비", "AbbVie Inc."),
    ("MRK", "머크", "Merck & Co., Inc."),
    ("PFE", "화이자", "Pfizer Inc."),
    ("AMGN", "암젠", "Amgen Inc."),
    ("GILD", "길리어드 사이언스", "Gilead Sciences, Inc."),
    ("VRTX", "버텍스 파마슈티컬스", "Vertex Pharmaceuticals Incorporated"),
    ("REGN", "리제네론 파마슈티컬스", "Regeneron Pharmaceuticals, Inc."),
    ("ISRG", "인튜이티브 서지컬 로봇수술", "Intuitive Surgical, Inc."),
    ("TMO", "써모 피셔 사이언티픽", "Thermo Fisher Scientific Inc."),
    ("HIMS", "힘스 앤 허스 헬스", "Hims & Hers Health, Inc."),
    ("TEM", "템퍼스 AI 의료", "Tempus AI, Inc."),

    # 소비재 & 유통 & 플랫폼 & 리츠 & 에너지
    ("WMT", "월마트", "Walmart Inc."),
    ("COST", "코스트코", "Costco Wholesale Corporation"),
    ("TGT", "타겟", "Target Corporation"),
    ("HD", "홈디포", "The Home Depot, Inc."),
    ("LOW", "로우스", "Lowe's Companies, Inc."),
    ("KO", "코카콜라", "The Coca-Cola Company"),
    ("PEP", "펩시코", "PepsiCo, Inc."),
    ("MCD", "맥도날드", "McDonald's Corporation"),
    ("SBUX", "스타벅스", "Starbucks Corporation"),
    ("NKE", "나이키", "NIKE, Inc."),
    ("PG", "프록터앤갬블 P&G", "The Procter & Gamble Company"),
    ("PM", "필립모리스", "Philip Morris International Inc."),
    ("MO", "알트리아 그룹", "Altria Group, Inc."),
    ("NFLX", "넷플릭스", "Netflix, Inc."),
    ("DIS", "월트 디즈니", "The Walt Disney Company"),
    ("SPOT", "스포티파이", "Spotify Technology S.A."),
    ("UBER", "우버 테크놀로지스", "Uber Technologies, Inc."),
    ("ABNB", "에어비앤비", "Airbnb, Inc."),
    ("BKNG", "부킹 홀딩스", "Booking Holdings Inc."),
    ("SHOP", "쇼피파이", "Shopify Inc."),
    ("CPNG", "쿠팡", "Coupang, Inc."),
    ("BABA", "알리바바", "Alibaba Group Holding Limited"),
    ("PDD", "핀둬둬 테무", "PDD Holdings Inc."),
    ("JD", "징둥닷컴", "JD.com, Inc."),
    ("RIVN", "리비안 전기차", "Rivian Automotive, Inc."),
    ("LCID", "루시드 전기차", "Lucid Group, Inc."),
    ("F", "포드 자동차", "Ford Motor Company"),
    ("GM", "제너럴 모터스", "General Motors Company"),
    ("CAT", "캐터필러 중장비", "Caterpillar Inc."),
    ("DE", "디어 존디어 농기계", "Deere & Company"),
    ("UPS", "UPS 유피에스 물류", "United Parcel Service, Inc."),
    ("FDX", "페덱스 물류", "FedEx Corporation"),
    ("XOM", "엑슨모빌 석유", "Exxon Mobil Corporation"),
    ("CVX", "셰브론 석유", "Chevron Corporation"),
    ("OXY", "옥시덴탈 페트롤리움", "Occidental Petroleum Corporation"),
    ("O", "리얼티인컴 월배당 리츠", "Realty Income Corporation"),
    ("AMT", "아메리칸 타워 리츠", "American Tower Corporation"),
    ("PLD", "프로로지스 물류리츠", "Prologis, Inc."),
    ("EQIX", "에퀴닉스 데이터센터 리츠", "Equinix, Inc."),
    ("DLR", "디지털 리얼티 데이터센터", "Digital Realty Trust, Inc."),
    ("VICI", "비시 프로퍼티스 리츠", "VICI Properties Inc."),
]

STOCK_OPTIONS = [f"{t} | {kr} ({en})" for t, kr, en in US_STOCKS]

# 실행 확정된 파라미터 상태 초기화
if "confirmed_params" not in st.session_state:
    st.session_state.confirmed_params = {
        "ticker": "TQQQ",
        "stock_label": STOCK_OPTIONS[0],
        "start_date": date(2020, 1, 1),
        "end_date": date.today(),
        "drop_pct": 3.0,
    }

# 1. 첫 화면 입력 컨트롤 (검색 드롭다운 + 하락률 + 기간 + 확인 버튼)
row1_col1, row1_col2 = st.columns([2.4, 1.0])
with row1_col1:
    selectbox_kwargs = {}
    if "accept_new_options" in inspect.signature(st.selectbox).parameters:
        selectbox_kwargs["accept_new_options"] = True

    selected_option = st.selectbox(
        "종목 검색 (티커 · 한글명 · 영문명 입력 후 선택)",
        options=STOCK_OPTIONS,
        index=0,
        placeholder="예: 엔비, 테슬, 나스닥, 배당, NVDA, TQQQ...",
        **selectbox_kwargs
    )

with row1_col2:
    drop_pct = st.number_input(
        "매수 기준 (전일 대비 하락률 %)",
        min_value=0.1,
        max_value=50.0,
        value=3.0,
        step=0.5,
        format="%.1f"
    )

row2_col1, row2_col2, row2_col3 = st.columns([1.3, 1.3, 0.8])
with row2_col1:
    start_date = st.date_input("백테스팅 시작일", value=date(2020, 1, 1))
with row2_col2:
    end_date = st.date_input("백테스팅 종료일", value=date.today())
with row2_col3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    run_clicked = st.button("확인", type="primary", use_container_width=True)

# 선택된 옵션에서 티커 추출
raw_selected = (selected_option or "TQQQ").strip()
input_ticker = raw_selected.split("|")[0].strip().upper()

# [확인] 버튼을 눌렀을 때만 실행 파라미터 갱신
if run_clicked:
    if not input_ticker:
        st.warning("종목 또는 티커를 선택해 주세요.")
    elif start_date >= end_date:
        st.warning("시작일은 종료일보다 이전 날짜여야 합니다.")
    else:
        st.session_state.confirmed_params = {
            "ticker": input_ticker,
            "stock_label": raw_selected,
            "start_date": start_date,
            "end_date": end_date,
            "drop_pct": float(drop_pct),
        }

cp = st.session_state.confirmed_params
is_changed = (
    input_ticker != cp["ticker"]
    or start_date != cp["start_date"]
    or end_date != cp["end_date"]
    or round(float(drop_pct), 2) != round(cp["drop_pct"], 2)
)
if is_changed:
    st.info("입력 조건이 변경되었습니다. **[확인]** 버튼을 누르면 새 조건으로 백테스팅이 실행됩니다.")

ticker = cp["ticker"]
active_start = cp["start_date"]
active_end = cp["end_date"]
active_drop = cp["drop_pct"]

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

df = load_stock_data(ticker, active_start, active_end)

if df.empty:
    st.error(f"'{ticker}' 데이터를 불러올 수 없습니다. 정확한 미국 주식/ETF 티커인지 확인해 주세요.")
    st.stop()

# 3. 이동평균선(20일, 120일, 240일) 및 매수 시그널 계산
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA120'] = df['Close'].rolling(window=120).mean()
df['MA240'] = df['Close'].rolling(window=240).mean()

df['Prev_Close'] = df['Close'].shift(1)
df['Pct_Change'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100
df['Buy_Signal'] = df['Pct_Change'] <= -abs(active_drop)

df_all = df[(df.index.date >= active_start) & (df.index.date <= active_end)].copy()
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
st.subheader(f"{ticker} — 전일대비 {active_drop:.1f}% 하락 시 매수 ({active_start} ~ {active_end})")

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
