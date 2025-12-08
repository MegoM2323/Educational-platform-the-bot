# T021: Invoice System Unit Tests - Fixes Required

**Status**: BLOCKED - 31 test failures identified
**Date**: 2025-12-08
**Total Tests**: 117
**Passed**: 86 (73.5%)
**Failed**: 31 (26.5%)

---

## Critical Issues (MUST FIX)

### Issue 1: Invoice Model - DateTime Validation Missing Null Checks

**File**: `backend/invoices/models.py`, lines 223-235

**Problem**:
```python
def clean(self):
    # Line 223 - ERROR: sent_at might be None, created_at is definitely set
    if self.sent_at and self.sent_at < self.created_at:  # Fails when sent_at is None
        raise ValidationError({...})

    # Line 228 - Same issue with viewed_at
    if self.viewed_at and self.sent_at and self.viewed_at < self.sent_at:
        raise ValidationError({...})

    # Line 233 - Same issue with paid_at
    if self.paid_at and self.viewed_at and self.paid_at < self.viewed_at:
        raise ValidationError({...})
```

**Current Code**:
```python
if self.sent_at and self.sent_at < self.created_at:  # TypeError if created_at is None
```

**Root Cause**:
- `created_at` is set by `auto_now_add=True` during save()
- But during validation, if invoice hasn't been saved yet, `created_at` might be None
- Test calls `full_clean()` before `save()`
- Comparison fails: `datetime.datetime < NoneType` is invalid

**Fix Required**:
```python
def clean(self):
    super().clean()

    # Check created_at is set (should be for new objects being validated)
    if self.created_at and self.sent_at and self.sent_at < self.created_at:
        raise ValidationError({'sent_at': 'Дата отправки не может быть раньше даты создания'})

    if self.viewed_at and self.sent_at and self.viewed_at < self.sent_at:
        raise ValidationError({'viewed_at': 'Дата просмотра не может быть раньше даты отправки'})

    if self.paid_at and self.viewed_at and self.paid_at < self.viewed_at:
        raise ValidationError({'paid_at': 'Дата оплаты не может быть раньше даты просмотра'})
```

**Affected Tests** (2):
- `test_models.py::TestInvoiceModel::test_invoice_sent_at_after_created_at`
- `test_models.py::TestInvoiceModel::test_invoice_viewed_at_after_sent_at`

**Effort**: LOW (5 min)

---

### Issue 2: Database Constraints Too Strict for Testing

**File**: `backend/invoices/models.py`, lines 160-173 (Model constraints)

**Problem**:
```python
class Meta:
    constraints = [
        # CHECK constraint requires sent_at >= created_at when status != DRAFT
        models.CheckConstraint(
            check=models.Q(sent_at__isnull=True) | models.Q(sent_at__gte=models.F('created_at')),
            name='check_invoice_sent_after_created'
        ),
        # ... similar for viewed_at, paid_at
    ]
```

**Issue**:
- When creating invoice with `status=SENT` but not setting `sent_at`, constraint fails
- Django auto-saves `sent_at` in `save()` method (line 254)
- But tests try to create invoice with `status=SENT` before saving
- Database rejects with: `CHECK constraint failed: check_invoice_sent_after_created`

**Test Code That Fails**:
```python
# This fails because status=SENT but sent_at is still None until save()
invoice = Invoice(
    tutor=...,
    student=...,
    parent=...,
    amount=Decimal('1000.00'),
    description='Test',
    due_date=date.today() + timedelta(days=7),
    status=Invoice.Status.SENT  # <-- Sets status but sent_at still None
)
invoice.save()  # <-- ERROR: sent_at not set yet, but constraint checks it
```

**Root Cause**:
- `save()` method sets `sent_at` AFTER checking constraints
- Need to ensure timestamps are set BEFORE database constraints are checked

**Fix Options**:

