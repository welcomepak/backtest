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

# 모바일 화면 여백 최소화 및 일봉/주봉 전환 버튼 스타일
st.markdown(
    """
    <style>
    .block-container {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
        padding-top: 1.4rem !important;
    }
    iframe {
        width: 100% !important;
        display: block;
    }
    /* 일봉 / 주봉 가로 알약 버튼 스타일 */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: inline-flex !important;
        flex-direction: row !important;
        gap: 6px !important;
        background-color: #f1f3f5;
        padding: 4px;
        border-radius: 8px;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        margin: 0 !important;
        padding: 4px 14px !important;
        border-radius: 6px !important;
        cursor: pointer;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        background-color: transparent;
        transition: all 0.15s ease;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        background-color: #ffffff !important;
        color: #d93025 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.14);
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    @media (min-width: 768px) {
        .block-container {
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
            padding-top: 2rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 미국주식 하락시 매매 백테스팅")

# 오늘 날짜 및 1년 전 날짜 계산 (윤년 2월 29일 예외 처리 포함)
today = date.today()
try:
    default_start_date = today.replace(year=today.year - 1)
except ValueError:
    default_start_date = today.replace(year=today.year - 1, day=28)

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
    ("QCOM", "퀄컴", "Qualcomm Incorporated"),
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

# 실행 확정된 파라미터 및 차트 기본 단위 상태 초기화
if "confirmed_params" not in st.session_state:
    st.session_state.confirmed_params = {
        "ticker": "TQQQ",
        "stock_label": STOCK_OPTIONS[0],
        "buy_basis": "전일대비",
        "drop_pct": 3.0,
        "start_date": default_start_date,
        "end_date": today,
    }

if "chart_timeframe" not in st.session_state:
    st.session_state.chart_timeframe = "일봉"

# 1. 첫 화면 입력 컨트롤
# Row 1: 종목 검색
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

# Row 2: 매수기준 (전일대비 / 전주대비) + 하락율(%)
row2_col1, row2_col2 = st.columns([1.0, 1.0])
with row2_col1:
    buy_basis = st.selectbox(
        "매수기준",
        options=["전일대비", "전주대비"],
        index=0
    )
with row2_col2:
    drop_pct = st.number_input(
        "하락율(%)",
        min_value=0.1,
        max_value=50.0,
        value=3.0,
        step=0.5,
        format="%.1f"
    )

# Row 3: 시작일 + 종료일 + 확인 버튼
row3_col1, row3_col2, row3_col3 = st.columns([1.3, 1.3, 0.8])
with row3_col1:
    start_date = st.date_input("백테스팅 시작일", value=default_start_date)
with row3_col2:
    end_date = st.date_input("백테스팅 종료일", value=today)
with row3_col3:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    run_clicked = st.button("확인", type="primary", use_container_width=True)

# 선택된 옵션에서 티커 추출
raw_selected = (selected_option or "TQQQ").strip()
input_ticker = raw_selected.split("|")[0].strip().upper()

# [확인] 버튼을 눌렀을 때만 실행 파라미터 및 차트 기본 단위(전일대비->일봉, 전주대비->주봉) 갱신
if run_clicked:
    if not input_ticker:
        st.warning("종목 또는 티커를 선택해 주세요.")
    elif start_date >= end_date:
        st.warning("시작일은 종료일보다 이전 날짜여야 합니다.")
    else:
        st.session_state.confirmed_params = {
            "ticker": input_ticker,
            "stock_label": raw_selected,
            "buy_basis": buy_basis,
            "drop_pct": float(drop_pct),
            "start_date": start_date,
            "end_date": end_date,
        }
        st.session_state.chart_timeframe = "주봉" if buy_basis == "전주대비" else "일봉"

cp = st.session_state.confirmed_params
is_changed = (
    input_ticker != cp["ticker"]
    or buy_basis != cp["buy_basis"]
    or round(float(drop_pct), 2) != round(cp["drop_pct"], 2)
    or start_date != cp["start_date"]
    or end_date != cp["end_date"]
)
if is_changed:
    st.info("입력 조건이 변경되었습니다. **[확인]** 버튼을 누르면 새 조건으로 백테스팅이 실행됩니다.")

ticker = cp["ticker"]
active_basis = cp["buy_basis"]
active_drop = cp["drop_pct"]
active_start = cp["start_date"]
active_end = cp["end_date"]

# 2. 주가 데이터 다운로드 함수 (240주선 연속성까지 확보하기 위해 약 5년 전부터 수집)
@st.cache_data(ttl=3600, show_spinner="주가 데이터를 불러오는 중입니다...")
def load_stock_data(symbol: str, start: date, end: date) -> pd.DataFrame:
    warmup_start = start - timedelta(days=1850)
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

# 종료일까지의 데이터만 사용
df = df[df.index.date <= active_end].copy()
if df.empty:
    st.warning("선택하신 기간에 해당하는 거래일 데이터가 없습니다.")
    st.stop()

# 3. 일봉 및 주봉 데이터 프레임 구축 (주봉은 해당 주 마지막 영업일 종가 기준)
df['Week_Period'] = df.index.to_period('W')
df['Date_Str'] = df.index.strftime('%Y-%m-%d')

# 일봉 이동평균선 (20일, 120일, 240일)
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA120'] = df['Close'].rolling(window=120).mean()
df['MA240'] = df['Close'].rolling(window=240).mean()
df['Prev_Close'] = df['Close'].shift(1)
df['Daily_Pct_Change'] = ((df['Close'] - df['Prev_Close']) / df['Prev_Close']) * 100

# 주봉 집계 (월~일 기준 각 주의 첫 시가, 최고가, 최저가, 마지막 영업일 종가 및 날짜)
df_with_date = df.copy()
df_with_date['Trade_Date'] = df_with_date.index
weekly_full = df_with_date.groupby('Week_Period').agg(
    Open=('Open', 'first'),
    High=('High', 'max'),
    Low=('Low', 'min'),
    Close=('Close', 'last'),
    Last_Date=('Trade_Date', 'last'),
)
weekly_full['Date_Str'] = weekly_full['Last_Date'].dt.strftime('%Y-%m-%d')
weekly_full['MA20'] = weekly_full['Close'].rolling(window=20).mean()
weekly_full['MA120'] = weekly_full['Close'].rolling(window=120).mean()
weekly_full['MA240'] = weekly_full['Close'].rolling(window=240).mean()
weekly_full['Prev_Week_Close'] = weekly_full['Close'].shift(1)
weekly_full['Weekly_Pct_Change'] = ((weekly_full['Close'] - weekly_full['Prev_Week_Close']) / weekly_full['Prev_Week_Close']) * 100

# 4. 매수기준(전일대비 vs 전주대비)에 따른 매수 시그널 및 누적 평단가 계산
df_period = df[(df.index.date >= active_start) & (df.index.date <= active_end)].copy()
weekly_period = weekly_full[
    (weekly_full['Last_Date'].dt.date >= active_start) & (weekly_full['Last_Date'].dt.date <= active_end)
].copy()

if df_period.empty or weekly_period.empty:
    st.warning("선택하신 기간에 해당하는 거래일 데이터가 없습니다.")
    st.stop()

if active_basis == "전일대비":
    # 일별 매수 판정
    df_period['Buy_Signal'] = df_period['Daily_Pct_Change'] <= -abs(active_drop)
    df_period['Buy_Price'] = np.where(df_period['Buy_Signal'], df_period['Close'], np.nan)
    df_period['Cum_Buy_Count'] = df_period['Buy_Signal'].cumsum()
    df_period['Cum_Buy_Sum'] = df_period['Buy_Price'].fillna(0).cumsum()
    df_period['Avg_Price'] = np.where(
        df_period['Cum_Buy_Count'] > 0,
        df_period['Cum_Buy_Sum'] / df_period['Cum_Buy_Count'],
        np.nan
    )

    # 주봉 표시용 집계: 한 주에 여러 번 매수했을 경우 주당 평균 매수가 및 주간 매수 수량 계산
    week_buy_stats = df_period.groupby('Week_Period').agg(
        Week_Buy_Count=('Buy_Signal', 'sum'),
        Week_Buy_Sum=('Buy_Price', 'sum'),
    )
    weekly_period = weekly_period.join(week_buy_stats)
    weekly_period['Week_Buy_Count'] = weekly_period['Week_Buy_Count'].fillna(0).astype(int)
    weekly_period['Week_Buy_Sum'] = weekly_period['Week_Buy_Sum'].fillna(0.0)
    weekly_period['Buy_Signal'] = weekly_period['Week_Buy_Count'] > 0
    weekly_period['Week_Avg_Buy_Price'] = np.where(
        weekly_period['Buy_Signal'],
        weekly_period['Week_Buy_Sum'] / weekly_period['Week_Buy_Count'],
        np.nan
    )
    weekly_period['Cum_Buy_Count'] = weekly_period['Week_Buy_Count'].cumsum()
    weekly_period['Cum_Buy_Sum'] = weekly_period['Week_Buy_Sum'].cumsum()
    weekly_period['Avg_Price'] = np.where(
        weekly_period['Cum_Buy_Count'] > 0,
        weekly_period['Cum_Buy_Sum'] / weekly_period['Cum_Buy_Count'],
        np.nan
    )

    total_buys = int(df_period['Cum_Buy_Count'].iloc[-1])
    final_avg_price = float(df_period['Avg_Price'].iloc[-1]) if total_buys > 0 else np.nan
    total_units_label = f"전체 {len(df_period)}거래일 중"
else:
    # 전주대비 매수 판정 (주 마지막 영업일 종가 비교)
    weekly_period['Buy_Signal'] = weekly_period['Weekly_Pct_Change'] <= -abs(active_drop)
    weekly_period['Week_Buy_Count'] = weekly_period['Buy_Signal'].astype(int)
    weekly_period['Week_Avg_Buy_Price'] = np.where(weekly_period['Buy_Signal'], weekly_period['Close'], np.nan)
    weekly_period['Cum_Buy_Count'] = weekly_period['Buy_Signal'].cumsum()
    weekly_period['Cum_Buy_Sum'] = weekly_period['Week_Avg_Buy_Price'].fillna(0).cumsum()
    weekly_period['Avg_Price'] = np.where(
        weekly_period['Cum_Buy_Count'] > 0,
        weekly_period['Cum_Buy_Sum'] / weekly_period['Cum_Buy_Count'],
        np.nan
    )

    # 일봉 차트 전환 시에도 해당 주의 마지막 영업일에 매수 표시가 되도록 매핑
    buy_dates_map = dict(
        zip(
            weekly_period.loc[weekly_period['Buy_Signal'], 'Last_Date'],
            weekly_period.loc[weekly_period['Buy_Signal'], 'Close']
        )
    )
    pct_dates_map = dict(zip(weekly_period['Last_Date'], weekly_period['Weekly_Pct_Change']))

    df_period['Buy_Signal'] = df_period.index.isin(buy_dates_map.keys())
    df_period['Buy_Price'] = df_period.index.map(buy_dates_map).astype(float)
    df_period['Weekly_Pct_On_Day'] = df_period.index.map(pct_dates_map).astype(float)
    df_period['Cum_Buy_Count'] = df_period['Buy_Signal'].cumsum()
    df_period['Cum_Buy_Sum'] = df_period['Buy_Price'].fillna(0).cumsum()
    df_period['Avg_Price'] = np.where(
        df_period['Cum_Buy_Count'] > 0,
        df_period['Cum_Buy_Sum'] / df_period['Cum_Buy_Count'],
        np.nan
    )

    total_buys = int(weekly_period['Cum_Buy_Count'].iloc[-1])
    final_avg_price = float(weekly_period['Avg_Price'].iloc[-1]) if total_buys > 0 else np.nan
    total_units_label = f"전체 {len(weekly_period)}주 중"

# 5. 상단 핵심 요약 지표 카드
last_close = float(df_period['Close'].iloc[-1])
m1, m2, m3, m4 = st.columns(4)
m1.metric("총 매수 횟수 (누적 수량)", f"{total_buys}회 ({total_buys}주)", total_units_label)
m2.metric("최종 누적 평단가", f"${final_avg_price:.2f}" if total_buys > 0 else "-")
m3.metric(f"{df_period['Date_Str'].iloc[-1]} 종가", f"${last_close:.2f}")
if total_buys > 0:
    profit_pct = ((last_close - final_avg_price) / final_avg_price) * 100
    m4.metric("평단 대비 현재 수익률", f"{profit_pct:+.2f}%", f"${last_close - final_avg_price:+.2f}")
else:
    m4.metric("평단 대비 현재 수익률", "-")

# 6. 차트 제목 및 차트 위쪽 [일봉 / 주봉] 선택 버튼
st.markdown(
    f"<h4 style='margin: 0.4rem 0 0.25rem 0; font-size: clamp(1.0rem, 4.0vw, 1.35rem);'>"
    f"{ticker} — {active_basis} {active_drop:.1f}% 하락 시 매수 ({active_start} ~ {active_end})"
    f"</h4>",
    unsafe_allow_html=True,
)

selected_tf = st.radio(
    "차트 봉 단위",
    options=["일봉", "주봉"],
    key="chart_timeframe",
    horizontal=True,
    label_visibility="collapsed"
)

is_weekly_chart = (selected_tf == "주봉")
plot_df = weekly_period.copy() if is_weekly_chart else df_period.copy()

# 7. 전체 축 범위 고정값 계산 (안쪽 Y축 눈금과 첫 봉이 겹치지 않도록 좌측 미세 여백 포함)
left_pad_candles = max(1.2, float(len(plot_df)) * 0.035)
full_x0 = -left_pad_candles
full_x1 = float(len(plot_df)) - 0.5

y_candidates_low = [plot_df['Low'].min()]
y_candidates_high = [plot_df['High'].max()]

for ma_col in ['MA20', 'MA120', 'MA240', 'Avg_Price']:
    if plot_df[ma_col].notna().any():
        y_candidates_low.append(plot_df[ma_col].min())
        y_candidates_high.append(plot_df[ma_col].max())

buy_price_col = 'Week_Avg_Buy_Price' if is_weekly_chart else 'Buy_Price'
if plot_df[buy_price_col].notna().any():
    y_candidates_low.append(plot_df[buy_price_col].min())
    y_candidates_high.append(plot_df[buy_price_col].max())

y_min_val = float(min(y_candidates_low))
y_max_val = float(max(y_candidates_high))
y_pad = (y_max_val - y_min_val) * 0.06 if y_max_val > y_min_val else 1.0
full_y0 = max(0.0, y_min_val - y_pad)
full_y1 = y_max_val + y_pad

# 8. PC(마우스) + 스마트폰(터치 핀치/스와이프 + 경계 고정) 통합 제어 자바스크립트
custom_interaction_js = """
(function() {
  var gd = document.getElementById('{plot_id}');
  if (!gd) return;

  var FULL_X0 = __FULL_X0__;
  var FULL_X1 = __FULL_X1__;
  var FULL_X_SPAN = FULL_X1 - FULL_X0;
  var MIN_X_SPAN = Math.min(5.0, FULL_X_SPAN);

  var FULL_Y0 = __FULL_Y0__;
  var FULL_Y1 = __FULL_Y1__;
  var FULL_Y_SPAN = FULL_Y1 - FULL_Y0;
  var MIN_Y_SPAN = FULL_Y_SPAN * 0.02;

  function clampRanges(x0, x1, y0, y1) {
    var xSpan = x1 - x0;
    if (xSpan >= FULL_X_SPAN) {
      x0 = FULL_X0;
      x1 = FULL_X1;
    } else {
      if (xSpan < MIN_X_SPAN) {
        var xMid = (x0 + x1) / 2;
        xSpan = MIN_X_SPAN;
        x0 = xMid - xSpan / 2;
        x1 = xMid + xSpan / 2;
      }
      if (x0 < FULL_X0) { x0 = FULL_X0; x1 = FULL_X0 + xSpan; }
      if (x1 > FULL_X1) { x1 = FULL_X1; x0 = FULL_X1 - xSpan; }
    }

    var ySpan = y1 - y0;
    if (ySpan >= FULL_Y_SPAN) {
      y0 = FULL_Y0;
      y1 = FULL_Y1;
    } else {
      if (ySpan < MIN_Y_SPAN) {
        var yMid = (y0 + y1) / 2;
        ySpan = MIN_Y_SPAN;
        y0 = yMid - ySpan / 2;
        y1 = yMid + ySpan / 2;
      }
      if (y0 < FULL_Y0) { y0 = FULL_Y0; y1 = FULL_Y0 + ySpan; }
      if (y1 > FULL_Y1) { y1 = FULL_Y1; y0 = FULL_Y1 - ySpan; }
    }

    return { x: [x0, x1], y: [y0, y1] };
  }

  // [A] PC(노트북) 마우스 드래그: 좌->우 확대 / 우->좌 이전 배율 축소
  var startX = null;
  var preDragRange = null;
  var zoomStack = [];
  var pendingAction = null;
  var lastTouchEnd = 0;

  gd.addEventListener('mousedown', function(e) {
    if (Date.now() - lastTouchEnd < 500) return;
    if (e.button !== 0) return;
    startX = e.clientX;
    var curX = gd.layout.xaxis.range ? gd.layout.xaxis.range.slice() : [FULL_X0, FULL_X1];
    var curY = gd.layout.yaxis.range ? gd.layout.yaxis.range.slice() : [FULL_Y0, FULL_Y1];
    var isFull = (Math.abs(curX[0] - FULL_X0) < 0.1 && Math.abs(curX[1] - FULL_X1) < 0.1);
    preDragRange = isFull ? null : { x: curX, y: curY };
  }, true);

  window.addEventListener('mouseup', function(e) {
    if (startX === null) return;
    var diff = e.clientX - startX;
    startX = null;
    if (Math.abs(diff) <= 10) return;

    if (diff > 10) {
      zoomStack.push(preDragRange);
    } else if (diff < -10) {
      pendingAction = 'zoomOut';
    }
  }, true);

  gd.on('plotly_relayout', function() {
    if (pendingAction === 'zoomOut') {
      pendingAction = null;
      var prev = zoomStack.pop();
      if (prev && prev.x && prev.y) {
        Plotly.relayout(gd, {
          'xaxis.range': prev.x,
          'yaxis.range': prev.y
        });
      } else {
        Plotly.relayout(gd, {
          'xaxis.range': [FULL_X0, FULL_X1],
          'yaxis.range': [FULL_Y0, FULL_Y1]
        });
      }
    }
  });

  gd.on('plotly_doubleclick', function() {
    zoomStack = [];
    Plotly.relayout(gd, {
      'xaxis.range': [FULL_X0, FULL_X1],
      'yaxis.range': [FULL_Y0, FULL_Y1]
    });
  });

  // [B] 스마트폰 터치 제스처 (안쪽 봉차트 격자 영역 터치 시에만 작동)
  var touchMode = null;
  var moved = false;
  var lastTapTime = 0;

  var panStartX = 0, panStartY = 0;
  var panInitXRange = null, panInitYRange = null;

  var pinchInitDist = 0;
  var pinchFocalX = 0, pinchFocalY = 0;
  var pinchInitXSpan = 0, pinchInitYSpan = 0;

  var rafPending = false;
  var nextLayoutUpdate = null;

  function scheduleRelayout(updateObj) {
    nextLayoutUpdate = updateObj;
    if (!rafPending) {
      rafPending = true;
      requestAnimationFrame(function() {
        rafPending = false;
        if (nextLayoutUpdate) {
          Plotly.relayout(gd, nextLayoutUpdate);
          nextLayoutUpdate = null;
        }
      });
    }
  }

  function getPlotMetrics() {
    var full = gd._fullLayout;
    if (!full || !full.xaxis || !full.yaxis || !full._size) return null;
    var rect = gd.getBoundingClientRect();
    var left = rect.left + full._size.l;
    var top = rect.top + full._size.t;
    return {
      xRange: full.xaxis.range.slice(),
      yRange: full.yaxis.range.slice(),
      size: full._size,
      rect: rect,
      plotLeft: left,
      plotRight: left + full._size.w,
      plotTop: top,
      plotBottom: top + full._size.h
    };
  }

  function isInsidePlotBox(touch, m) {
    return (
      touch.clientX >= m.plotLeft &&
      touch.clientX <= m.plotRight &&
      touch.clientY >= m.plotTop &&
      touch.clientY <= m.plotBottom
    );
  }

  function applyTouchActionPolicy() {
    var dragLayer = gd.querySelector('.nsewdrag');
    if (dragLayer) {
      dragLayer.style.touchAction = 'none';
    }
    gd.style.touchAction = 'pan-y';
  }
  applyTouchActionPolicy();
  gd.on('plotly_afterplot', applyTouchActionPolicy);

  function initPan(touch) {
    var m = getPlotMetrics();
    if (!m) return;
    touchMode = 'pan';
    panStartX = touch.clientX;
    panStartY = touch.clientY;
    panInitXRange = m.xRange;
    panInitYRange = m.yRange;
  }

  function initPinch(t1, t2) {
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
  }

  gd.addEventListener('touchstart', function(e) {
    if (!e.touches || e.touches.length === 0) return;
    var m = getPlotMetrics();
    if (!m) return;

    if (touchMode === null && !isInsidePlotBox(e.touches[0], m)) {
      return;
    }

    e.stopPropagation();

    if (e.touches.length === 1) {
      moved = false;
      initPan(e.touches[0]);
    } else if (e.touches.length >= 2) {
      moved = true;
      e.preventDefault();
      initPinch(e.touches[0], e.touches[1]);
    }
  }, { passive: false, capture: true });

  gd.addEventListener('touchmove', function(e) {
    if (!touchMode || !e.touches || e.touches.length === 0) return;
    var m = getPlotMetrics();
    if (!m) return;

    if (e.touches.length === 1 && touchMode === 'pan') {
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

      scheduleRelayout({
        'xaxis.range': clamped.x,
        'yaxis.range': clamped.y
      });
    } else if (e.touches.length >= 2) {
      if (touchMode !== 'pinch') {
        initPinch(e.touches[0], e.touches[1]);
        return;
      }
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

      scheduleRelayout({
        'xaxis.range': clamped.x,
        'yaxis.range': clamped.y
      });
    }
  }, { passive: false, capture: true });

  gd.addEventListener('touchend', function(e) {
    if (!touchMode) return;
    lastTouchEnd = Date.now();
    e.stopPropagation();

    if (e.touches.length === 1) {
      initPan(e.touches[0]);
    } else if (e.touches.length === 0) {
      if (!moved) {
        var now = Date.now();
        if (now - lastTapTime < 300) {
          lastTapTime = 0;
          zoomStack = [];
          Plotly.relayout(gd, {
            'xaxis.range': [FULL_X0, FULL_X1],
            'yaxis.range': [FULL_Y0, FULL_Y1]
          });
        } else {
          lastTapTime = now;
        }
      }
      touchMode = null;
      moved = false;
    }
  }, { passive: false, capture: true });
})();
"""

custom_interaction_js = (
    custom_interaction_js
    .replace("__FULL_X0__", str(full_x0))
    .replace("__FULL_X1__", str(full_x1))
    .replace("__FULL_Y0__", str(full_y0))
    .replace("__FULL_Y1__", str(full_y1))
)

# 9. Plotly 봉차트 생성 (일봉 / 주봉 동적 전환)
price_span = plot_df['High'].max() - plot_df['Low'].min()
min_body = price_span * 0.003 if price_span > 0 else 0.01
open_plot = np.where(
    np.abs(plot_df['Close'] - plot_df['Open']) < min_body,
    np.where(plot_df['Close'] >= plot_df['Open'], plot_df['Close'] - min_body, plot_df['Close'] + min_body),
    plot_df['Open']
)

ma_unit = "주선" if is_weekly_chart else "일선"
candle_label = f"{ticker} 주봉" if is_weekly_chart else f"{ticker} 일봉"

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=plot_df['Date_Str'],
    open=open_plot,
    high=plot_df['High'],
    low=plot_df['Low'],
    close=plot_df['Close'],
    increasing=dict(line=dict(color='#e53935', width=1.4), fillcolor='#e53935'),
    decreasing=dict(line=dict(color='#1e88e5', width=1.4), fillcolor='#1e88e5'),
    whiskerwidth=0.8,
    name=candle_label,
    hoverinfo='skip'
))

fig.add_trace(go.Scatter(
    x=plot_df['Date_Str'], y=plot_df['MA20'],
    mode='lines', name=f'20{ma_unit}',
    line=dict(color='#2e7d32', width=1.3),
    hoverinfo='skip'
))
fig.add_trace(go.Scatter(
    x=plot_df['Date_Str'], y=plot_df['MA120'],
    mode='lines', name=f'120{ma_unit}',
    line=dict(color='#ff8f00', width=1.4),
    hoverinfo='skip'
))
fig.add_trace(go.Scatter(
    x=plot_df['Date_Str'], y=plot_df['MA240'],
    mode='lines', name=f'240{ma_unit}',
    line=dict(color='#8e24aa', width=1.4),
    hoverinfo='skip'
))

fig.add_trace(go.Scatter(
    x=plot_df['Date_Str'], y=plot_df['Avg_Price'],
    mode='lines', name='평단선',
    line=dict(color='#00838f', width=2.0, dash='dash'),
    hoverinfo='skip'
))

# 매수 시그널 빨간 삼각형 (위쪽 꼭지점이 매수 금액에 맞도록 y 위치를 보정)
buy_points = plot_df[plot_df['Buy_Signal']].copy()
if not buy_points.empty:
    # 차트 세로 높이(540px) 대비 삼각형 반높이(~5.5px)만큼 아래로 배치해 위 꼭지점이 매수가에 닿게 설정
    y_data_span = full_y1 - full_y0
    tip_offset = y_data_span * (5.5 / 470.0)

    if is_weekly_chart:
        y_marker = buy_points['Week_Avg_Buy_Price'] - tip_offset
        if active_basis == "전일대비":
            custom_data = np.stack([
                buy_points['Date_Str'],
                buy_points['Week_Avg_Buy_Price'],
                buy_points['Week_Buy_Count'],
                buy_points['Avg_Price'],
                buy_points['Cum_Buy_Count'],
            ], axis=-1)
            hover_tpl = (
                f"<b>전일대비 {active_drop:.1f}% 하락 주간 매수 (누적 %{{customdata[4]:.0f}}주)</b><br>"
                "주간 기준일(마지막 영업일): %{customdata[0]}<br>"
                "해당 주 매수 수량: <b>%{customdata[2]:.0f}주</b><br>"
                "해당 주 평균 매수가: <b>$%{customdata[1]:.2f}</b><br>"
                "전체 누적 평단가: $%{customdata[3]:.2f}"
                "<extra></extra>"
            )
            legend_name = f'-{active_drop:.1f}% 매수 ({len(buy_points)}주간 / 총 {total_buys}주)'
        else:
            custom_data = np.stack([
                buy_points['Date_Str'],
                buy_points['Week_Avg_Buy_Price'],
                buy_points['Weekly_Pct_Change'],
                buy_points['Avg_Price'],
                buy_points['Cum_Buy_Count'],
            ], axis=-1)
            hover_tpl = (
                f"<b>전주대비 {active_drop:.1f}% 하락 시 매수 (누적 %{{customdata[4]:.0f}}주)</b><br>"
                "매수 날짜(주 마지막 영업일): %{customdata[0]}<br>"
                "매수 금액(주간 종가): <b>$%{customdata[1]:.2f}</b><br>"
                "전주 종가 대비 하락률: <b>%{customdata[2]:.2f}%</b><br>"
                "누적 평단가: $%{customdata[3]:.2f}"
                "<extra></extra>"
            )
            legend_name = f'-{active_drop:.1f}% 매수 ({len(buy_points)}/{len(plot_df)}주)'
    else:
        y_marker = buy_points['Buy_Price'] - tip_offset
        if active_basis == "전일대비":
            custom_data = np.stack([
                buy_points['Date_Str'],
                buy_points['Buy_Price'],
                buy_points['Daily_Pct_Change'],
                buy_points['Avg_Price'],
                buy_points['Cum_Buy_Count'],
            ], axis=-1)
            hover_tpl = (
                f"<b>전일대비 {active_drop:.1f}% 하락 시 매수 (누적 %{{customdata[4]:.0f}}주)</b><br>"
                "매수 날짜: %{customdata[0]}<br>"
                "매수 금액(종가): <b>$%{customdata[1]:.2f}</b><br>"
                "전일 종가 대비 하락률: <b>%{customdata[2]:.2f}%</b><br>"
                "누적 평단가: $%{customdata[3]:.2f}"
                "<extra></extra>"
            )
        else:
            custom_data = np.stack([
                buy_points['Date_Str'],
                buy_points['Buy_Price'],
                buy_points['Weekly_Pct_On_Day'],
                buy_points['Avg_Price'],
                buy_points['Cum_Buy_Count'],
            ], axis=-1)
            hover_tpl = (
                f"<b>전주대비 {active_drop:.1f}% 하락 시 매수 (누적 %{{customdata[4]:.0f}}주)</b><br>"
                "매수 날짜(주 마지막 영업일): %{customdata[0]}<br>"
                "매수 금액(종가): <b>$%{customdata[1]:.2f}</b><br>"
                "전주 종가 대비 하락률: <b>%{customdata[2]:.2f}%</b><br>"
                "누적 평단가: $%{customdata[3]:.2f}"
                "<extra></extra>"
            )
        legend_name = f'-{active_drop:.1f}% 매수 ({len(buy_points)}/{len(plot_df)}일)'

    fig.add_trace(go.Scatter(
        x=buy_points['Date_Str'],
        y=y_marker,
        mode='markers',
        marker=dict(
            symbol='triangle-up',
            size=9,
            color='#d93025',
            line=dict(color='black', width=0.6)
        ),
        name=legend_name,
        customdata=custom_data,
        hovertemplate=hover_tpl
    ))

# X축 날짜 눈금 간격 자동 조정
dt_index = pd.to_datetime(plot_df['Date_Str'])
month_starts = plot_df.groupby(dt_index.to_period('M')).head(1)
month_starts_dt = pd.to_datetime(month_starts['Date_Str'])

if is_weekly_chart:
    if len(plot_df) <= 30:
        tick_points = month_starts
    elif len(plot_df) <= 110:
        tick_points = month_starts[month_starts_dt.dt.month.isin([1, 4, 7, 10])]
    elif len(plot_df) <= 280:
        tick_points = month_starts[month_starts_dt.dt.month.isin([1, 7])]
    else:
        tick_points = month_starts[month_starts_dt.dt.month == 1]
else:
    if len(plot_df) <= 130:
        tick_points = month_starts
    elif len(plot_df) <= 400:
        tick_points = month_starts[month_starts_dt.dt.month.isin([1, 4, 7, 10])]
    elif len(plot_df) <= 1000:
        tick_points = month_starts[month_starts_dt.dt.month.isin([1, 7])]
    else:
        tick_points = month_starts[month_starts_dt.dt.month == 1]

fig.update_layout(
    autosize=True,
    height=540,
    template='plotly_white',
    dragmode='zoom',
    hovermode='closest',
    hoverdistance=15,
    xaxis=dict(
        type='category',
        range=[full_x0, full_x1],
        autorange=False,
        automargin=False,
        rangeslider=dict(visible=False),
        tickmode='array',
        tickvals=tick_points['Date_Str'],
        ticktext=pd.to_datetime(tick_points['Date_Str']).dt.strftime('%Y-%m'),
        tickfont=dict(size=10),
        showgrid=True,
        gridcolor='rgba(0,0,0,0.08)'
    ),
    yaxis=dict(
        title=None,
        tickprefix='$',
        ticklabelposition='inside',
        tickfont=dict(size=10, color='#555555'),
        automargin=False,
        range=[full_y0, full_y1],
        autorange=False,
        showgrid=True,
        gridcolor='rgba(0,0,0,0.08)'
    ),
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.01,
        xanchor='left',
        x=0,
        font=dict(size=10),
        itemsizing='constant'
    ),
    margin=dict(l=4, r=4, t=46, b=28)
)

iframe_reset_css = "<style>html, body { margin: 0 !important; padding: 0 !important; width: 100% !important; overflow-x: hidden; }</style>"
html_str = iframe_reset_css + pio.to_html(
    fig,
    include_plotlyjs='cdn',
    full_html=False,
    config={'responsive': True, 'displayModeBar': False},
    post_script=custom_interaction_js
)
components.html(html_str, height=545)
st.caption("💡 PC: 좌→우 드래그 확대 / 우→좌 드래그 축소 | 스마트폰: 봉차트 안쪽을 두 손가락으로 벌려 확대·오므려 축소 / 한 손가락 좌우 이동 / 두 번 탭 전체 복귀")
