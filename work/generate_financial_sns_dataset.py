# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SEED = 20260630
ROOT = Path(os.environ.get("DATASET_WORKSPACE", Path.cwd()))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", ROOT / "outputs" / "financial_sns_mydata_202606"))
SOURCE_API_DIR = Path(os.environ.get("SOURCE_API_DIR", "inputs/source_api_json"))
RESPONSE_SCHEMA_DIR = Path(os.environ.get("RESPONSE_SCHEMA_DIR", "inputs/response_schemas"))
SOURCE_XLSX_PATH = Path(os.environ.get("SOURCE_XLSX_PATH", "inputs/6월_한달_거래내역.xlsx"))
MINJI_DEMO_DIR = Path(os.environ.get("MINJI_DEMO_DIR", "inputs/mydata_realistic_persona_minji"))
MIN_ROWS = 60
MAX_ROWS = 180

LEDGER_COLUMNS = [
    "날짜",
    "시간",
    "타입",
    "대분류",
    "소분류",
    "내용",
    "금액",
    "화폐",
    "결제수단",
    "메모",
    "persona_id",
    "transaction_id",
    "cashflow_bucket",
    "account_ref",
    "api_ref",
]

ORIGINAL_COLUMNS = LEDGER_COLUMNS[:10]

BASE_RESPONSE = {
    "rsp_code": "00000",
    "rsp_msg": "SUCCESS",
}

STOCK_UNIVERSE = [
    {"prod_code": "005930", "prod_name": "삼성전자", "price": 76000, "prod_type": "101", "risk": 2},
    {"prod_code": "000660", "prod_name": "SK하이닉스", "price": 240000, "prod_type": "101", "risk": 4},
    {"prod_code": "035420", "prod_name": "NAVER", "price": 185000, "prod_type": "101", "risk": 3},
    {"prod_code": "035720", "prod_name": "카카오", "price": 48000, "prod_type": "101", "risk": 4},
    {"prod_code": "373220", "prod_name": "LG에너지솔루션", "price": 350000, "prod_type": "101", "risk": 4},
    {"prod_code": "069500", "prod_name": "KODEX 200", "price": 39000, "prod_type": "201", "risk": 1},
    {"prod_code": "379810", "prod_name": "KODEX 미국나스닥100TR", "price": 18000, "prod_type": "201", "risk": 3},
    {"prod_code": "091160", "prod_name": "KODEX 반도체", "price": 45000, "prod_type": "201", "risk": 4},
    {"prod_code": "133690", "prod_name": "TIGER 미국나스닥100", "price": 115000, "prod_type": "201", "risk": 3},
    {"prod_code": "229200", "prod_name": "KODEX 코스닥150", "price": 13000, "prod_type": "201", "risk": 5},
]

PAY_SERVICES = [
    {"service": "카카오페이", "method": "카카오페이 간편결제", "org_code": "06000001"},
    {"service": "네이버페이", "method": "네이버페이 간편결제", "org_code": "06000002"},
    {"service": "토스페이", "method": "토스 간편결제", "org_code": "06000003"},
]

CARD_NAMES = [
    "토스뱅크 체크카드",
    "하나 원더 체크카드",
    "프렌즈 체크카드",
    "어피치 스윗 체크카드",
    "KB 청춘대로 체크카드",
    "신한 Deep Dream 체크",
]

BANK_PRODUCTS = [
    "토스뱅크 통장",
    "하나핀크 생활통장",
    "NH주거래우대통장",
    "KB Star 청춘통장",
    "카카오뱅크 입출금통장",
]

SAVING_PRODUCTS = [
    "청년희망 적금",
    "세이프박스",
    "주택청약종합저축",
    "저축예금",
    "비상금 통장",
]

MERCHANTS = {
    ("식비", "한식"): ["김밥천국 홍대점", "담소소사골순대", "두끼 노량진역점", "한솥도시락 신촌점"],
    ("식비", "배달"): ["주식회사 우아한형제들", "쿠팡이츠", "요기요", "배민스토어"],
    ("카페/간식", "커피/음료"): ["스타벅스 합정점", "메가MGC커피", "컴포즈커피", "이디야커피"],
    ("카페/간식", "디저트/떡"): ["파리바게뜨", "배스킨라빈스", "던킨", "노티드"],
    ("교통", "대중교통"): ["티머니", "서울교통공사", "카카오버스", "모바일티머니"],
    ("교통", "택시"): ["카카오T 택시", "우티", "타다", "아이엠택시"],
    ("온라인쇼핑", "인터넷쇼핑"): ["쿠팡", "네이버쇼핑", "무신사", "11번가", "오늘의집"],
    ("생활", "편의점"): ["GS25", "CU", "세븐일레븐", "이마트24"],
    ("생활", "서비스구독"): ["넷플릭스", "유튜브 프리미엄", "멜론", "노션", "챗GPT"],
    ("생활", "마트"): ["이마트", "롯데마트", "홈플러스", "마켓컬리"],
    ("뷰티/미용", "화장품"): ["올리브영", "무신사뷰티", "아모레몰"],
    ("문화/여가", "도서"): ["교보문고", "알라딘", "예스24"],
    ("문화/여가", "공연/영화"): ["CGV", "메가박스", "인터파크티켓"],
    ("교육/학습", "학원/강의"): ["패스트캠퍼스", "클래스101", "인프런", "해커스"],
    ("의료/건강", "약국"): ["온누리약국", "플랜 B", "365약국"],
    ("여행/숙박", "숙박"): ["야놀자", "여기어때", "아고다"],
    ("패션/쇼핑", "패션"): ["무신사", "29CM", "지그재그", "에이블리"],
}

CATEGORY_WEIGHTS_BY_ARCHETYPE = {
    "학생/알바": {"식비": 20, "카페/간식": 14, "교통": 16, "온라인쇼핑": 11, "생활": 17, "문화/여가": 9, "교육/학습": 8, "패션/쇼핑": 5},
    "취준·지원": {"식비": 18, "카페/간식": 12, "교통": 15, "온라인쇼핑": 9, "생활": 20, "문화/여가": 5, "교육/학습": 15, "패션/쇼핑": 6},
    "사회초년생": {"식비": 20, "카페/간식": 13, "교통": 14, "온라인쇼핑": 15, "생활": 18, "문화/여가": 7, "뷰티/미용": 6, "교육/학습": 4, "패션/쇼핑": 3},
    "도시 직장인": {"식비": 18, "카페/간식": 12, "교통": 12, "온라인쇼핑": 18, "생활": 18, "문화/여가": 8, "뷰티/미용": 7, "여행/숙박": 4, "패션/쇼핑": 3},
    "절약·저축형": {"식비": 18, "카페/간식": 7, "교통": 16, "온라인쇼핑": 8, "생활": 28, "문화/여가": 4, "의료/건강": 5, "교육/학습": 8, "패션/쇼핑": 6},
    "소비·구독형": {"식비": 17, "카페/간식": 16, "교통": 10, "온라인쇼핑": 20, "생활": 17, "문화/여가": 10, "뷰티/미용": 5, "패션/쇼핑": 5},
    "프리랜서": {"식비": 17, "카페/간식": 15, "교통": 9, "온라인쇼핑": 13, "생활": 20, "문화/여가": 6, "교육/학습": 12, "의료/건강": 4, "패션/쇼핑": 4},
    "투자적극형": {"식비": 15, "카페/간식": 10, "교통": 10, "온라인쇼핑": 12, "생활": 16, "문화/여가": 7, "교육/학습": 12, "패션/쇼핑": 4, "여행/숙박": 4, "뷰티/미용": 3},
    "청약·내집마련형": {"식비": 15, "카페/간식": 8, "교통": 12, "온라인쇼핑": 10, "생활": 28, "문화/여가": 4, "교육/학습": 7, "의료/건강": 4, "패션/쇼핑": 2},
    "고소득 FIRE형": {"식비": 15, "카페/간식": 8, "교통": 8, "온라인쇼핑": 16, "생활": 18, "문화/여가": 8, "교육/학습": 11, "여행/숙박": 7, "패션/쇼핑": 4, "뷰티/미용": 5},
}

