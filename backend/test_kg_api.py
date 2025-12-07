#!/usr/bin/env python
"""
Test script for Knowledge Graph API endpoints
Tests all API routes to verify they work correctly
"""
import os
import sys
import django

# Setup Django environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.core.management import call_command
from accounts.models import User
from materials.models import Subject, TeacherSubject
from rest_framework.authtoken.models import Token
import json

def test_knowledge_graph_api():
    """Test Knowledge Graph API endpoints"""

    print("=" * 70)
    print("TESTING KNOWLEDGE GRAPH API ENDPOINTS")
    print("=" * 70)

    # Run migrations
    print("\n0. Running migrations...")
    call_command('migrate', '--run-syncdb', verbosity=0)
    print("   ✓ Migrations applied")

    # Create test user
    print("\n1. Creating test teacher user...")
    user = User.objects.create_user(
        username='teacher_test',
        email='teacher@test.com',
        password='test123',
        role='teacher',
        first_name='Test',
        last_name='Teacher'
    )
    token, _ = Token.objects.get_or_create(user=user)
    print(f"   ✓ User created: {user.email}")
    print(f"   ✓ Token: {token.key}")

    # Create subject for teacher
    subject = Subject.objects.create(name='Mathematics', description='Math subject')
    TeacherSubject.objects.create(teacher=user, subject=subject)
    print(f"   ✓ Subject created: {subject.name}")

    # Create client
    client = Client()
    headers = {
        'HTTP_AUTHORIZATION': f'Token {token.key}',
        'content_type': 'application/json'
    }

    # Test 1: Create Element
    print("\n2. Testing Element Creation (POST /api/knowledge-graph/elements/)...")
    element_data = {
        'title': 'Simple Addition Problem',
        'description': 'Basic addition task for beginners',
        'element_type': 'text_problem',
        'content': {
            'problem_text': 'What is 2 + 2?'
        },
        'difficulty': 1,
        'estimated_time_minutes': 5,
        'max_score': 10
    }
    response = client.post(
        '/api/knowledge-graph/elements/',
        data=json.dumps(element_data),
        **headers
    )
    print(f"   Status: {response.status_code}")
    response_data = response.json() if response.status_code in [200, 201] else response.content
    print(f"   Response: {response_data}")

    if response.status_code == 201:
        # Extract ID from 'data' wrapper
        element_id = response_data.get('data', {}).get('id') if isinstance(response_data, dict) else None
        print(f"   ✓ Element created with ID: {element_id}")
    else:
        print(f"   ✗ FAILED: {response.content}")
        return False

    # Test 2: List Elements
    print("\n3. Testing Element List (GET /api/knowledge-graph/elements/)...")
    response = client.get('/api/knowledge-graph/elements/', **headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        elements = response.json()
        print(f"   ✓ Found {len(elements) if isinstance(elements, list) else 'N/A'} elements")
    else:
        print(f"   ✗ FAILED: {response.content}")

    # Test 3: Get Element Detail
    print(f"\n4. Testing Element Detail (GET /api/knowledge-graph/elements/{element_id}/)...")
    response = client.get(f'/api/knowledge-graph/elements/{element_id}/', **headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Element retrieved: {response.json().get('title')}")
    else:
        print(f"   ✗ FAILED: {response.content}")

    # Test 4: Create Lesson
    print("\n5. Testing Lesson Creation (POST /api/knowledge-graph/lessons/)...")
    lesson_data = {
        'title': 'Introduction to Math',
        'description': 'Basic arithmetic operations',
        'subject': subject.id
    }
    response = client.post(
        '/api/knowledge-graph/lessons/',
        data=json.dumps(lesson_data),
        **headers
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 201:
        # Extract ID from 'data' wrapper
        lesson_response = response.json()
        lesson_id = lesson_response.get('data', {}).get('id') if isinstance(lesson_response, dict) else None
        print(f"   ✓ Lesson created with ID: {lesson_id}")
    else:
        print(f"   ✗ FAILED: {response.content}")
        return False

    # Test 5: Add Element to Lesson
    print(f"\n6. Testing Add Element to Lesson (POST /api/knowledge-graph/lessons/{lesson_id}/elements/)...")
    add_element_data = {
        'element_id': element_id,
        'order': 1
    }
    response = client.post(
        f'/api/knowledge-graph/lessons/{lesson_id}/elements/',
        data=json.dumps(add_element_data),
        **headers
    )
    print(f"   Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"   ✓ Element added to lesson")
    else:
        print(f"   ✗ FAILED: {response.content}")

    # Test 6: List Lessons
    print("\n7. Testing Lesson List (GET /api/knowledge-graph/lessons/)...")
    response = client.get('/api/knowledge-graph/lessons/', **headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        lessons = response.json()
        print(f"   ✓ Found {len(lessons) if isinstance(lessons, list) else 'N/A'} lessons")
    else:
        print(f"   ✗ FAILED: {response.content}")

    print("\n" + "=" * 70)
    print("API TESTING COMPLETE")
    print("=" * 70)
    return True

if __name__ == '__main__':
    try:
        success = test_knowledge_graph_api()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
