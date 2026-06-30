# 금융 SNS 서비스 설계용 합성 데이터셋

금융 SNS 서비스 설계를 위해 만든 199명 규모의 합성 금융 활동 데이터셋입니다.

2026년 6월 한 달 동안 대한민국 청년 만 19~34세가 벌고, 쓰고, 저축하고, 투자하는 흐름을 페르소나 단위로 구성했습니다. MyData API 응답 형식을 참고한 금융 데이터와, 금융 SNS 앱 기능을 검증하기 위한 앱 기능 데이터를 함께 제공합니다.

```text
outputs/financial_sns_mydata_202606/
```

## 데이터셋 개요

이 데이터셋은 하나핀크 리얼리, 뱅크샐러드, 인스타그램의 성격을 결합한 금융 SNS 서비스를 가정합니다.

- 리얼리: 인증된 금융 활동을 기반으로 한 금융 피드
- 뱅크샐러드: 자산, 소비, 가계부 분석
- 인스타그램: 팔로우, 피드, 반응 중심의 소셜 경험

목표는 단순 거래 내역이 아니라, 서비스 설계와 기능 검증에 바로 사용할 수 있는 샘플 데이터를 확보하는 것입니다.

## 구성

각 페르소나는 하나의 번들로 관리됩니다.

```text
outputs/financial_sns_mydata_202606/
  bundles/P001..P199/      # 개인별 데이터 번들
  aggregates/              # 전체 통합 CSV/JSON
  validation/              # 검증 결과
  references/              # 입력 기준 요약
```

개인별 번들에는 다음 파일이 들어 있습니다.

- `profile.json`: 나이, 직업, 소득대, 지출대, 가구 형태, 소비 성향, 금융 목표
- `ledger.csv`, `ledger.xlsx`: 2026년 6월 소득, 소비, 저축, 투자 내역
- `api/`: 은행, 카드, 전금, 금투, 공통 영역의 MyData 유사 JSON 응답
- `social/`: 금융 SNS 앱의 익명 프로필, 팔로우, 피드, 반응 데이터
- `manifest.json`: 번들 구성과 참조 관계를 정리한 인덱스

## SNS 데이터의 의미

`social/`은 MyData API 응답이 아닙니다.

이 영역은 금융 SNS 앱 안에서 만들어지는 기능 데이터입니다. 예를 들어 저축 목표 달성 피드, 투자 기록 공유, 소비 패턴 공유, 팔로우 관계, 좋아요와 댓글 같은 기능을 검증하기 위해 추가했습니다.

데이터의 역할은 다음처럼 나뉩니다.

- `api/`: 금융기관 조회 결과를 모사한 원천 데이터
- `ledger.csv`: 금융 흐름 분석을 위한 정규화 가계부
- `profile.json`: 사용자의 배경과 금융 성향을 설명하는 페르소나
- `social/`: 앱 내부 SNS 기능을 검증하기 위한 앱 기능 데이터

따라서 SNS 데이터는 원천 금융 데이터가 아니라, 금융 데이터를 활용하는 앱 기능 검증용 데이터로 봐야 합니다.

## 먼저 볼 파일

- 개인 예시: `outputs/financial_sns_mydata_202606/bundles/P001/`
- 전체 페르소나: `outputs/financial_sns_mydata_202606/aggregates/personas.jsonl`
- 전체 가계부: `outputs/financial_sns_mydata_202606/aggregates/ledger_all.csv`
- 분석 피처: `outputs/financial_sns_mydata_202606/aggregates/feature_matrix.csv`
- SNS 팔로우: `outputs/financial_sns_mydata_202606/aggregates/social_edges.csv`
- SNS 피드: `outputs/financial_sns_mydata_202606/aggregates/social_feed.csv`
- 검증 결과: `outputs/financial_sns_mydata_202606/validation/validation_report.json`
- 생성 스크립트: `work/generate_financial_sns_dataset.py`

## 활용 가능한 분석

이 데이터셋으로 다음 항목을 확인할 수 있습니다.

- 개인별 월간 자산 흐름 추적
- 소비 카테고리별 집계
- 소득 대비 저축률 계산
- 주식 매수와 보유 포트폴리오 집계
- 거래 내역 기반 페르소나 특성 유추
- 전체 사용자 군집화
- 금융 SNS 피드, 팔로우, 반응 기능 검증

## 검증 결과

- 검증 상태: `PASS`
- 페르소나 수: `199`
- 검증 에러 수: `0`
- 군집화 silhouette 유사 점수: `0.2893`
- 최소 군집 크기: `8`

## 주의사항

이 레포지토리의 데이터는 모두 합성 데이터입니다. 실제 개인정보나 실제 금융 거래 내역을 포함하지 않습니다.

원본 엑셀과 API 예시 파일은 형식 참고용으로만 사용했으며, 공개 레포지토리에는 포함하지 않았습니다.