ARCHETYPES = [
    {
        "name": "학생/알바",
        "count": 20,
        "age": (19, 24),
        "income": (650_000, 1_700_000),
        "spend_ratio": (0.55, 0.88),
        "saving_rate": (0.05, 0.20),
        "invest_rate": (0.02, 0.08),
        "risk": (1, 3),
        "rows": (60, 115),
        "jobs": ["대학생/편의점 아르바이트", "대학생/카페 아르바이트", "휴학생/단기알바"],
        "households": ["부모동거", "쉐어하우스", "1인가구"],
        "goals": ["여행자금", "등록금 완충", "독립 준비"],
        "lifestyle": ["가성비", "캠퍼스생활", "간편결제선호"],
    },
    {
        "name": "취준·지원",
        "count": 16,
        "age": (23, 29),
        "income": (500_000, 1_400_000),
        "spend_ratio": (0.65, 1.05),
        "saving_rate": (0.02, 0.12),
        "invest_rate": (0.01, 0.05),
        "risk": (1, 2),
        "rows": (60, 105),
        "jobs": ["취업준비생", "국비교육 수강생", "인턴 준비생"],
        "households": ["부모동거", "1인가구", "쉐어하우스"],
        "goals": ["취업준비비 마련", "비상금", "자격증"],
        "lifestyle": ["절약", "교육투자", "불규칙수입"],
    },
    {
        "name": "사회초년생",
        "count": 32,
        "age": (24, 30),
        "income": (2_300_000, 3_800_000),
        "spend_ratio": (0.48, 0.78),
        "saving_rate": (0.12, 0.35),
        "invest_rate": (0.04, 0.16),
        "risk": (2, 4),
        "rows": (85, 150),
        "jobs": ["주니어 마케터", "신입 개발자", "영업관리 사원", "디자이너"],
        "households": ["1인가구", "부모동거", "쉐어하우스"],
        "goals": ["독립", "비상금", "첫 투자"],
        "lifestyle": ["출퇴근", "구독서비스", "점심외식"],
    },
    {
        "name": "도시 직장인",
        "count": 36,
        "age": (27, 34),
        "income": (3_300_000, 5_400_000),
        "spend_ratio": (0.45, 0.76),
        "saving_rate": (0.18, 0.42),
        "invest_rate": (0.08, 0.24),
        "risk": (2, 4),
        "rows": (95, 175),
        "jobs": ["서비스 기획자", "브랜드 매니저", "데이터 분석가", "대기업 사무직"],
        "households": ["1인가구", "신혼/동거", "부모동거"],
        "goals": ["내집마련", "여행", "커리어전환"],
        "lifestyle": ["도심생활", "모바일뱅킹", "외식"],
    },
    {
        "name": "절약·저축형",
        "count": 24,
        "age": (23, 34),
        "income": (2_000_000, 4_700_000),
        "spend_ratio": (0.30, 0.55),
        "saving_rate": (0.30, 0.58),
        "invest_rate": (0.02, 0.12),
        "risk": (1, 3),
        "rows": (70, 135),
        "jobs": ["공공기관 계약직", "회계 담당자", "간호조무사", "품질관리 사원"],
        "households": ["부모동거", "1인가구", "신혼/동거"],
        "goals": ["목돈 만들기", "청약", "비상금"],
        "lifestyle": ["무지출챌린지", "도시락", "자동저축"],
    },
    {
        "name": "소비·구독형",
        "count": 20,
        "age": (22, 33),
        "income": (2_100_000, 4_600_000),
        "spend_ratio": (0.65, 0.98),
        "saving_rate": (0.03, 0.18),
        "invest_rate": (0.02, 0.10),
        "risk": (2, 4),
        "rows": (110, 180),
        "jobs": ["콘텐츠 에디터", "패션 MD", "SNS 운영자", "영상 편집자"],
        "households": ["1인가구", "쉐어하우스", "부모동거"],
        "goals": ["취미생활", "여행", "카드혜택 최적화"],
        "lifestyle": ["구독다수", "온라인쇼핑", "취향소비"],
    },
    {
        "name": "프리랜서",
        "count": 17,
        "age": (24, 34),
        "income": (1_800_000, 5_200_000),
        "spend_ratio": (0.42, 0.85),
        "saving_rate": (0.08, 0.28),
        "invest_rate": (0.04, 0.18),
        "risk": (2, 4),
        "rows": (75, 150),
        "jobs": ["프리랜서 디자이너", "프리랜서 개발자", "강사", "1인 크리에이터"],
        "households": ["1인가구", "신혼/동거", "쉐어하우스"],
        "goals": ["세금준비", "장비구매", "수입 안정화"],
        "lifestyle": ["불규칙수입", "카페작업", "자기계발"],
    },
    {
        "name": "투자적극형",
        "count": 18,
        "age": (25, 34),
        "income": (2_800_000, 6_200_000),
        "spend_ratio": (0.35, 0.65),
        "saving_rate": (0.12, 0.35),
        "invest_rate": (0.18, 0.45),
        "risk": (4, 5),
        "rows": (90, 170),
        "jobs": ["핀테크 개발자", "증권사 주니어", "데이터 엔지니어", "IT 컨설턴트"],
        "households": ["1인가구", "부모동거", "신혼/동거"],
        "goals": ["포트폴리오 성장", "파이어", "배당소득"],
        "lifestyle": ["투자공유", "리밸런싱", "경제뉴스"],
    },
    {
        "name": "청약·내집마련형",
        "count": 10,
        "age": (27, 34),
        "income": (3_000_000, 5_600_000),
        "spend_ratio": (0.36, 0.60),
        "saving_rate": (0.30, 0.55),
        "invest_rate": (0.04, 0.16),
        "risk": (1, 3),
        "rows": (75, 145),
        "jobs": ["중견기업 사무직", "공무원", "제조업 엔지니어", "교직원"],
        "households": ["신혼/동거", "1인가구", "부모동거"],
        "goals": ["내집마련", "청약", "전세보증금"],
        "lifestyle": ["주거비관리", "청약저축", "장기계획"],
    },
    {
        "name": "고소득 FIRE형",
        "count": 6,
        "age": (29, 34),
        "income": (6_000_000, 9_500_000),
        "spend_ratio": (0.28, 0.52),
        "saving_rate": (0.28, 0.50),
        "invest_rate": (0.25, 0.55),
        "risk": (3, 5),
        "rows": (95, 170),
        "jobs": ["시니어 개발자", "전문직", "스타트업 리드", "외국계 PM"],
        "households": ["1인가구", "신혼/동거"],
        "goals": ["FIRE", "장기투자", "해외여행"],
        "lifestyle": ["고소득", "투자자동화", "시간절약"],
    },
]


@dataclass
class Account:
    kind: str
    account_id: str
    name: str
    display_name: str
    balance: float


@dataclass
class Card:
    card_id: str
    card_name: str
    card_num: str


@dataclass
class PersonaBundle:
    profile: dict[str, Any]
    accounts: dict[str, Account]
    cards: list[Card]
    ledger_rows: list[dict[str, Any]] = field(default_factory=list)
    bank_trans: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    card_approved: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    card_purchase: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    efinance_trans: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    efinance_wallet_trans: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: defaultdict(list))
    invest_trans: list[dict[str, Any]] = field(default_factory=list)
    portfolio: list[dict[str, Any]] = field(default_factory=list)
    social: dict[str, Any] = field(default_factory=dict)


