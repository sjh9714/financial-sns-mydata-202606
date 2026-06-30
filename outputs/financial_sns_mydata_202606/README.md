# Financial SNS MyData Synthetic Dataset 2026-06

대한민국 청년 만 19~34세 199명의 합성 금융 활동 데이터셋이다.

## Contents

- `bundles/P001..P199/`: 개인별 profile, ledger, MyData API JSON, social companion data
- `aggregates/personas.jsonl`: 전체 페르소나
- `aggregates/ledger_all.csv`: 전체 가계부 통합본
- `aggregates/feature_matrix.csv`: 군집화와 특성 복원용 feature
- `aggregates/social_edges.csv`: 금융 SNS 팔로우 관계
- `validation/`: 첫 10건 리뷰, 검증 리포트, 군집화 준비성, 스키마 차이

## Generation Rules

- seed: `20260630`
- month: `2026-06-01` to `2026-06-30`
- ledger columns: original 10 columns plus persona/API tracing fields
- API scope: common, bank, card, efinance, invest
- all data is synthetic and must not be treated as real personal financial data

## Validation Summary

- validation status: `PASS`
- error_count: `0`
- cluster silhouette score: `0.2893`
- min cluster size: `8`
