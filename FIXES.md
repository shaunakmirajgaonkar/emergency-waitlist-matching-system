# Stability Fixes

This release hardens QueueMatch Local against common CSV-quality problems.

### Fixed date arithmetic
All date arithmetic now uses normalized pandas `Timestamp` values. The previous expression mixed a pandas `Timestamp` with a Python `datetime.date`, which caused:

`TypeError: unsupported operand type(s) for -: 'Timestamp' and 'datetime.date'`

### Defensive CSV handling
The application now:

- strips column-name whitespace;
- rejects empty CSV files with a readable message;
- attempts UTF-8 first and Latin-1 as a fallback;
- parses dates with `errors="coerce"`;
- handles missing or invalid dates without terminating the dashboard;
- normalizes common boolean text such as `Yes`, `No`, `True`, and `False`;
- applies neutral operational defaults for missing numeric values;
- keeps matching logic deterministic and local.
