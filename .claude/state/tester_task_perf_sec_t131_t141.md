# TESTER TASK: Performance & Security Tests T131-T141
Session: tutor_cabinet_test_20260107

## OBJECTIVE
Write & run 11 comprehensive test suites for:
- T131-T135: Performance tests
- T136-T141: Security tests

## REQUIREMENTS
1. One test file per test (T131-T141)
2. Clear test naming: test_{function}_{scenario}
3. No mocking unless necessary
4. No documentation in tests
5. Unit + integration tests

## PERFORMANCE TESTS

### T131: Dashboard Load Time <2s
```python
test_dashboard_loads_under_2_seconds
test_dashboard_response_structure
test_dashboard_handles_large_datasets
test_dashboard_caches_correctly
test_dashboard_timeout_handling
```

### T132: List 1000 Students No Lag
```python
test_list_students_pagination
test_list_1000_students_memory
test_list_students_sorting
test_list_students_filtering_performance
test_list_students_concurrent_requests
```

### T133: Full-Text Search Performance
```python
test_search_under_500ms
test_search_10k_documents
test_search_query_optimization
test_search_result_relevance
test_search_empty_query
```

### T134: API Response Time <500ms
```python
test_api_response_time_p95_under_500ms
test_api_response_time_all_endpoints
test_api_response_statistics (min/max/mean/median)
test_api_concurrent_requests
test_api_rate_limiting
```

### T135: No Memory Leaks
```python
test_memory_growth_after_requests
test_memory_cleanup_on_disconnect
test_memory_with_large_payloads
test_memory_concurrent_connections
test_memory_sustained_load
```

## SECURITY TESTS

### T136: SQL Injection Protection
```python
test_sql_injection_in_search
test_sql_injection_in_login
test_sql_injection_in_filter
test_sql_injection_drop_table
test_sql_injection_union_based
test_sql_injection_time_based
```

### T137: XSS Protection
```python
test_xss_in_comment_body
test_xss_in_comment_title
test_xss_in_user_profile
test_xss_script_tag
test_xss_img_onerror
test_xss_event_handler
```

### T138: CSRF Token Protection
```python
test_csrf_token_in_form
test_csrf_post_without_token
test_csrf_put_without_token
test_csrf_delete_without_token
test_csrf_token_validation
```

### T139: Authorization Header Validation
```python
test_invalid_token_rejected
test_expired_token_rejected
test_malformed_header_rejected
test_missing_bearer_prefix
test_token_refresh_flow
test_token_expiration_validation
```

### T140: No Private Data Leakage
```python
test_password_not_in_response
test_api_key_not_in_response
test_private_key_not_in_response
test_student_cannot_see_other_students
test_parent_cannot_see_other_parents
test_tutor_data_isolation
test_no_sensitive_fields_in_list_endpoints
```

### T141: Password Hashing (PBKDF2)
```python
test_password_hashed_pbkdf2
test_password_unique_salt
test_password_not_plaintext
test_password_hash_consistency
test_password_migration_security
```

## EXECUTION PLAN
1. Create test_performance_t131_t135.py (all perf tests)
2. Create test_security_t136_t141.py (all security tests)
3. Run: pytest test_performance_t131_t135.py -v
4. Run: pytest test_security_t136_t141.py -v
5. Generate results JSON
6. Report findings

## OUTPUT FORMAT
- TESTS: {passed}/{total} passed → {test_file}
- If failures: HANDOFF:coder:{file}:{issue}
- If all pass: DONE
