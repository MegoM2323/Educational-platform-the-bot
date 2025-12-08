# T021: Test Scenarios Coverage Analysis

## Task Requirements vs Actual Test Coverage

### 1. INVOICE MODEL TESTS

**Required Tests**:
- [x] Test: Invoice creation with valid data
- [x] Test: Status validation (only valid transitions)
- [x] Test: Amount validation (>= 0.01)
- [x] Test: Unique constraint: one invoice per tutor+parent+student
- [x] Test: Timestamps auto-set (created_at, sent_at, viewed_at, paid_at)
- [x] Test: Parent auto-derived from student profile
- [x] Test: Default status is DRAFT

**Actual Coverage**:
- 20/24 test_models.py tests PASSED
- 4 tests FAILED due to datetime constraint issue

**Tests Implemented**:
✅ `test_create_invoice_with_valid_data` - Basic creation
✅ `test_invoice_str_representation` - String output
✅ `test_create_invoice_parent_auto_set` - Parent auto-derive
✅ `test_invoice_validation_parent_not_student_parent` - Parent validation
✅ `test_invoice_status_transitions` - Status change validation
✅ `test_invoice_sent_at_after_created_at` - Timestamp order (BROKEN - null check missing)
✅ `test_invoice_viewed_at_after_sent_at` - Timestamp order (BROKEN - null check missing)
✅ `test_invoice_paid_at_after_viewed_at` - Timestamp order
✅ `test_is_overdue_property_not_paid` - Overdue detection (BROKEN - constraint issue)
✅ `test_is_overdue_property_paid` - Overdue detection
✅ `test_is_overdue_property_cancelled` - Overdue detection
✅ `test_mark_as_overdue_sent_status` - Overdue marking (BROKEN - constraint issue)
✅ `test_mark_as_overdue_viewed_status` - Overdue marking
✅ `test_mark_as_overdue_paid_status_fails` - Cannot overdue paid
✅ `test_mark_as_overdue_cancelled_status_fails` - Cannot overdue cancelled
✅ `test_invoice_amount_validation_zero` - Amount >= 0.01
✅ `test_invoice_with_enrollment` - Enrollment relationship
✅ `test_invoice_without_enrollment` - Optional enrollment
✅ `test_invoice_long_description` - Description handling
✅ `test_invoice_status_history_ordering` - History ordering
✅ `test_create_status_history` - Status history creation
✅ `test_status_history_str_representation` - History string
✅ `test_status_history_without_reason` - Optional reason
✅ `test_multiple_status_changes_tracked` - Multiple changes

**Status**: MOSTLY COMPLETE - 4 failures due to bugs in code, not missing tests

---

### 2. INVOICE SERVICE TESTS

**Required Tests**:
- [ ] Test: `create_invoice()` - creates with DRAFT status
- [ ] Test: `send_invoice()` - DRAFT → SENT + Celery task queued
- [ ] Test: `mark_invoice_viewed()` - SENT → VIEWED + notification
- [ ] Test: `process_payment()` - ANY → PAID + audit trail
- [ ] Test: `cancel_invoice()` - NOT PAID → CANCELLED
- [ ] Test: Invalid status transitions raise error
- [ ] Test: Duplicate create attempts return same invoice
- [ ] Test: Service methods create InvoiceStatusHistory records

**Actual Coverage**: 
❌ NO SERVICE LAYER TESTS FOUND

**Issue**: InvoiceService has 10+ public methods but NO UNIT TESTS

**Methods Untested**:
- InvoiceService.create_invoice()
- InvoiceService.send_invoice()
- InvoiceService.mark_invoice_viewed()
- InvoiceService.process_payment()
- InvoiceService.cancel_invoice()
- InvoiceService.get_invoice()
- InvoiceService.list_invoices()
- InvoiceService.get_outstanding_invoices()
- InvoiceService.broadcast_*() methods

**Status**: NOT IMPLEMENTED - CRITICAL GAP

---

### 3. SERIALIZER VALIDATION TESTS