**Option A (RECOMMENDED)**: Fix save() to set timestamps before save
```python
def save(self, *args, **kwargs):
    """Set timestamps based on status transitions before save"""
    now = timezone.now()

    # Set timestamps FIRST, before any database operations
    if self.status == self.Status.SENT and not self.sent_at:
        self.sent_at = now

    if self.status == self.Status.VIEWED and not self.viewed_at:
        self.viewed_at = now

    if self.status == self.Status.PAID and not self.paid_at:
        self.paid_at = now

    # Auto-set parent from student profile
    if self.student_id and not self.parent_id:
        if hasattr(self.student, 'student_profile') and self.student.student_profile.parent:
            self.parent = self.student.student_profile.parent
        else:
            raise ValidationError('У студента не указан родитель в профиле')

    # NOW call parent save with timestamps set
    super().save(*args, **kwargs)
```

**Option B**: Use `pre_save` signal instead of `save()` override
```python
@receiver(pre_save, sender=Invoice)
def set_invoice_timestamps(sender, instance, **kwargs):
    now = timezone.now()
    if instance.status == Invoice.Status.SENT and not instance.sent_at:
        instance.sent_at = now
    # ... etc
```

**Affected Tests** (14):
- All tests creating invoices with non-DRAFT status
- test_serializers.py (4 tests)
- test_views.py (5 tests)
- test_reports.py (5 tests)

**Effort**: LOW (10 min)

---

### Issue 3: Missing Enrollment Validation in Serializer

**File**: `backend/invoices/serializers.py`, lines 158-180

**Problem**:
```python
def validate(self, attrs):
    """Комплексная валидация"""
    enrollment_id = attrs.get('enrollment_id')
    if enrollment_id:
        try:
            enrollment = SubjectEnrollment.objects.select_related(...).get(id=enrollment_id)

            # Check enrollment.student matches specified student
            student_id = attrs.get('student_id')
            if enrollment.student_id != student_id:  # THIS CHECK EXISTS
                raise serializers.ValidationError({...})
        except SubjectEnrollment.DoesNotExist:
            raise serializers.ValidationError({...})

    return attrs
```

**Test That Fails**:
```python
def test_enrollment_not_for_this_student(self, student1, student2, enrollment_for_student1):
    data = {
        'student_id': student2.id,  # Student 2
        'amount': Decimal('1000.00'),
        'description': 'Test',
        'due_date': date.today() + timedelta(days=7),
        'enrollment_id': enrollment_for_student1.id  # But enrollment for Student 1!
    }
    serializer = CreateInvoiceSerializer(data=data)
    assert not serializer.is_valid()  # FAILS - says it IS valid!
```

**Root Cause**:
- Validation logic exists but might have bug
- Need to verify enrollment relationship also works with tutor relationship
- May need to check: `enrollment.subject.teacher` or `enrollment.teacher` matches tutor

**Possible Fix**:
```python
def validate(self, attrs):
    enrollment_id = attrs.get('enrollment_id')
    if enrollment_id:
        from materials.models import SubjectEnrollment
        try:
            enrollment = SubjectEnrollment.objects.select_related(
                'student', 'subject', 'teacher'
            ).get(id=enrollment_id)

            student_id = attrs.get('student_id')

            # Check 1: Enrollment must belong to specified student
            if enrollment.student_id != student_id:
                raise serializers.ValidationError({
                    'enrollment_id': 'Зачисление не относится к указанному студенту'
                })

            # Check 2: If in context of tutor, verify tutor relationship
            # (May be optional depending on use case)

        except SubjectEnrollment.DoesNotExist:
            raise serializers.ValidationError({
                'enrollment_id': f'Зачисление с ID {enrollment_id} не найдено'
            })

    return attrs
```

**Affected Tests** (1):
- `test_serializers.py::TestCreateInvoiceSerializer::test_enrollment_not_for_this_student`

**Effort**: LOW (5 min)

---

### Issue 4: Missing Field Implementation in TutorStatisticsSerializer

**File**: `backend/invoices/serializers.py`, lines 200-206

**Problem**:
```python
class TutorStatisticsSerializer(serializers.Serializer):
    period = serializers.CharField()
    statistics = serializers.DictField(child=serializers.Field())  # <-- WRONG!
```

**Error**:
```
NotImplementedError: Field.to_representation() must be implemented for field .
```

**Issue**:
- Using generic `serializers.Field()` for dict values without implementation
- Must use a concrete field type like `serializers.DictField()` or specific field

**Fix**:
```python
class TutorStatisticsSerializer(serializers.Serializer):
    period = serializers.CharField()
    statistics = serializers.DictField(
        child=serializers.CharField(),  # Specify what type of values (or use Field with to_representation)
        required=True
    )
```

