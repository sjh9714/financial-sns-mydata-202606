# Financial SNS MyData Synthetic Dataset 2026-06

This public repository contains a synthetic dataset for designing and testing a financial SNS product that combines MyData-style personal finance records, portfolio data, and lightweight social interactions.

The full generated dataset is in:

- `outputs/financial_sns_mydata_202606/`

## What Is Included

- 199 synthetic Korean youth personas, ages 19-34
- June 2026 ledger data for each persona
- MyData-like JSON responses for common, bank, card, efinance, and investment APIs
- SNS companion data: social profiles, follow edges, finance-derived feed posts, and reactions
- Aggregated analysis tables for personas, ledgers, feature vectors, feeds, follows, and reactions
- Validation reports showing the dataset passes structure, API-reference, and clustering-readiness checks

## Quick Entry Points

- Dataset README: `outputs/financial_sns_mydata_202606/README.md`
- All ledgers: `outputs/financial_sns_mydata_202606/aggregates/ledger_all.csv`
- Feature matrix: `outputs/financial_sns_mydata_202606/aggregates/feature_matrix.csv`
- Validation report: `outputs/financial_sns_mydata_202606/validation/validation_report.json`
- First 10 review: `outputs/financial_sns_mydata_202606/validation/first10_review.md`
- Generator script: `work/generate_financial_sns_dataset.py`

## Notes

All data is synthetic. It should not be interpreted as real personal financial data.

The original local input files used for format reference are not included in this public repository.