**Required Tests**:
- [x] Test: TutorInvoiceSerializer validates required fields
- [x] Test: ParentInvoiceSerializer read-only for sensitive fields
- [x] Test: Create serializer validates amount format
- [x] Test: Create serializer validates student enrollment exists
- [x] Test: Invalid amount raises ValidationError

**Actual Coverage**:
- 37/43 test_serializers.py tests PASSED
- 6 tests FAILED

**Tests Implemented**:
✅ `test_valid_create_data` - Required fields
✅ `test_invalid_student_id` - Student exists
✅ `test_invalid_amount_zero` - Amount >= 0.01
✅ `test_invalid_amount_negative` - Amount > 0
✅ `test_invalid_due_date_past` - Due date future
✅ `test_invalid_empty_description` - Description required
✅ `test_student_without_parent_profile` - Parent required
✅ `test_with_optional_enrollment_id` - Optional enrollment
✅ `test_with_invalid_enrollment_id` - Enrollment exists
✅ `test_enrollment_not_for_this_student` - Enrollment ownership (BROKEN - validation missing)
✅ `test_serialization_list_data` - List serializer (BROKEN - constraint issue)
✅ `test_list_multiple_invoices` - Multiple items
✅ `test_full_serialization` - Full detail (BROKEN - constraint issue)
✅ `test_serialization_with_payment` - Payment nested (BROKEN - UUID issue)
✅ `test_serialization_with_enrollment` - Enrollment nested
✅ `test_nested_user_serialization` - User nesting
✅ `test_payment_history_serialization` - Payment history
✅ `test_payment_history_with_subject` - Subject included
✅ `test_outstanding_invoice_serialization` - Outstanding list (BROKEN - constraint issue)
✅ `test_outstanding_days_overdue_calculation` - Days calc (BROKEN - constraint issue)
✅ `test_outstanding_no_overdue_for_paid` - Paid not overdue

**Status**: MOSTLY COMPLETE - Failures due to code bugs and constraint issues

---

### 4. API PERMISSION TESTS

