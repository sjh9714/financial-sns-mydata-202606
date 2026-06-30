# Schema Drift Report

생성 JSON은 `inputs/source_api_json`의 top-level 응답 관례를 우선 따른다.

| API group | compatibility policy | notes |
|---|---|---|
| common | source-compatible | 정보제공-공통-002 필드 유지 |
| bank | source-compatible | 은행-001/004의 count/list 필드 및 거래 필드 유지 |
| card | source-compatible | 카드-008/014는 승인/매입 중복 계층으로 생성 |
| efinance | source-compatible | source_api_json의 전금-001 account_list 관례 유지 |
| invest | response-schema-plus-example | 금투-001/002/003/004는 response_schemas와 minji 예시 기반 확장 |

- source API reference path: `inputs/source_api_json`
- response schema reference path: `inputs/response_schemas`
- 공개 배포본에는 원본 입력 파일을 포함하지 않고, 생성 산출물과 재현 스크립트만 포함한다.
