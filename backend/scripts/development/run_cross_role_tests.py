#!/usr/bin/env python
"""
Quick test runner for cross-role messaging.
Runs all 8 scenarios and prints summary table.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ENVIRONMENT'] = 'development'

django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile
from materials.models import SubjectEnrollment, Subject
from chat.permissions import CanInitiateChat

User = get_user_model()

# Get existing test users
student = User.objects.get(email='student@test.com')
teacher = User.objects.get(email='teacher@test.com')
tutor = User.objects.get(email='tutor@test.com')
parent = User.objects.get(email='parent@test.com')

# Get student profile to check relationships
student_profile = StudentProfile.objects.get(user=student)

# Get subject ID from student's enrollment
student_enrollments = SubjectEnrollment.objects.filter(student=student)
subject_id = student_enrollments.first().subject_id if student_enrollments.exists() else None

print("\n" + "="*80)
print("CROSS-ROLE MESSAGING TEST RESULTS")
print("="*80 + "\n")

# Test scenarios: (from_user, to_user, subject_id, scenario_name)
# Note: Student-Teacher chats REQUIRE subject_id to work properly
scenarios = [
    (student, teacher, subject_id, "Student → Teacher"),
    (teacher, student, subject_id, "Teacher → Student"),
    (tutor, student, None, "Tutor → Student"),
    (student, tutor, None, "Student → Tutor"),
    (parent, teacher, subject_id, "Parent → Teacher"),
    (teacher, parent, subject_id, "Teacher → Parent"),
    (parent, tutor, None, "Parent → Tutor"),
    (tutor, parent, None, "Tutor → Parent"),
]

results = {}
passed = 0
failed = 0

for from_user, to_user, subj_id, scenario_name in scenarios:
    try:
        # Check permission using CanInitiateChat
        can_chat, chat_type, enrollment = CanInitiateChat.can_chat_with(
            from_user, to_user, subj_id
        )

        if can_chat and enrollment:
            status = "PASS"
            reason = f"Chat type: {chat_type}"
            passed += 1
        else:
            status = "FAIL"
            reason = f"Permission denied (can_chat={can_chat}, enrollment={enrollment})"
            failed += 1

        results[scenario_name] = (status, reason)
    except Exception as e:
        status = "ERROR"
        reason = str(e)[:50]
        failed += 1
        results[scenario_name] = (status, reason)

# Print results
print(f"{'Scenario':<25} | {'Status':<6} | {'Reason':<50}")
print("-" * 85)

for scenario, (status, reason) in results.items():
    status_short = status[:6]
    reason_short = reason[:47]
    print(f"{scenario:<25} | {status_short:<6} | {reason_short:<50}")

print("\n" + "="*80)
print(f"SUMMARY: {passed} PASS, {failed} FAIL")
print("="*80 + "\n")

# Detailed info
print("RELATIONSHIPS CHECK:")
print(f"  Student: {student.get_full_name()} (ID: {student.id})")
print(f"  Teacher: {teacher.get_full_name()} (ID: {teacher.id})")
print(f"  Tutor: {tutor.get_full_name()} (ID: {tutor.id})")
print(f"  Parent: {parent.get_full_name()} (ID: {parent.id})")
print()
print(f"  Student has tutor: {student_profile.tutor}")
print(f"  Student has parent: {student_profile.parent}")

enrollments = SubjectEnrollment.objects.filter(student=student)
print(f"  Student enrollments: {enrollments.count()}")
for e in enrollments:
    print(f"    - {e.subject.name} (ID: {e.subject_id}) with {e.teacher.get_full_name()}")

sys.exit(0 if failed == 0 else 1)