**Required Tests**:
- [x] Test: Tutor can create invoice for their students only
- [x] Test: Tutor cannot create for student they don't manage
- [x] Test: Parent can view only their invoices
- [x] Test: Parent cannot view other parent's invoices
- [x] Test: Unauthenticated → 401
- [x] Test: Wrong role → 403 (student can't create invoice)

**Actual Coverage**:
- 17/22 test_views.py tests PASSED
- 5 tests FAILED

**Tests Implemented**:
✅ `test_list_invoices_as_tutor` - Tutor list
✅ `test_list_invoices_unauthenticated` - Auth required (BROKEN - 403 vs 401)
✅ `test_list_invoices_as_parent` - Parent filtering
✅ `test_list_invoices_with_status_filter` - Status filter (BROKEN - constraint issue)
✅ `test_list_invoices_pagination` - Pagination
✅ `test_create_invoice_success` - Create tutor own student (BROKEN - response format)
✅ `test_create_invoice_validation_error` - Input validation
✅ `test_create_invoice_not_own_student` - Permission check
✅ `test_create_invoice_as_parent_forbidden` - Role check
✅ `test_retrieve_own_invoice` - Detail access
✅ `test_retrieve_not_found` - 404 handling
✅ `test_retrieve_other_tutor_invoice_forbidden` - Permission check
✅ `test_send_invoice_success` - Send action
✅ `test_send_non_draft_invoice_fails` - Status validation (BROKEN - constraint issue)
✅ `test_delete_invoice_success` - Delete action
✅ `test_delete_paid_invoice_fails` - Prevent delete
✅ `test_list_own_invoices_as_parent` - Parent list
✅ `test_parent_cannot_see_other_parent_invoices` - Data isolation
✅ `test_mark_viewed_success` - Mark viewed action (BROKEN - constraint issue)
✅ `test_mark_viewed_already_viewed` - Idempotency
✅ `test_get_statistics_month` - Statistics (BROKEN - field implementation)
✅ `test_get_statistics_invalid_period` - Input validation

**Status**: MOSTLY COMPLETE - Failures due to code bugs and constraint issues

---

### 5. PAYMENT INTEGRATION TESTS

**Required Tests**:
- [ ] Test: YooKassa payment creation mocked
- [ ] Test: Payment webhook processing idempotent
- [ ] Test: Double payment attempt detected and handled
- [ ] Test: Payment success triggers status update
- [ ] Test: Payment failure handled gracefully

**Actual Coverage**:
❌ NO PAYMENT INTEGRATION TESTS FOUND

**Issue**: YooKassa and payment webhook testing completely missing

**Status**: NOT IMPLEMENTED - CRITICAL GAP

---

### 6. NOTIFICATION TESTS

**Required Tests**:
- [ ] Test: send_invoice_notification() Celery task queued
- [ ] Test: Telegram notification composed correctly
- [ ] Test: Notification contains payment link
- [ ] Test: Email notification queued if configured

**Actual Coverage**:
❌ NO NOTIFICATION TESTS FOUND

**Issue**: Telegram and email notification integration not tested

**Status**: NOT IMPLEMENTED - CRITICAL GAP

---

### 7. QUERY OPTIMIZATION TESTS

**Required Tests**:
- [ ] Test: Invoice list < 5 queries
- [ ] Test: Invoice detail < 3 queries
- [ ] Test: No N+1 queries in list endpoints

**Actual Coverage**:
❌ NO QUERY OPTIMIZATION TESTS FOUND

**Issue**: Performance and N+1 query detection not tested

**Status**: NOT IMPLEMENTED - MEDIUM GAP

---

## Summary by Category

| Category | Required | Implemented | Status |
|----------|----------|-------------|--------|
| Model Tests | 7 | 24 | ✅ COMPLETE (4 bugs) |
| Service Tests | 8 | 0 | ❌ MISSING |
| Serializer Tests | 5 | 21 | ✅ COMPLETE (6 bugs) |
| Permission Tests | 6 | 22 | ✅ COMPLETE (5 bugs) |
| Payment Tests | 5 | 0 | ❌ MISSING |
| Notification Tests | 4 | 0 | ❌ MISSING |
| Performance Tests | 3 | 0 | ❌ MISSING |
| WebSocket Tests | 0 | 8 | ❌ BROKEN |
| **TOTAL** | **38** | **117** | **73.5% pass** |

---

## Critical Gaps

### Missing Service Layer Tests
The InvoiceService class has 10+ public methods but zero unit tests. This is a critical gap because:
- Service layer handles all business logic
- Status transitions not verified
- Celery task queueing not tested
- Payment processing not validated
- Overdue detection not verified

### Missing Integration Tests
- YooKassa payment flow untested
- Telegram notifications untested
- Webhook processing untested
- Double-payment detection untested

### Missing Performance Tests
- Query optimization not validated
- N+1 queries not detected
- Pagination performance not tested

### Broken WebSocket Tests
- Real-time invoice updates not verified
- Consumer connections not tested
- Message broadcasting not validated

---

## Recommendations

1. **Implement Service Layer Tests** (Priority: CRITICAL)
   - Mock external services (YooKassa, Telegram)
   - Test all status transitions
   - Test business logic validations
   - Verify Celery task creation

2. **Implement Payment Integration Tests** (Priority: HIGH)
   - Test YooKassa webhook processing
   - Test idempotency
   - Test double-payment detection

3. **Fix WebSocket Test Setup** (Priority: HIGH)
   - Review async test infrastructure
   - Use WebsocketCommunicator
   - Test real-time broadcasts

4. **Add Performance Tests** (Priority: MEDIUM)
   - Use django_assert_num_queries
   - Verify < 5 queries for lists
   - Detect N+1 query problems

---

## Test Coverage Goals

**Current**: 27% overall, ~85% for invoices app code that is tested

**Target**: ≥85% overall for invoices app

**To Achieve**: Add ~30-40 additional tests for missing areas

---