def rng_for(*parts: Any) -> random.Random:
    h = hashlib.sha256(("|".join(map(str, parts)) + f"|{SEED}").encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def clean_filename(value: str) -> str:
    safe = value.replace("/", "_").replace("\\", "_").replace(" ", "_")
    for ch in '()[]{}:;,"\'':
        safe = safe.replace(ch, "")
    return safe


def ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def ymd_dash(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def hm(t: time) -> str:
    return t.strftime("%H:%M")


def dtime(d: date, t: time) -> str:
    return d.strftime("%Y%m%d") + t.strftime("%H%M%S")


def rand_date(rng: random.Random, start_day: int = 1, end_day: int = 30, weekend_bias: float = 0.0) -> date:
    while True:
        d = date(2026, 6, rng.randint(start_day, end_day))
        if d.weekday() >= 5 and rng.random() < weekend_bias:
            return d
        if rng.random() > weekend_bias / 2:
            return d


def rand_time(rng: random.Random, category: str = "normal") -> time:
    if category in {"식비", "카페/간식"}:
        hour = rng.choice([8, 9, 11, 12, 13, 18, 19, 20, 21])
    elif category == "교통":
        hour = rng.choice([7, 8, 9, 18, 19, 22, 23])
    elif category == "온라인쇼핑":
        hour = rng.choice([10, 12, 20, 21, 22, 23])
    else:
        hour = rng.randint(9, 23)
    return time(hour, rng.randint(0, 59), rng.randint(0, 59))


def choose_weighted(rng: random.Random, weights: dict[str, int]) -> str:
    total = sum(weights.values())
    mark = rng.uniform(0, total)
    upto = 0
    for key, weight in weights.items():
        upto += weight
        if upto >= mark:
            return key
    return next(reversed(weights))


def amount_for_category(rng: random.Random, category: str, archetype: str, income: int) -> int:
    base_ranges = {
        "식비": (6_500, 32_000),
        "카페/간식": (2_000, 12_000),
        "교통": (1_450, 32_000),
        "온라인쇼핑": (9_000, 120_000),
        "생활": (2_000, 85_000),
        "뷰티/미용": (8_000, 80_000),
        "문화/여가": (7_000, 65_000),
        "교육/학습": (12_000, 180_000),
        "의료/건강": (4_000, 55_000),
        "여행/숙박": (35_000, 260_000),
        "패션/쇼핑": (12_000, 150_000),
    }
    lo, hi = base_ranges.get(category, (5_000, 50_000))
    if archetype == "소비·구독형":
        hi = int(hi * 1.35)
    elif archetype in {"절약·저축형", "청약·내집마련형"}:
        hi = int(hi * 0.78)
    elif archetype == "고소득 FIRE형":
        lo = int(lo * 1.2)
        hi = int(hi * 1.7)
    if income < 1_800_000:
        hi = int(hi * 0.75)
    amount = int(rng.triangular(lo, hi, lo + (hi - lo) * 0.28))
    return int(round(amount / 100) * 100)


def persona_distribution() -> list[dict[str, Any]]:
    archetype_items: list[dict[str, Any]] = []
    # First 10 are one manually curated instance per archetype.
    for arch in ARCHETYPES:
        archetype_items.append(arch)
    for arch in ARCHETYPES:
        for _ in range(arch["count"] - 1):
            archetype_items.append(arch)
    assert len(archetype_items) == 199
    return archetype_items


def build_profile(idx: int, arch: dict[str, Any]) -> dict[str, Any]:
    pid = f"P{idx:03d}"
    rng = rng_for(pid, "profile")
    age = rng.randint(*arch["age"])
    income = int(round(rng.randint(*arch["income"]) / 10_000) * 10_000)
    spend_ratio = round(rng.uniform(*arch["spend_ratio"]), 3)
    saving_rate = round(rng.uniform(*arch["saving_rate"]), 3)
    invest_rate = round(rng.uniform(*arch["invest_rate"]), 3)
    risk_score = rng.randint(*arch["risk"])
    household = rng.choice(arch["households"])
    household_size = {"부모동거": rng.choice([3, 4]), "쉐어하우스": rng.choice([2, 3]), "1인가구": 1, "신혼/동거": 2}[household]
    job = rng.choice(arch["jobs"])
    goal = rng.choice(arch["goals"])
    lifestyle = sorted(set(rng.sample(arch["lifestyle"], k=min(len(arch["lifestyle"]), 2)) + [rng.choice(["배달선호", "대중교통", "모바일결제", "소액투자", "예산관리"])]))
    target_rows = rng.randint(*arch["rows"])
    target_rows = max(MIN_ROWS, min(MAX_ROWS, target_rows))
    sns_mode = rng.choice(["투자피드형", "절약챌린지형", "소비인사이트형", "목표공유형", "눈팅형"])
    region = rng.choice(["서울 마포구", "서울 관악구", "서울 성동구", "경기 성남시", "인천 부평구", "부산 해운대구", "대구 중구", "대전 서구", "광주 동구"])
    return {
        "persona_id": pid,
        "synthetic_name": f"가상청년 {pid}",
        "age": age,
        "birth_year": 2026 - age,
        "generation": "대한민국 청년(만19~34세)",
        "archetype": arch["name"],
        "job": job,
        "region": region,
        "monthly_income_krw": income,
        "income_band": band_income(income),
        "target_monthly_spend_krw": int(round(income * spend_ratio / 10_000) * 10_000),
        "spend_band": band_spend(int(income * spend_ratio)),
        "target_saving_rate": saving_rate,
        "target_investment_rate": invest_rate,
        "risk_score": risk_score,
        "risk_attitude": ["원금보전형", "안정추구형", "중립형", "성장추구형", "공격투자형"][risk_score - 1],
        "household_type": household,
        "household_size": household_size,
        "lifestyle_tags": lifestyle,
        "financial_goal": goal,
        "sns_tendency": sns_mode,
        "target_ledger_rows": target_rows,
        "data_month": "2026-06",
        "is_synthetic": True,
    }


def band_income(income: int) -> str:
    if income < 1_500_000:
        return "150만원 미만"
    if income < 2_500_000:
        return "150~250만원"
    if income < 3_500_000:
        return "250~350만원"
    if income < 5_000_000:
        return "350~500만원"
    if income < 7_000_000:
        return "500~700만원"
    return "700만원 이상"


def band_spend(spend: int) -> str:
    if spend < 900_000:
        return "90만원 미만"
    if spend < 1_500_000:
        return "90~150만원"
    if spend < 2_300_000:
        return "150~230만원"
    if spend < 3_200_000:
        return "230~320만원"
    return "320만원 이상"


def make_accounts(profile: dict[str, Any]) -> tuple[dict[str, Account], list[Card]]:
    pid = profile["persona_id"]
    rng = rng_for(pid, "accounts")
    main_name = rng.choice(BANK_PRODUCTS)
    accounts = {
        "main": Account("bank", f"{pid}-BANK-MAIN", "main", main_name, float(rng.randint(200_000, 2_500_000))),
        "savings": Account("bank", f"{pid}-BANK-SAVE", "savings", rng.choice(SAVING_PRODUCTS), float(rng.randint(100_000, 8_000_000))),
        "housing": Account("bank", f"{pid}-BANK-HOUSING", "housing", "주택청약종합저축", float(rng.randint(0, 12_000_000))),
        "wallet_kakao": Account("wallet", f"{pid}-WALLET-KAKAO", "wallet_kakao", "카카오페이 머니", float(rng.randint(5_000, 120_000))),
        "wallet_naver": Account("wallet", f"{pid}-WALLET-NAVER", "wallet_naver", "네이버페이 머니", float(rng.randint(2_000, 90_000))),
        "invest": Account("invest", f"{pid}-INV-001", "invest", rng.choice(["한국투자증권 종합계좌", "신한투자증권 종합계좌", "미래에셋증권 CMA", "토스증권 계좌"]), float(rng.randint(0, 500_000))),
    }
    card_count = 1 if profile["monthly_income_krw"] < 1_700_000 else rng.choice([1, 2, 2, 3])
    chosen_names = rng.sample(CARD_NAMES, k=card_count)
    cards = [
        Card(
            card_id=f"{pid}-CARD-{i + 1:02d}",
            card_name=name,
            card_num=f"9{rng.randint(1000, 9999)}-****-****-{rng.randint(1000, 9999)}",
        )
        for i, name in enumerate(chosen_names)
    ]
    return accounts, cards


def new_bundle(idx: int, arch: dict[str, Any]) -> PersonaBundle:
    profile = build_profile(idx, arch)
    accounts, cards = make_accounts(profile)
    return PersonaBundle(profile=profile, accounts=accounts, cards=cards)


def add_ledger_row(
    bundle: PersonaBundle,
    d: date,
    t: time,
    typ: str,
    category: str,
    subcategory: str,
    content: str,
    amount: int,
    payment: str,
    memo: str | None,
    bucket: str,
    account_ref: str,
    api_ref: str,
) -> dict[str, Any]:
    txid = f"{bundle.profile['persona_id']}-T{len(bundle.ledger_rows) + 1:04d}"
    row = {
        "날짜": ymd_dash(d),
        "시간": hm(t),
        "타입": typ,
        "대분류": category,
        "소분류": subcategory,
        "내용": content,
        "금액": int(amount),
        "화폐": "KRW",
        "결제수단": payment,
        "메모": memo,
        "persona_id": bundle.profile["persona_id"],
        "transaction_id": txid,
        "cashflow_bucket": bucket,
        "account_ref": account_ref,
        "api_ref": api_ref,
    }
    bundle.ledger_rows.append(row)
    return row


def bank_file_name(account: Account) -> str:
    return f"bank/은행-004-{clean_filename(account.display_name)}_{clean_filename(account.account_id)}.json"


def card_file_name(card: Card, kind: str) -> str:
    code = "008" if kind == "approved" else "014"
    title = "승인내역" if kind == "approved" else "매입정보"
    return f"card/카드-{code}-{clean_filename(card.card_name)}_{title}.json"


def efinance_file_name(service: str) -> str:
    return f"efinance/전금-103-{clean_filename(service)}.json"


def wallet_file_name(wallet: Account) -> str:
    return f"efinance/전금-004-{clean_filename(wallet.display_name)}.json"


def invest_file_name(account: Account) -> str:
    return f"invest/금투-003-{clean_filename(account.display_name)}.json"


def add_bank_trans(bundle: PersonaBundle, account_key: str, d: date, t: time, amount: int, trans_class: str, memo: str, txid: str | None = None) -> str:
    account = bundle.accounts[account_key]
    account.balance += amount
    trans_no = txid or f"B{bundle.profile['persona_id']}{len(bundle.bank_trans[account.account_id]) + 1:05d}"
    bundle.bank_trans[account.account_id].append(
        {
            "trans_dtime": dtime(d, t),
            "trans_no": trans_no,
            "trans_type": "03" if amount >= 0 else "02",
            "trans_class": trans_class,
            "currency_code": "KRW",
            "trans_amt": float(amount),
            "balance_amt": round(account.balance, 3),
            "paid_in_cnt": None,
            "trans_memo": memo,
        }
    )
    return f"{bank_file_name(account)}#{trans_no}"


def add_card_trans(bundle: PersonaBundle, card: Card, d: date, t: time, merchant: str, amount_abs: int, txid: str) -> str:
    approved_num = f"A{bundle.profile['persona_id']}{len(bundle.card_approved[card.card_id]) + 1:06d}"
    regno = fake_regno(bundle.profile["persona_id"], merchant)
    approved = {
        "approved_num": approved_num,
        "approved_dtime": dtime(d, t),
        "status": "01",
        "pay_type": "01",
        "trans_dtime": None,
        "merchant_name": merchant,
        "merchant_regno": regno,
        "approved_amt": float(amount_abs),
        "modified_amt": None,
        "total_install_cnt": None,
        "transaction_id": txid,
    }
    purchase = {
        "approved_num": approved_num,
        "merchant_name": merchant,
        "merchant_regno": regno,
        "purchase_dtime": dtime(d + timedelta(days=min(2, max(0, 30 - d.day))), t),
        "purchase_amt": float(amount_abs),
        "transaction_id": txid,
    }
    bundle.card_approved[card.card_id].append(approved)
    bundle.card_purchase[card.card_id].append(purchase)
    return f"{card_file_name(card, 'approved')}#{approved_num};{card_file_name(card, 'purchase')}#{approved_num}"


def add_efinance_trans(
    bundle: PersonaBundle,
    service: dict[str, str],
    d: date,
    t: time,
    merchant: str,
    amount_abs: int,
    title: str,
    category: str,
    txid: str,
    wallet_key: str | None = None,
) -> str:
    trans_num = f"E{bundle.profile['persona_id']}{service['service'][:1]}{len(bundle.efinance_trans[service['service']]) + 1:05d}"
    regno = fake_regno(bundle.profile["persona_id"], merchant)
    item = {
        "trans_type": "6101",
        "trans_num": trans_num,
        "trans_dtime": dtime(d, t),
        "trans_no": f"{len(bundle.efinance_trans[service['service']]) + 1:04d}",
        "currency_code": "KRW",
        "trans_amt": float(amount_abs),
        "trans_org_code": service["org_code"],
        "pay_type": "01",
        "pay_id": f"{bundle.profile['persona_id']}-{service['service']}-PAY",
        "approved_num": f"EP{bundle.profile['persona_id']}{len(bundle.efinance_trans[service['service']]) + 1:05d}",
        "card_name": None,
        "total_install_cnt": None,
        "trans_memo": "간편결제",
        "merchant_name": merchant,
        "merchant_regno": regno,
        "trans_title": title,
        "trans_category": category,
        "pay_method": "01",
        "transaction_id": txid,
    }
    bundle.efinance_trans[service["service"]].append(item)
    refs = [f"{efinance_file_name(service['service'])}#{trans_num}"]
    if wallet_key:
        wallet = bundle.accounts[wallet_key]
        wallet.balance -= amount_abs
        wallet_trans_no = f"W{bundle.profile['persona_id']}{len(bundle.efinance_wallet_trans[wallet.account_id]) + 1:05d}"
        bundle.efinance_wallet_trans[wallet.account_id].append(
            {
                "trans_type": "04",
                "trans_num": trans_num,
                "trans_dtime": dtime(d, t),
                "trans_no": wallet_trans_no,
                "currency_code": "KRW",
                "trans_amt": float(-amount_abs),
                "trans_org_code": service["org_code"],
                "trans_memo": "머니 결제",
                "merchant_name": merchant,
                "trans_title": title,
                "trans_category": category,
            }
        )
        refs.append(f"{wallet_file_name(wallet)}#{wallet_trans_no}")
    return ";".join(refs)


def fake_regno(pid: str, seed_value: str) -> str:
    h = int(hashlib.md5(f"{pid}:{seed_value}:{SEED}".encode("utf-8")).hexdigest()[:9], 16)
    return f"{100 + h % 800}-{10 + (h // 7) % 80}-{10000 + (h // 13) % 80000}"


def generate_income(bundle: PersonaBundle) -> None:
    profile = bundle.profile
    rng = rng_for(profile["persona_id"], "income")
    income = int(profile["monthly_income_krw"])
    arch = profile["archetype"]
    if arch in {"학생/알바", "취준·지원", "프리랜서"}:
        chunks = rng.choice([2, 3, 4])
        remaining = income
        days = sorted(rng.sample(range(3, 29), k=chunks))
        for i, day in enumerate(days):
            if i == chunks - 1:
                amt = remaining
            else:
                amt = int(round(rng.uniform(0.18, 0.42) * income / 10_000) * 10_000)
                amt = max(80_000, min(remaining - 50_000, amt))
                remaining -= amt
            d = date(2026, 6, day)
            t = time(rng.randint(9, 17), rng.randint(0, 59), rng.randint(0, 59))
            trans_no = f"INC{profile['persona_id']}{i + 1:03d}"
            api_ref = add_bank_trans(bundle, "main", d, t, amt, "소득입금", "6월 수입", trans_no)
            add_ledger_row(bundle, d, t, "수입", "근로소득" if arch != "취준·지원" else "기타수입", "급여/용역", "6월 수입", amt, bundle.accounts["main"].display_name, None, "소득", bundle.accounts["main"].account_id, api_ref)
    else:
        d = date(2026, 6, rng.choice([24, 25, 26, 28]))
        t = time(rng.randint(8, 10), rng.randint(0, 59), rng.randint(0, 59))
        api_ref = add_bank_trans(bundle, "main", d, t, income, "급여이체", "6월 월급", f"PAY{profile['persona_id']}")
        add_ledger_row(bundle, d, t, "수입", "근로소득", "급여", "6월 월급", income, bundle.accounts["main"].display_name, None, "소득", bundle.accounts["main"].account_id, api_ref)
    cashback_count = rng.randint(1, 4)
    for i in range(cashback_count):
        d = rand_date(rng, 5, 29)
        t = rand_time(rng)
        amt = rng.randint(20, 900)
        api_ref = add_bank_trans(bundle, "main", d, t, amt, "캐시백", "카드 캐시백")
        add_ledger_row(bundle, d, t, "수입", "금융수입", "캐시백", "카드 캐시백", amt, bundle.accounts["main"].display_name, None, "소득", bundle.accounts["main"].account_id, api_ref)


def generate_fixed_outflows(bundle: PersonaBundle) -> None:
    profile = bundle.profile
    rng = rng_for(profile["persona_id"], "fixed")
    income = profile["monthly_income_krw"]
    household = profile["household_type"]
    if household == "1인가구":
        rent = int(round(rng.uniform(0.16, 0.28) * income / 10_000) * 10_000)
        rent = max(330_000, min(1_250_000, rent))
    elif household == "신혼/동거":
        rent = int(round(rng.uniform(0.10, 0.20) * income / 10_000) * 10_000)
        rent = max(250_000, min(950_000, rent))
    elif household == "쉐어하우스":
        rent = int(round(rng.uniform(0.12, 0.20) * income / 10_000) * 10_000)
        rent = max(230_000, min(650_000, rent))
    else:
        rent = rng.choice([0, 50_000, 100_000, 150_000, 200_000])
    if rent:
        d = date(2026, 6, rng.choice([1, 2, 25]))
        t = time(9, rng.randint(0, 59), rng.randint(0, 59))
        api_ref = add_bank_trans(bundle, "main", d, t, -rent, "자동이체", "주거비")
        add_ledger_row(bundle, d, t, "지출", "주거", "월세/관리비", "주거비 자동이체", -rent, bundle.accounts["main"].display_name, None, "소비", bundle.accounts["main"].account_id, api_ref)
    fixed_items = [
        ("생활", "통신", "휴대폰 요금", int(round(rng.randint(45_000, 110_000) / 100) * 100)),
        ("생활", "서비스구독", "구독 서비스", int(round(rng.randint(9_900, 45_000) / 100) * 100)),
    ]
    if profile["archetype"] in {"소비·구독형", "도시 직장인", "고소득 FIRE형"}:
        fixed_items.append(("생활", "서비스구독", "추가 구독 서비스", int(round(rng.randint(9_900, 65_000) / 100) * 100)))
    if profile["age"] >= 27 or profile["monthly_income_krw"] >= 3_000_000:
        fixed_items.append(("금융", "보험", "실손보험료", int(round(rng.randint(28_000, 95_000) / 100) * 100)))
    for idx, (cat, sub, content, amt) in enumerate(fixed_items):
        d = date(2026, 6, rng.randint(5, 25))
        t = time(rng.randint(8, 21), rng.randint(0, 59), rng.randint(0, 59))
        if rng.random() < 0.45 and bundle.cards:
            placeholder_txid = f"{bundle.profile['persona_id']}-T{len(bundle.ledger_rows) + 1:04d}"
            card = rng.choice(bundle.cards)
            api_ref = add_card_trans(bundle, card, d, t, content, amt, placeholder_txid)
            payment = card.card_name
            account_ref = card.card_id
        else:
            api_ref = add_bank_trans(bundle, "main", d, t, -amt, "자동이체", content)
            payment = bundle.accounts["main"].display_name
            account_ref = bundle.accounts["main"].account_id
        add_ledger_row(bundle, d, t, "지출", cat, sub, content, -amt, payment, None, "소비", account_ref, api_ref)


def generate_savings(bundle: PersonaBundle) -> None:
    profile = bundle.profile
    rng = rng_for(profile["persona_id"], "savings")
    income = profile["monthly_income_krw"]
    total_saving = int(round(income * profile["target_saving_rate"] / 10_000) * 10_000)
    total_saving = max(30_000, total_saving)
    splits = [0.55, 0.25, 0.20] if profile["financial_goal"] in {"내집마련", "청약", "전세보증금"} else [0.65, 0.15, 0.20]
    targets = ["savings", "housing", "savings"]
    names = ["적금 자동이체", "청약 납입", "비상금 이체"]
    for i, (ratio, account_key, name) in enumerate(zip(splits, targets, names, strict=True)):
        amt = int(round(total_saving * ratio / 10_000) * 10_000)
        if amt <= 0:
            continue
        d = date(2026, 6, rng.choice([3, 10, 25, 26, 28]))
        t = time(rng.randint(8, 18), rng.randint(0, 59), rng.randint(0, 59))
        main_ref = add_bank_trans(bundle, "main", d, t, -amt, "내계좌이체", name)
        target_ref = add_bank_trans(bundle, account_key, d, t, amt, "내계좌이체", name)
        refs = f"{main_ref};{target_ref}"
        add_ledger_row(bundle, d, t, "이체", "저축", "예적금/청약", name, -amt, bundle.accounts["main"].display_name, None, "저축", f"{bundle.accounts['main'].account_id}->{bundle.accounts[account_key].account_id}", refs)


def generate_investments(bundle: PersonaBundle) -> None:
    profile = bundle.profile
    rng = rng_for(profile["persona_id"], "invest")
    income = profile["monthly_income_krw"]
    risk = profile["risk_score"]
    budget = int(round(max(30_000, income * profile["target_investment_rate"]) / 10_000) * 10_000)
    eligible = [s for s in STOCK_UNIVERSE if s["risk"] <= max(2, risk + 1)]
    if risk <= 2:
        eligible = [s for s in eligible if s["prod_type"] == "201" or s["prod_code"] in {"005930", "035720"}]
    product_count = min(len(eligible), 1 + (1 if risk >= 3 else 0) + (1 if budget > 600_000 else 0) + (1 if risk >= 5 else 0))
    picks = rng.sample(eligible, k=max(1, product_count))
    remaining = max(budget, min(s["price"] for s in picks))
    holdings: dict[str, dict[str, Any]] = {}
    for i, stock in enumerate(picks):
        alloc = remaining / (len(picks) - i)
        shares = max(1, int(alloc // stock["price"]))
        gross = shares * stock["price"]
        if gross > remaining and i > 0:
            shares = max(1, int(remaining // stock["price"]))
            gross = shares * stock["price"]
        if gross <= 0:
            continue
        commission = max(100, int(gross * 0.00015))
        settle = gross + commission
        d = date(2026, 6, rng.randint(1, 18))
        t = time(rng.randint(9, 15), rng.randint(0, 59), rng.randint(0, 59))
        trans_no = f"STK{profile['persona_id']}{len(bundle.invest_trans) + 1:04d}"
        invest_item = {
            "prod_name": stock["prod_name"],
            "prod_code": stock["prod_code"],
            "trans_dtime": dtime(d, t),
            "Bod": "매수",
            "trans_no": trans_no,
            "trans_type": "101",
            "trans_type_detail": "현금매수",
            "trans_num": float(shares),
            "trans_unit": "주" if stock["prod_type"] == "101" else "좌",
            "base_amt": float(stock["price"]),
            "trans_amt": float(gross),
            "settle_amt": float(settle),
            "balance_amt": round(bundle.accounts["invest"].balance + settle, 3),
            "currency_code": "KRW",
            "trans_memo": f"{stock['prod_name']} 매수",
            "ex_code": "001",
        }
        bundle.invest_trans.append(invest_item)
        main_ref = add_bank_trans(bundle, "main", d, t, -settle, "증권이체", f"{stock['prod_name']} 매수")
        api_ref = f"{main_ref};{invest_file_name(bundle.accounts['invest'])}#{trans_no}"
        add_ledger_row(bundle, d, t, "이체", "투자", "국내주식/ETF", f"{stock['prod_name']} {shares}주 매수", -settle, bundle.accounts["main"].display_name, None, "투자", f"{bundle.accounts['main'].account_id}->{bundle.accounts['invest'].account_id}", api_ref)
        holdings[stock["prod_code"]] = {
            "stock": stock,
            "shares": float(shares),
            "purchase_amt": float(gross),
            "unit": "주" if stock["prod_type"] == "101" else "좌",
        }
        remaining -= settle
    if risk >= 4 and holdings and rng.random() < 0.45:
        code = rng.choice(list(holdings.keys()))
        holding = holdings[code]
        if holding["shares"] >= 2:
            sell_shares = max(1, int(holding["shares"] * rng.uniform(0.15, 0.35)))
            stock = holding["stock"]
            sell_price = int(stock["price"] * rng.uniform(0.96, 1.08))
            gross = sell_shares * sell_price
            settle = gross - max(100, int(gross * 0.00015))
            d = date(2026, 6, rng.randint(19, 29))
            t = time(rng.randint(9, 15), rng.randint(0, 59), rng.randint(0, 59))
            trans_no = f"STK{profile['persona_id']}{len(bundle.invest_trans) + 1:04d}"
            bundle.invest_trans.append(
                {
                    "prod_name": stock["prod_name"],
                    "prod_code": stock["prod_code"],
                    "trans_dtime": dtime(d, t),
                    "Bod": "매도",
                    "trans_no": trans_no,
                    "trans_type": "201",
                    "trans_type_detail": "현금매도",
                    "trans_num": float(sell_shares),
                    "trans_unit": holding["unit"],
                    "base_amt": float(sell_price),
                    "trans_amt": float(gross),
                    "settle_amt": float(settle),
                    "balance_amt": round(bundle.accounts["invest"].balance + settle, 3),
                    "currency_code": "KRW",
                    "trans_memo": f"{stock['prod_name']} 일부 매도",
                    "ex_code": "001",
                }
            )
            holding["shares"] -= sell_shares
            holding["purchase_amt"] *= holding["shares"] / (holding["shares"] + sell_shares)
            bank_ref = add_bank_trans(bundle, "main", d, t, settle, "증권입금", f"{stock['prod_name']} 매도대금")
            api_ref = f"{bank_ref};{invest_file_name(bundle.accounts['invest'])}#{trans_no}"
            add_ledger_row(bundle, d, t, "이체", "투자", "매도대금", f"{stock['prod_name']} {sell_shares}주 매도", settle, bundle.accounts["main"].display_name, None, "투자", f"{bundle.accounts['invest'].account_id}->{bundle.accounts['main'].account_id}", api_ref)
    for holding in holdings.values():
        stock = holding["stock"]
        if holding["shares"] <= 0:
            continue
        fluctuation = rng.uniform(0.88, 1.18) if risk >= 4 else rng.uniform(0.94, 1.10)
        eval_amt = holding["shares"] * stock["price"] * fluctuation
        bundle.portfolio.append(
            {
                "prod_type": stock["prod_type"],
                "prod_type_detail": "001",
                "prod_code": stock["prod_code"],
                "ex_code": "001",
                "prod_name": stock["prod_name"],
                "pos_type": "01",
                "credit_type": "00",
                "is_tax_benefits": stock["prod_type"] == "201" and profile["financial_goal"] in {"FIRE", "장기투자", "내집마련"},
                "purchase_amt": round(holding["purchase_amt"], 3),
                "holding_num": round(holding["shares"], 8),
                "trans_unit": holding["unit"],
                "eval_amt": round(eval_amt, 3),
                "is_execution": True,
                "currency_code": "KRW",
            }
        )


def generate_variable_spend(bundle: PersonaBundle) -> None:
    profile = bundle.profile
    rng = rng_for(profile["persona_id"], "spend")
    target_rows = profile["target_ledger_rows"]
    weights = CATEGORY_WEIGHTS_BY_ARCHETYPE[profile["archetype"]]
    while len(bundle.ledger_rows) < target_rows:
        category = choose_weighted(rng, weights)
        choices = [k for k in MERCHANTS if k[0] == category]
        if not choices:
            choices = list(MERCHANTS)
        cat, sub = rng.choice(choices)
        merchant = rng.choice(MERCHANTS[(cat, sub)])
        amount = amount_for_category(rng, cat, profile["archetype"], profile["monthly_income_krw"])
        d = rand_date(rng, 1, 30, weekend_bias=0.35 if cat in {"문화/여가", "여행/숙박", "온라인쇼핑"} else 0.12)
        t = rand_time(rng, cat)
        payment_choice = rng.random()
        placeholder_txid = f"{bundle.profile['persona_id']}-T{len(bundle.ledger_rows) + 1:04d}"
        if payment_choice < 0.52 and bundle.cards:
            card = rng.choice(bundle.cards)
            api_ref = add_card_trans(bundle, card, d, t, merchant, amount, placeholder_txid)
            payment = card.card_name
            account_ref = card.card_id
        elif payment_choice < 0.82:
            service = rng.choice(PAY_SERVICES)
            wallet_key = None
            if rng.random() < 0.30:
                wallet_key = "wallet_kakao" if service["service"] == "카카오페이" else ("wallet_naver" if service["service"] == "네이버페이" else None)
            api_ref = add_efinance_trans(bundle, service, d, t, merchant, amount, f"{sub} 결제", cat, placeholder_txid, wallet_key)
            payment = service["method"]
            account_ref = f"{bundle.profile['persona_id']}-{service['service']}"
        else:
            api_ref = add_bank_trans(bundle, "main", d, t, -amount, "계좌출금", merchant)
            payment = bundle.accounts["main"].display_name
            account_ref = bundle.accounts["main"].account_id
        memo = None
        if profile["archetype"] == "절약·저축형" and rng.random() < 0.12:
            memo = "예산 내 소비"
        elif profile["archetype"] == "소비·구독형" and cat in {"생활", "온라인쇼핑"} and rng.random() < 0.10:
            memo = "취향소비"
        add_ledger_row(bundle, d, t, "지출", cat, sub, merchant, -amount, payment, memo, "소비", account_ref, api_ref)


def generate_persona(idx: int, arch: dict[str, Any]) -> PersonaBundle:
    bundle = new_bundle(idx, arch)
    generate_income(bundle)
    generate_fixed_outflows(bundle)
    generate_savings(bundle)
    generate_investments(bundle)
    generate_variable_spend(bundle)
    bundle.ledger_rows.sort(key=lambda r: (r["날짜"], r["시간"], r["transaction_id"]), reverse=True)
    return bundle


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def response_header(tran_id: str) -> dict[str, Any]:
    return {"x-api-tran-id": tran_id, **BASE_RESPONSE}


def write_bundle(bundle: PersonaBundle, all_persona_ids: list[str]) -> dict[str, Any]:
    pid = bundle.profile["persona_id"]
    root = OUTPUT_ROOT / "bundles" / pid
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "profile.json", bundle.profile)
    ledger_df = pd.DataFrame(bundle.ledger_rows, columns=LEDGER_COLUMNS)
    ledger_df.to_csv(root / "ledger.csv", index=False, encoding="utf-8-sig")
    ledger_df.to_excel(root / "ledger.xlsx", index=False, sheet_name="ledger")
    files: dict[str, dict[str, Any]] = {}
    common = {
        **response_header(f"{pid}-정보제공-공통-002"),
        "is_scheduled": True,
        "fnd_cycle": "1m",
        "add_cycle": "1d",
        "end_date": "20271231",
        "purpose": "금융 SNS 설계용 합성 MyData 샘플",
        "period": "20260601-20260630",
        "is_consent_trans_memo": True,
        "is_consent_merchant_name_regno": True,
        "is_consent_trans_category": True,
    }
    write_json(root / "api" / "common" / "정보제공-공통-002.json", common)
    files["정보제공-공통-002"] = {"file_name": "api/common/정보제공-공통-002.json"}

    bank_accounts = [bundle.accounts[k] for k in ["main", "savings", "housing"]]
    bank001 = {
        **response_header(f"{pid}-은행-001"),
        "search_timestamp": "20260630235900",
        "reg_date": "20260601",
        "next_page": None,
        "account_cnt": len(bank_accounts),
        "account_list": [
            {
                "account_num": acct.account_id,
                "is_consent": True,
                "seqno": None,
                "is_foreign_deposit": False,
                "prod_name": acct.display_name,
                "is_minus": False,
                "account_type": "01" if acct.name == "main" else "02",
                "account_status": "01",
            }
            for acct in bank_accounts
        ],
    }
    write_json(root / "api" / "bank" / "은행-001-계좌_목록_조회.json", bank001)
    files["은행-001"] = {"file_name": "api/bank/은행-001-계좌_목록_조회.json"}
    for acct in bank_accounts:
        data = {
            **response_header(f"{pid}-은행-004-{acct.account_id}"),
            "next_page": None,
            "trans_cnt": len(bundle.bank_trans[acct.account_id]),
            "trans_list": sorted(bundle.bank_trans[acct.account_id], key=lambda x: x["trans_dtime"], reverse=True),
        }
        rel = bank_file_name(acct)
        write_json(root / "api" / rel, data)
    files["은행-004"] = {"file_name_pattern": "api/bank/은행-004-*.json"}

    card001 = {
        **response_header(f"{pid}-카드-001"),
        "search_timestamp": "20260630235900",
        "next_page": None,
        "card_cnt": len(bundle.cards),
        "card_list": [
            {
                "card_id": c.card_id,
                "card_num": c.card_num,
                "is_consent": True,
                "card_name": c.card_name,
                "card_member": "1",
                "card_type": "02",
            }
            for c in bundle.cards
        ],
    }
    write_json(root / "api" / "card" / "카드-001-카드_목록_조회.json", card001)
    files["카드-001"] = {"file_name": "api/card/카드-001-카드_목록_조회.json"}
    for c in bundle.cards:
        approved = {
            **response_header(f"{pid}-카드-008-{c.card_id}"),
            "next_page": None,
            "approved_cnt": len(bundle.card_approved[c.card_id]),
            "approved_list": sorted(bundle.card_approved[c.card_id], key=lambda x: x["approved_dtime"], reverse=True),
        }
        purchase = {
            **response_header(f"{pid}-카드-014-{c.card_id}"),
            "next_page": None,
            "purchase_cnt": len(bundle.card_purchase[c.card_id]),
            "purchase_list": sorted(bundle.card_purchase[c.card_id], key=lambda x: x["purchase_dtime"], reverse=True),
        }
        write_json(root / "api" / card_file_name(c, "approved"), approved)
        write_json(root / "api" / card_file_name(c, "purchase"), purchase)
    files["카드-008"] = {"file_name_pattern": "api/card/카드-008-*.json"}
    files["카드-014"] = {"file_name_pattern": "api/card/카드-014-*.json"}

    wallets = [bundle.accounts["wallet_kakao"], bundle.accounts["wallet_naver"]]
    efin001 = {
        **response_header(f"{pid}-전금-001"),
        "search_timestamp": "20260630235900",
        "next_page": None,
        "account_cnt": len(wallets),
        "account_list": [
            {
                "account_id": w.account_id,
                "is_consent": True,
                "fob_name": w.display_name,
                "account_type": "01",
                "account_status": "01",
            }
            for w in wallets
        ],
    }
    write_json(root / "api" / "efinance" / "전금-001-선불전자지급수단_목록_조회.json", efin001)
    for w in wallets:
        data = {
            **response_header(f"{pid}-전금-004-{w.account_id}"),
            "next_page": None,
            "trans_cnt": len(bundle.efinance_wallet_trans[w.account_id]),
            "trans_list": sorted(bundle.efinance_wallet_trans[w.account_id], key=lambda x: x["trans_dtime"], reverse=True),
        }
        write_json(root / "api" / wallet_file_name(w), data)
    efin101_accounts = [
        {
            "account_id": f"{pid}-{svc['service']}",
            "is_consent": True,
            "account_type": "01",
            "account_status": "01",
            "account_name": svc["service"],
        }
        for svc in PAY_SERVICES
    ]
    efin101 = {
        **response_header(f"{pid}-전금-101"),
        "search_timestamp": "20260630235900",
        "next_page": None,
        "account_cnt": len(efin101_accounts),
        "account_list": efin101_accounts,
    }
    write_json(root / "api" / "efinance" / "전금-101-계정_목록_조회.json", efin101)
    for svc in PAY_SERVICES:
        pay_list = [
            {"pay_org_code": svc["org_code"], "pay_type": "01", "pay_id": f"{pid}-{svc['service']}-PAY", "is_primary": True}
        ]
        efin102 = {**response_header(f"{pid}-전금-102-{svc['service']}"), "search_timestamp": "20260630235900", "pay_cnt": len(pay_list), "pay_list": pay_list}
        efin103 = {
            **response_header(f"{pid}-전금-103-{svc['service']}"),
            "next_page": None,
            "trans_cnt": len(bundle.efinance_trans[svc["service"]]),
            "trans_list": sorted(bundle.efinance_trans[svc["service"]], key=lambda x: x["trans_dtime"], reverse=True),
        }
        write_json(root / "api" / "efinance" / f"전금-102-{clean_filename(svc['service'])}.json", efin102)
        write_json(root / "api" / efinance_file_name(svc["service"]), efin103)
    files["전금-001"] = {"file_name": "api/efinance/전금-001-선불전자지급수단_목록_조회.json"}
    files["전금-004"] = {"file_name_pattern": "api/efinance/전금-004-*.json"}
    files["전금-101"] = {"file_name": "api/efinance/전금-101-계정_목록_조회.json"}
    files["전금-102"] = {"file_name_pattern": "api/efinance/전금-102-*.json"}
    files["전금-103"] = {"file_name_pattern": "api/efinance/전금-103-*.json"}

    invest_acct = bundle.accounts["invest"]
    invest001 = {
        **response_header(f"{pid}-금투-001"),
        "search_timestamp": "20260630235900",
        "next_page": None,
        "account_cnt": 1,
        "account_list": [
            {
                "account_num": invest_acct.account_id,
                "is_consent": True,
                "account_name": invest_acct.display_name,
                "account_type": "01",
                "issue_date": "20250115",
                "is_tax_benefits": any(p["is_tax_benefits"] for p in bundle.portfolio),
                "is_cma": "CMA" in invest_acct.display_name,
                "is_stock_trans": True,
                "is_account_link": True,
            }
        ],
    }
    invest002 = {
        **response_header(f"{pid}-금투-002"),
        "search_timestamp": "20260630235900",
        "base_date": "20260630",
        "basic_cnt": 1,
        "basic_list": [
            {
                "currency_code": "KRW",
                "withholdings_amt": 0.0,
                "credit_loan_amt": 0.0,
                "mortgage_amt": 0.0,
                "avail_balance": round(max(0, invest_acct.balance), 3),
            }
        ],
    }
    invest003 = {
        **response_header(f"{pid}-금투-003-{invest_acct.account_id}"),
        "next_page": None,
        "trans_cnt": len(bundle.invest_trans),
        "trans_list": sorted(bundle.invest_trans, key=lambda x: x["trans_dtime"], reverse=True),
    }
    invest004 = {
        **response_header(f"{pid}-금투-004-{invest_acct.account_id}"),
        "search_timestamp": "20260630235900",
        "next_page": None,
        "base_date": "20260630",
        "prod_cnt": len(bundle.portfolio),
        "prod_list": sorted(bundle.portfolio, key=lambda x: x["prod_code"]),
    }
    write_json(root / "api" / "invest" / "금투-001-계좌_목록_조회.json", invest001)
    write_json(root / "api" / "invest" / "금투-002-계좌_기본정보_조회.json", invest002)
    write_json(root / "api" / invest_file_name(invest_acct), invest003)
    write_json(root / "api" / "invest" / f"금투-004-{clean_filename(invest_acct.display_name)}.json", invest004)
    files["금투-001"] = {"file_name": "api/invest/금투-001-계좌_목록_조회.json"}
    files["금투-002"] = {"file_name": "api/invest/금투-002-계좌_기본정보_조회.json"}
    files["금투-003"] = {"file_name_pattern": "api/invest/금투-003-*.json"}
    files["금투-004"] = {"file_name_pattern": "api/invest/금투-004-*.json"}

    write_social(bundle, root, all_persona_ids)
    manifest = {
        "persona_id": pid,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "ledger_rows": len(bundle.ledger_rows),
        "api_scope": sorted(files.keys()),
        "files": files,
        "source_references": {
            "source_api_json": str(SOURCE_API_DIR),
            "response_schemas": str(RESPONSE_SCHEMA_DIR),
        },
    }
    write_json(root / "manifest.json", manifest)
    return manifest


def write_social(bundle: PersonaBundle, root: Path, all_persona_ids: list[str]) -> None:
    profile = bundle.profile
    rng = rng_for(profile["persona_id"], "social")
    handle = f"fin_{profile['persona_id'].lower()}_{rng.choice(['save','flow','folio','daily','young'])}"
    candidates = [p for p in all_persona_ids if p != profile["persona_id"]]
    follow_count = rng.randint(5, 24)
    follows = sorted(rng.sample(candidates, k=min(follow_count, len(candidates))))
    spend = sum(-r["금액"] for r in bundle.ledger_rows if r["cashflow_bucket"] == "소비" and r["금액"] < 0)
    saving = sum(-r["금액"] for r in bundle.ledger_rows if r["cashflow_bucket"] == "저축" and r["금액"] < 0)
    invest_buy = sum(-r["금액"] for r in bundle.ledger_rows if r["cashflow_bucket"] == "투자" and r["금액"] < 0)
    income = sum(r["금액"] for r in bundle.ledger_rows if r["cashflow_bucket"] == "소득" and r["금액"] > 0)
    posts = []
    top_cat = Counter(r["대분류"] for r in bundle.ledger_rows if r["cashflow_bucket"] == "소비").most_common(1)
    post_templates = [
        ("saving_milestone", "이번 달 저축률 기록", f"6월 수입 대비 저축률 {saving / income:.1%} 달성"),
        ("investment_trade", "포트폴리오 업데이트", f"6월 투자 매수 {invest_buy:,.0f}원, 보유 종목 {len(bundle.portfolio)}개"),
        ("spend_pattern", "소비 카테고리 회고", f"가장 큰 소비 카테고리는 {top_cat[0][0] if top_cat else '생활'}"),
    ]
    if profile["sns_tendency"] != "눈팅형":
        post_count = rng.randint(2, 5)
    else:
        post_count = rng.randint(0, 2)
    for i, (ptype, title, body) in enumerate(post_templates[:post_count]):
        d = date(2026, 6, rng.randint(7, 30))
        posts.append(
            {
                "post_id": f"{profile['persona_id']}-POST-{i + 1:03d}",
                "persona_id": profile["persona_id"],
                "handle": handle,
                "created_at": f"{ymd_dash(d)}T{rng.randint(8, 23):02d}:{rng.randint(0, 59):02d}:00+09:00",
                "post_type": ptype,
                "visibility": rng.choice(["followers", "public", "challenge_group"]),
                "source": "derived_from_ledger",
                "title": title,
                "body": body,
                "metrics": {
                    "like_count": rng.randint(0, 80),
                    "comment_count": rng.randint(0, 14),
                    "save_count": rng.randint(0, 20),
                },
            }
        )
    reactions = []
    for i in range(rng.randint(3, 18)):
        reactions.append(
            {
                "reaction_id": f"{profile['persona_id']}-R{i + 1:03d}",
                "actor_persona_id": profile["persona_id"],
                "target_persona_id": rng.choice(follows) if follows else rng.choice(candidates),
                "reaction_type": rng.choice(["like", "cheer", "question", "bookmark"]),
                "created_at": f"2026-06-{rng.randint(1, 30):02d}T{rng.randint(8, 23):02d}:{rng.randint(0, 59):02d}:00+09:00",
            }
        )
    social_profile = {
        "persona_id": profile["persona_id"],
        "handle": handle,
        "privacy_level": rng.choice(["public_aggregated", "followers_only", "challenge_only"]),
        "sns_tendency": profile["sns_tendency"],
        "bio_tags": profile["lifestyle_tags"] + [profile["financial_goal"], profile["archetype"]],
        "follower_count_estimate": rng.randint(8, 650) if profile["sns_tendency"] != "눈팅형" else rng.randint(0, 60),
        "following_count": len(follows),
    }
    write_json(root / "social" / "profile_social.json", social_profile)
    write_json(root / "social" / "follows.json", {"persona_id": profile["persona_id"], "follows": follows})
    write_json(root / "social" / "feed.json", {"persona_id": profile["persona_id"], "posts": posts})
    write_json(root / "social" / "reactions.json", {"persona_id": profile["persona_id"], "reactions": reactions})
    bundle.social = {"profile": social_profile, "follows": follows, "posts": posts, "reactions": reactions}


def build_features(bundle: PersonaBundle) -> dict[str, Any]:
    rows = bundle.ledger_rows
    profile = bundle.profile
    income = sum(r["금액"] for r in rows if r["cashflow_bucket"] == "소득" and r["금액"] > 0)
    spend = sum(-r["금액"] for r in rows if r["cashflow_bucket"] == "소비" and r["금액"] < 0)
    saving = sum(-r["금액"] for r in rows if r["cashflow_bucket"] == "저축" and r["금액"] < 0)
    invest_buy = sum(-r["금액"] for r in rows if r["cashflow_bucket"] == "투자" and r["금액"] < 0)
    category_spend = Counter()
    weekend_spend = 0
    online_spend = 0
    subscription_count = 0
    for r in rows:
        if r["cashflow_bucket"] == "소비" and r["금액"] < 0:
            amt = -r["금액"]
            category_spend[r["대분류"]] += amt
            d = datetime.strptime(r["날짜"], "%Y-%m-%d").date()
            if d.weekday() >= 5:
                weekend_spend += amt
            if r["대분류"] == "온라인쇼핑":
                online_spend += amt
            if r["소분류"] == "서비스구독":
                subscription_count += 1
    social_posts = len(bundle.social.get("posts", []))
    return {
        "persona_id": profile["persona_id"],
        "archetype": profile["archetype"],
        "age": profile["age"],
        "monthly_income_krw": profile["monthly_income_krw"],
        "total_income_krw": income,
        "total_spend_krw": spend,
        "total_saving_krw": saving,
        "total_invest_buy_krw": invest_buy,
        "savings_rate": round(saving / income, 4) if income else 0,
        "investment_rate": round(invest_buy / income, 4) if income else 0,
        "spend_rate": round(spend / income, 4) if income else 0,
        "food_ratio": round(category_spend["식비"] / spend, 4) if spend else 0,
        "cafe_ratio": round(category_spend["카페/간식"] / spend, 4) if spend else 0,
        "transport_spend_krw": category_spend["교통"],
        "online_spend_ratio": round(online_spend / spend, 4) if spend else 0,
        "weekend_spend_ratio": round(weekend_spend / spend, 4) if spend else 0,
        "subscription_count": subscription_count,
        "risk_score": profile["risk_score"],
        "household_size": profile["household_size"],
        "transaction_count": len(rows),
        "portfolio_count": len(bundle.portfolio),
        "social_post_count": social_posts,
        "log_monthly_income_krw": round(math.log1p(profile["monthly_income_krw"]), 6),
        "log_total_spend_krw": round(math.log1p(spend), 6),
        "log_total_saving_krw": round(math.log1p(saving), 6),
        "log_total_invest_buy_krw": round(math.log1p(invest_buy), 6),
    }


def validate_counts(obj: Any, path: Path, errors: list[str]) -> None:
    if not isinstance(obj, dict):
        return
    pairs = {
        "account_cnt": "account_list",
        "card_cnt": "card_list",
        "trans_cnt": "trans_list",
        "approved_cnt": "approved_list",
        "purchase_cnt": "purchase_list",
        "pay_cnt": "pay_list",
        "prod_cnt": "prod_list",
        "basic_cnt": "basic_list",
    }
    for cnt_key, list_key in pairs.items():
        if cnt_key in obj:
            value = obj.get(list_key)
            if not isinstance(value, list):
                errors.append(f"{path}: {cnt_key} exists but {list_key} is not list")
            elif obj[cnt_key] != len(value):
                errors.append(f"{path}: {cnt_key}={obj[cnt_key]} but len({list_key})={len(value)}")


def contains_exact_value(obj: Any, needle: str) -> bool:
    if isinstance(obj, dict):
        return any(contains_exact_value(v, needle) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_exact_value(v, needle) for v in obj)
    return str(obj) == needle


def validate_dataset(bundles: list[PersonaBundle], features: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    bundle_root = OUTPUT_ROOT / "bundles"
    dirs = sorted(p.name for p in bundle_root.iterdir() if p.is_dir())
    if len(dirs) != 199:
        errors.append(f"Expected 199 bundle dirs, found {len(dirs)}")
    required_subdirs = ["api/common", "api/bank", "api/card", "api/efinance", "api/invest", "social"]
    for bundle in bundles:
        pid = bundle.profile["persona_id"]
        root = bundle_root / pid
        if not (root / "profile.json").exists():
            errors.append(f"{pid}: missing profile.json")
        if not (root / "ledger.csv").exists() or not (root / "ledger.xlsx").exists():
            errors.append(f"{pid}: missing ledger files")
        for subdir in required_subdirs:
            if not (root / subdir).exists():
                errors.append(f"{pid}: missing {subdir}")
        df = pd.read_csv(root / "ledger.csv")
        if len(df) < MIN_ROWS or len(df) > MAX_ROWS:
            errors.append(f"{pid}: ledger rows {len(df)} outside {MIN_ROWS}-{MAX_ROWS}")
        if list(df.columns) != LEDGER_COLUMNS:
            errors.append(f"{pid}: ledger columns mismatch")
        parsed_dates = pd.to_datetime(df["날짜"], errors="coerce")
        if parsed_dates.isna().any() or not ((parsed_dates.dt.year == 2026) & (parsed_dates.dt.month == 6)).all():
            errors.append(f"{pid}: invalid date outside 2026-06")
        if (df[df["타입"] == "지출"]["금액"] >= 0).any():
            errors.append(f"{pid}: 지출 contains non-negative amount")
        if (df[df["타입"] == "수입"]["금액"] <= 0).any():
            errors.append(f"{pid}: 수입 contains non-positive amount")
        for bucket in ["소득", "소비", "저축", "투자"]:
            if bucket not in set(df["cashflow_bucket"]):
                errors.append(f"{pid}: missing cashflow bucket {bucket}")
        if df["api_ref"].isna().any():
            errors.append(f"{pid}: ledger has empty api_ref")
        api_cache: dict[Path, Any] = {}
        for refs in df["api_ref"].dropna():
            for ref in str(refs).split(";"):
                file_part = ref.split("#")[0]
                target = root / "api" / file_part
                if not target.exists():
                    errors.append(f"{pid}: api_ref target missing {file_part}")
                    continue
                if "#" in ref:
                    ident = ref.split("#", 1)[1]
                    if target not in api_cache:
                        api_cache[target] = json.loads(target.read_text(encoding="utf-8"))
                    if not contains_exact_value(api_cache[target], ident):
                        errors.append(f"{pid}: api_ref id {ident} missing inside {file_part}")
        for jp in root.rglob("*.json"):
            try:
                data = json.loads(jp.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"{pid}: JSON parse failed {jp.name}: {exc}")
                continue
            validate_counts(data, jp, errors)
        invest_files = list((root / "api" / "invest").glob("금투-004-*.json"))
        if not invest_files:
            errors.append(f"{pid}: missing 금투-004 portfolio")
        else:
            data = json.loads(invest_files[0].read_text(encoding="utf-8"))
            if data.get("prod_cnt", 0) < 1:
                errors.append(f"{pid}: empty portfolio")
    if len(features) != 199:
        errors.append(f"Expected 199 feature rows, found {len(features)}")
    for col in ["monthly_income_krw", "total_spend_krw", "total_saving_krw", "total_invest_buy_krw", "risk_score"]:
        vals = [f[col] for f in features]
        if statistics.pstdev(vals) == 0:
            errors.append(f"Feature {col} has zero variance")
    return {
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors[:200],
        "warnings": warnings,
    }


def kmeans_cluster_report(features: list[dict[str, Any]], k: int = 6) -> dict[str, Any]:
    feature_cols = [
        "log_monthly_income_krw",
        "savings_rate",
        "investment_rate",
        "spend_rate",
        "risk_score",
    ]
    x = np.array([[float(f[c]) for c in feature_cols] for f in features], dtype=float)
    mu = x.mean(axis=0)
    sigma = x.std(axis=0)
    sigma[sigma == 0] = 1
    z = (x - mu) / sigma
    distance_matrix = np.linalg.norm(z[:, None, :] - z[None, :, :], axis=2)
    best: tuple[float, np.ndarray, int] | None = None
    for restart in range(500):
        rng = np.random.default_rng(SEED + restart)
        centers = z[rng.choice(len(z), size=k, replace=False)]
        labels = np.zeros(len(z), dtype=int)
        for _ in range(100):
            distances = np.linalg.norm(z[:, None, :] - centers[None, :, :], axis=2)
            new_labels = distances.argmin(axis=1)
            if np.array_equal(labels, new_labels):
                break
            labels = new_labels
            for i in range(k):
                if np.any(labels == i):
                    centers[i] = z[labels == i].mean(axis=0)
        cluster_sizes = Counter(labels.tolist())
        if min(cluster_sizes.values()) < 8:
            continue
        silhouettes = []
        for i in range(len(z)):
            same = labels == labels[i]
            if same.sum() <= 1:
                silhouettes.append(0.0)
                continue
            a = distance_matrix[i, same].sum() / (same.sum() - 1)
            b = min(distance_matrix[i, labels == c].mean() for c in range(k) if np.any(labels == c) and c != labels[i])
            silhouettes.append((b - a) / max(a, b) if max(a, b) else 0.0)
        score = float(np.mean(silhouettes))
        if best is None or score > best[0]:
            best = (score, labels.copy(), restart)
    if best is None:
        best = (0.0, np.zeros(len(z), dtype=int), -1)
    score, labels, best_restart = best
    cluster_sizes = Counter(labels.tolist())
    for f, label in zip(features, labels.tolist(), strict=True):
        f["cluster_id"] = int(label)
    return {
        "k": k,
        "feature_columns": feature_cols,
        "best_restart": best_restart,
        "silhouette_score": round(score, 4),
        "cluster_sizes": {str(k): v for k, v in sorted(cluster_sizes.items())},
        "min_cluster_size": min(cluster_sizes.values()),
        "passes_threshold": score >= 0.18 and min(cluster_sizes.values()) >= 8,
    }


def write_aggregates(bundles: list[PersonaBundle], manifests: list[dict[str, Any]], features: list[dict[str, Any]]) -> None:
    agg = OUTPUT_ROOT / "aggregates"
    agg.mkdir(parents=True, exist_ok=True)
    with (agg / "personas.jsonl").open("w", encoding="utf-8") as f:
        for b in bundles:
            f.write(json.dumps(b.profile, ensure_ascii=False) + "\n")
    all_rows = []
    for b in bundles:
        all_rows.extend(b.ledger_rows)
    pd.DataFrame(all_rows, columns=LEDGER_COLUMNS).to_csv(agg / "ledger_all.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(features).to_csv(agg / "feature_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(agg / "api_index.json", {"generated_at": datetime.now().isoformat(timespec="seconds"), "bundle_count": len(manifests), "bundles": manifests})
    social_edges = []
    reactions = []
    feed = []
    for b in bundles:
        for target in b.social.get("follows", []):
            social_edges.append({"source_persona_id": b.profile["persona_id"], "target_persona_id": target, "edge_type": "follow"})
        reactions.extend(b.social.get("reactions", []))
        feed.extend(b.social.get("posts", []))
    pd.DataFrame(social_edges).to_csv(agg / "social_edges.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(reactions).to_csv(agg / "social_reactions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(feed).to_csv(agg / "social_feed.csv", index=False, encoding="utf-8-sig")


def write_reports(bundles: list[PersonaBundle], features: list[dict[str, Any]], validation: dict[str, Any], cluster: dict[str, Any]) -> None:
    val_dir = OUTPUT_ROOT / "validation"
    val_dir.mkdir(parents=True, exist_ok=True)
    write_json(val_dir / "validation_report.json", validation)
    first10 = bundles[:10]
    lines = [
        "# First 10 Persona Review",
        "",
        "P001-P010은 10개 archetype을 각각 1명씩 직접 고정 배치한 기준 사례다.",
        "",
        "| persona_id | archetype | age | income | rows | savings_rate | investment_rate | portfolio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    feature_by_pid = {f["persona_id"]: f for f in features}
    for b in first10:
        f = feature_by_pid[b.profile["persona_id"]]
        lines.append(
            f"| {b.profile['persona_id']} | {b.profile['archetype']} | {b.profile['age']} | {b.profile['monthly_income_krw']:,} | {len(b.ledger_rows)} | {f['savings_rate']:.1%} | {f['investment_rate']:.1%} | {len(b.portfolio)} |"
        )
    lines.extend(
        [
            "",
            "## Criteria Review",
            "",
            "- 자산흐름: 모든 기준 사례에 소득, 소비, 저축, 투자 bucket과 API 참조가 존재한다.",
            "- 소비집계: 원본 엑셀의 대분류/소분류를 유지하고 확장했기 때문에 식비, 구독, 교통 등 집계가 가능하다.",
            "- 저축률: `total_saving_krw / total_income_krw`를 feature matrix에 기록한다.",
            "- 투자 포트폴리오: 모든 기준 사례에 금투-003 거래와 금투-004 보유 상품이 있다.",
            "- 개인 특성 복원: profile과 ledger-derived feature가 소득대, 지출대, 라이프스타일, 목표를 복원 가능하게 한다.",
            "- 군집화: 199명 전체 feature matrix와 numpy KMeans 리포트를 생성한다.",
        ]
    )
    (val_dir / "first10_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    cluster_lines = [
        "# Cluster Readiness Report",
        "",
        f"- k: {cluster['k']}",
        f"- silhouette_score: {cluster['silhouette_score']}",
        f"- min_cluster_size: {cluster['min_cluster_size']}",
        f"- passes_threshold: {cluster['passes_threshold']}",
        f"- cluster_sizes: {cluster['cluster_sizes']}",
        "",
        "## Feature Columns",
        "",
    ]
    cluster_lines.extend(f"- `{c}`" for c in cluster["feature_columns"])
    (val_dir / "cluster_readiness_report.md").write_text("\n".join(cluster_lines) + "\n", encoding="utf-8")

    drift_lines = [
        "# Schema Drift Report",
        "",
        "생성 JSON은 `inputs/source_api_json`의 top-level 응답 관례를 우선 따른다.",
        "",
        "| API group | compatibility policy | notes |",
        "|---|---|---|",
        "| common | source-compatible | 정보제공-공통-002 필드 유지 |",
        "| bank | source-compatible | 은행-001/004의 count/list 필드 및 거래 필드 유지 |",
        "| card | source-compatible | 카드-008/014는 승인/매입 중복 계층으로 생성 |",
        "| efinance | source-compatible | source_api_json의 전금-001 account_list 관례 유지 |",
        "| invest | response-schema-plus-example | 금투-001/002/003/004는 response_schemas와 minji 예시 기반 확장 |",
        "",
        f"- source API reference path: `{SOURCE_API_DIR}`",
        f"- response schema reference path: `{RESPONSE_SCHEMA_DIR}`",
        "- 공개 배포본에는 원본 입력 파일을 포함하지 않고, 생성 산출물과 재현 스크립트만 포함한다.",
    ]
    (val_dir / "schema_drift_report.md").write_text("\n".join(drift_lines) + "\n", encoding="utf-8")


def write_root_readme(bundles: list[PersonaBundle], validation: dict[str, Any], cluster: dict[str, Any]) -> None:
    readme = [
        "# Financial SNS MyData Synthetic Dataset 2026-06",
        "",
        "대한민국 청년 만 19~34세 199명의 합성 금융 활동 데이터셋이다.",
        "",
        "## Contents",
        "",
        "- `bundles/P001..P199/`: 개인별 profile, ledger, MyData API JSON, social companion data",
        "- `aggregates/personas.jsonl`: 전체 페르소나",
        "- `aggregates/ledger_all.csv`: 전체 가계부 통합본",
        "- `aggregates/feature_matrix.csv`: 군집화와 특성 복원용 feature",
        "- `aggregates/social_edges.csv`: 금융 SNS 팔로우 관계",
        "- `validation/`: 첫 10건 리뷰, 검증 리포트, 군집화 준비성, 스키마 차이",
        "",
        "## Generation Rules",
        "",
        f"- seed: `{SEED}`",
        "- month: `2026-06-01` to `2026-06-30`",
        "- ledger columns: original 10 columns plus persona/API tracing fields",
        "- API scope: common, bank, card, efinance, invest",
        "- all data is synthetic and must not be treated as real personal financial data",
        "",
        "## Validation Summary",
        "",
        f"- validation status: `{validation['status']}`",
        f"- error_count: `{validation['error_count']}`",
        f"- cluster silhouette score: `{cluster['silhouette_score']}`",
        f"- min cluster size: `{cluster['min_cluster_size']}`",
    ]
    (OUTPUT_ROOT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")


def copy_reference_manifest() -> None:
    references = OUTPUT_ROOT / "references"
    references.mkdir(parents=True, exist_ok=True)
    manifest = {
        "input_files": {
            "source_xlsx": str(SOURCE_XLSX_PATH),
            "source_api_json_dir": str(SOURCE_API_DIR),
            "response_schemas_dir": str(RESPONSE_SCHEMA_DIR),
            "minji_demo_dir": str(MINJI_DEMO_DIR),
        },
        "notes": [
            "입력 파일은 형식과 분포 참고용이며 실제 거래를 복사하지 않는다.",
            "생성 결과는 deterministic seed 기반 합성 데이터다.",
        ],
    }
    write_json(references / "input_manifest.json", manifest)


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    copy_reference_manifest()
    archetypes = persona_distribution()
    bundles = [generate_persona(i + 1, arch) for i, arch in enumerate(archetypes)]
    all_persona_ids = [b.profile["persona_id"] for b in bundles]
    manifests = [write_bundle(b, all_persona_ids) for b in bundles]
    features = [build_features(b) for b in bundles]
    cluster = kmeans_cluster_report(features, k=6)
    # Re-write features after cluster labels are added.
    write_aggregates(bundles, manifests, features)
    validation = validate_dataset(bundles, features)
    validation["cluster"] = cluster
    if not cluster["passes_threshold"]:
        validation["status"] = "FAIL"
        validation["error_count"] += 1
        validation["errors"].append("Cluster readiness threshold failed")
    write_reports(bundles, features, validation, cluster)
    write_root_readme(bundles, validation, cluster)
    print(json.dumps({"output_root": str(OUTPUT_ROOT), "bundle_count": len(bundles), "validation": validation["status"], "errors": validation["error_count"], "cluster": cluster}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
