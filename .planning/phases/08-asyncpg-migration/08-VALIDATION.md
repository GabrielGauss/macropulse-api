# Phase 8 Validation: Async Database Migration

**Phase:** 08-asyncpg-migration
**Requirements:** DB-10, DB-11, DB-12, DB-13

Run all checks from the project root:
```
cd c:/Users/gabri/OneDrive/Documentos/code/claude/macropulse
```

---

## DB-10: No psycopg2 in production paths

```bash
# Must return 0 matches (psycopg2 removed everywhere except comments/docs)
grep -rn "import psycopg2\|from psycopg2" database/ api/ config/ services/ && echo "FAIL: psycopg2 still imported" || echo "PASS DB-10"

# asyncpg must be present in requirements.txt
grep "asyncpg" requirements.txt && echo "PASS: asyncpg in requirements" || echo "FAIL: asyncpg missing"

# psycopg2-binary must be absent from requirements.txt
grep "psycopg2" requirements.txt && echo "FAIL: psycopg2 still in requirements" || echo "PASS: psycopg2 removed"
```

Expected: 0 psycopg2 imports, asyncpg present, psycopg2-binary absent.

---

## DB-11: Async context managers throughout

```bash
# No get_sync_cursor anywhere in the codebase
grep -rn "get_sync_cursor" database/ api/ tests/ && echo "FAIL: get_sync_cursor found" || echo "PASS DB-11a"

# All functions in queries.py are async def (should return 0 sync funcs)
python -c "
import ast
src = open('database/queries.py').read()
tree = ast.parse(src)
sync_defs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
if sync_defs:
    print('FAIL DB-11b: sync functions found:', sync_defs)
else:
    print('PASS DB-11b: all query functions are async def')
"

# get_db_conn used as async context manager in queries.py
grep -c "async with get_db_conn" database/queries.py && echo "PASS DB-11c: get_db_conn used" || echo "FAIL DB-11c: get_db_conn missing"

# Auth route handlers are async def
python -c "
import ast
src = open('api/routes/auth.py').read()
tree = ast.parse(src)
handlers = ['register', 'verify', 'recover', 'recover_verify', 'rotate_key', 'get_me', 'get_usage']
async_defs = {n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)}
missing = [h for h in handlers if h not in async_defs]
if missing:
    print('FAIL DB-11d: sync handlers:', missing)
else:
    print('PASS DB-11d: all auth handlers are async def')
"
```

---

## DB-12: Pool tuning (min_size=5, max_size=20, command_timeout=30)

```bash
# Check pool constants in connection.py
python -c "
import re
src = open('database/connection.py').read()
# Check defaults
min_match = re.search(r'_POOL_MIN\s*=\s*int\(os\.getenv\(.+?,\s*[\"'\''](\d+)[\"'\'']\)', src)
max_match = re.search(r'_POOL_MAX\s*=\s*int\(os\.getenv\(.+?,\s*[\"'\''](\d+)[\"'\'']\)', src)
timeout_match = re.search(r'_CMD_TIMEOUT\s*=\s*(\d+)', src)
min_val = min_match.group(1) if min_match else 'NOT FOUND'
max_val = max_match.group(1) if max_match else 'NOT FOUND'
timeout_val = timeout_match.group(1) if timeout_match else 'NOT FOUND'
print(f'min_size default: {min_val} (expect 5)')
print(f'max_size default: {max_val} (expect 20)')
print(f'command_timeout: {timeout_val} (expect 30)')
assert min_val == '5', 'FAIL DB-12: wrong min_size default'
assert max_val == '20', 'FAIL DB-12: wrong max_size default'
assert timeout_val == '30', 'FAIL DB-12: wrong command_timeout'
print('PASS DB-12: pool tuning correct')
"

# Verify env var override works (DB_POOL_MIN, DB_POOL_MAX in create_pool args)
grep "DB_POOL_MIN\|DB_POOL_MAX" database/connection.py && echo "PASS: env var overrides present" || echo "FAIL: no env var overrides"

# asyncpg.create_pool called with all three params
python -c "
src = open('database/connection.py').read()
checks = ['min_size', 'max_size', 'command_timeout']
for c in checks:
    if c not in src:
        print(f'FAIL DB-12: {c} not passed to create_pool')
    else:
        print(f'PASS: {c} present')
"
```

---

## DB-13: Tests updated for async

```bash
# pytest.ini has asyncio_mode = auto
grep "asyncio_mode" pytest.ini && echo "PASS DB-13a" || echo "FAIL DB-13a: asyncio_mode missing"

# pytest-asyncio in requirements
grep "pytest-asyncio" requirements.txt && echo "PASS DB-13b" || echo "FAIL DB-13b: pytest-asyncio missing"

# conftest.py uses AsyncMock (not MagicMock sync context manager for DB)
grep "AsyncMock" tests/conftest.py && echo "PASS DB-13c" || echo "FAIL DB-13c: AsyncMock missing in conftest"

# test_auth_rate_limit.py patches get_db_conn, not get_sync_cursor
grep "get_db_conn" tests/test_auth_rate_limit.py && echo "PASS DB-13d" || echo "FAIL DB-13d: still uses get_sync_cursor"

# Full test suite passes
python -m pytest tests/ -q 2>&1 | tail -5
```

---

## End-to-End: Full Suite

```bash
# Install updated requirements first (if not already done)
pip install "asyncpg>=0.29,<1.0" "pytest-asyncio>=0.23,<1.0"

# Run all tests
python -m pytest tests/ -v 2>&1 | tail -30
```

Expected: All tests pass. 0 failures, 0 errors.

---

## Smoke: App Start

```bash
# App must import cleanly (no missing async awaits at import time)
python -c "from api.main import app; print('PASS: app imports OK')"
```

---

## Summary Checklist

| Requirement | Check | Pass/Fail |
|-------------|-------|-----------|
| DB-10 | No psycopg2 import in database/ or api/ | [ ] |
| DB-10 | asyncpg in requirements.txt | [ ] |
| DB-10 | psycopg2-binary removed from requirements.txt | [ ] |
| DB-11 | No get_sync_cursor anywhere | [ ] |
| DB-11 | All queries.py functions are async def | [ ] |
| DB-11 | All auth route handlers are async def | [ ] |
| DB-11 | check_auth_rate_limit is async def | [ ] |
| DB-11 | _resolve_limit is async def | [ ] |
| DB-12 | min_size=5 (or DB_POOL_MIN env override) | [ ] |
| DB-12 | max_size=20 (or DB_POOL_MAX env override) | [ ] |
| DB-12 | command_timeout=30 | [ ] |
| DB-13 | asyncio_mode = auto in pytest.ini | [ ] |
| DB-13 | pytest-asyncio in requirements.txt | [ ] |
| DB-13 | conftest.py uses AsyncMock for DB fixture | [ ] |
| DB-13 | test_auth_rate_limit.py patches get_db_conn | [ ] |
| DB-13 | pytest exits 0, no regressions | [ ] |