**Or better** - define specific fields:
```python
class StatisticsDataSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    invoices_count = serializers.IntegerField()
    paid_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    # ... etc

class TutorStatisticsSerializer(serializers.Serializer):
    period = serializers.CharField()
    statistics = StatisticsDataSerializer()
```

**Affected Tests** (1):
- `test_views.py::TestTutorStatistics::test_get_statistics_month`

**Effort**: LOW (10 min)

---

### Issue 5: Missing Date Range Validation

**File**: `backend/invoices/reports.py` (need to check exact location)

**Problem**:
- Reports module accepts invalid date ranges (start_date > end_date)
- Should raise ValidationError but doesn't

**Test That Fails**:
```python
def test_revenue_report_invalid_date_range(self):
    with pytest.raises(Exception):  # Expects exception
        # Call reports.get_revenue_report(start_date=date(2025, 12, 15), end_date=date(2025, 12, 8))
        # Should fail but doesn't!
```

**Fix**: Add validation at start of report generation methods
```python
def get_revenue_report(start_date, end_date):
    if start_date > end_date:
        raise ValidationError('Дата начала должна быть <= даты окончания')
    # ... rest of implementation
```

**Affected Tests** (1):
- `test_reports.py::TestRevenueReport::test_revenue_report_invalid_date_range`

**Effort**: LOW (5 min)

---

## Medium Priority Issues

### Issue 6: UUID Serialization in Payment Field

**File**: `backend/payments/models.py` and `backend/invoices/serializers.py`

**Problem**:
- Payment model uses UUID as primary key
- Serializer returns UUID as large integer instead of string
- Tests expect UUID type but get integer

**Example**:
```python
# Expected: UUID('9df82e4f-8f65-48dc-a0cd-8e7d028ebc22')
# Actual: 209977424253393837893986402305896791074
```

**Likely Cause**:
- UUID field not properly serialized
- Need to check PaymentBriefSerializer

**Fix**:
```python
class PaymentBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()  # Explicitly use UUIDField, not IntegerField
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    yookassa_payment_id = serializers.CharField()
    paid_at = serializers.DateTimeField()
```

**Affected Tests** (2):
- `test_serializers.py::TestInvoiceSerializer::test_serialization_with_payment`
- `test_serializers.py::TestCreateInvoiceSerializer::test_valid_create_data`

**Effort**: LOW (5 min)

---

### Issue 7: Response Format Mismatch in Create Invoice View

**File**: `backend/invoices/views.py` (CreateInvoiceView)

**Problem**:
- Test expects `response['student_id']` to be integer
- API returns `response['student']` as full user object

**Test**:
```python
def test_create_invoice_success(self):
    response = self.client.post(...)
    assert response['student_id'] == student_id  # FAILS: key is 'student', not 'student_id'
    # Actual: response['student'] = {'id': 2, 'email': '...', 'full_name': '...'}
```

**Fix**: Update test to match API response
```python
assert response['student']['id'] == student_id
# OR check that student is serialized as full object
assert response['student']['full_name'] == student.get_full_name()
```

**Affected Tests** (1):
- `test_views.py::TestTutorInvoiceViewSetCreate::test_create_invoice_success`

**Effort**: TRIVIAL (2 min)

---

### Issue 8: HTTP Status Code Convention

**File**: `backend/invoices/views.py` (Permission classes)

**Problem**:
- Test expects 401 Unauthorized
- API returns 403 Forbidden
- Both are correct but different conventions

**Test**:
```python
def test_list_invoices_unauthenticated(self):
    client = APIClient()  # No authentication
    response = client.get('/api/invoices/tutor/')
    assert response.status_code == 401  # FAILS: actual is 403
```

**Context**:
- 401 Unauthorized = client didn't provide credentials
- 403 Forbidden = client provided credentials but lacks permission
- DRF's `IsAuthenticated` returns 403 for unauthenticated users (design choice)

**Fix**: Update test
```python
# Either expect 403 (correct per DRF)
assert response.status_code == 403

# Or expect both
assert response.status_code in (401, 403)
```

