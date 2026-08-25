# Changelog

## 1.1.0 — Robust input and date handling

- Fixed the `Timestamp` versus `datetime.date` subtraction error in candidate freshness scoring.
- Normalized all CSV date fields to pandas `Timestamp` values before comparisons.
- Added safe date parsing for malformed, blank, and missing dates.
- Added robust Yes/No, True/False, and 1/0 normalization for operational boolean fields.
- Added defensive numeric parsing and sensible neutral defaults for missing operational values.
- Added CSV decoding and empty-file validation with user-facing error messages.
- Added conservative handling for missing freshness and availability dates instead of crashing.
- Preserved 100% local processing and human-in-the-loop review behavior.