**Affected Tests** (1):
- `test_views.py::TestTutorInvoiceViewSetList::test_list_invoices_unauthenticated`

**Effort**: TRIVIAL (1 min)

---

### Issue 9: Number Formatting in Statistics

**File**: `backend/invoices/reports.py` or serializer

**Problem**:
- Test expects `'3000.00'`
- Service returns `'3000'` (without decimal places)

**Test**:
```python
assert statistics['total_revenue'] == '3000.00'  # FAILS: actual is '3000'
```

**Fix**: Either
1. Format decimal values consistently:
   ```python
   f"{amount:.2f}"  # Always 2 decimal places
   ```
2. Update test to accept unformatted:
   ```python
   assert statistics['total_revenue'] == '3000'
   ```

**Affected Tests** (1):
- `test_reports.py::TestTutorStatistics::test_get_tutor_statistics_month`

**Effort**: TRIVIAL (2 min)

---

## Low Priority Issues (Tests Only)

### Issue 10: WebSocket Consumer Tests Completely Broken

**File**: `backend/tests/unit/invoices/test_websocket_consumers.py`

**Problem**:
- All 8 tests failing with generic `assert False is True`
- Tests not actually connecting to WebSocket
- Likely missing proper async test setup

**Affected Tests** (8):
- All tests in `TestInvoiceConsumerConnection`
- All tests in `TestInvoiceConsumerPingPong`
- All tests in `TestInvoiceConsumerEvents`
- All tests in `TestInvoiceConsumerErrorHandling`

**Fix Required**:
- Review WebSocket test implementation
- Use `channels.testing.WebsocketCommunicator` for proper async testing
- Ensure channel layer is configured in test environment
- May need to add async test markers and fixtures

**Effort**: MEDIUM (30-45 min) - Complex async testing

---

## Summary Table

| Issue | Severity | File | Line(s) | Tests Affected | Fix Time |
|-------|----------|------|---------|---|---|
| DateTime validation null checks | CRITICAL | models.py | 223-235 | 2 | 5 min |
| Constraint timing (sent_at not set) | CRITICAL | models.py | 254 | 14 | 10 min |
| Enrollment validation bug | CRITICAL | serializers.py | 158-180 | 1 | 5 min |
| Missing Field implementation | CRITICAL | serializers.py | 200 | 1 | 10 min |
| Date range validation | CRITICAL | reports.py | TBD | 1 | 5 min |
| UUID serialization | MEDIUM | serializers.py | 43-49 | 2 | 5 min |
| Response format mismatch | LOW | views.py | TBD | 1 | 2 min |
| HTTP status code | LOW | views.py | TBD | 1 | 1 min |
| Number formatting | LOW | reports.py | TBD | 1 | 2 min |
| WebSocket tests broken | MEDIUM | test_websocket.py | All | 8 | 30 min |
| **TOTAL** | | | | **31 failing** | **75 min** |

---

## Recommended Fix Order

1. **Phase 1 (Critical)** - 35 minutes:
   - Fix Issue 1: DateTime validation null checks (5 min)
   - Fix Issue 2: Constraint timing / save() method (10 min)
   - Fix Issue 5: Date range validation (5 min)
   - Fix Issue 4: Missing Field implementation (10 min)
   - Fix Issue 3: Enrollment validation (5 min)

2. **Phase 2 (Medium)** - 20 minutes:
   - Fix Issue 6: UUID serialization (5 min)
   - Fix WebSocket tests setup (15 min)

3. **Phase 3 (Trivial)** - 10 minutes:
   - Fix Issue 7: Response format (2 min)
   - Fix Issue 8: HTTP status (1 min)
   - Fix Issue 9: Number formatting (2 min)
   - Update remaining test assertions (5 min)

**Estimated Total Time**: 60-75 minutes

---

## Testing Verification

After each fix, verify with:
```bash
# Phase 1
bash scripts/run_tests.sh tests/unit/invoices/test_models.py -v

# Phase 1 + 2
bash scripts/run_tests.sh tests/unit/invoices/ --ignore=tests/unit/invoices/test_websocket_consumers.py -v

# Full suite
bash scripts/run_tests.sh tests/unit/invoices/ -v
```

Target: **All 117 tests passing** with **≥85% code coverage** for invoices app.

