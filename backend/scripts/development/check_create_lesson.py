import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from materials.models import Subject

User = get_user_model()
teacher = User.objects.get(email="teacher1@test.com")
teacher_token = Token.objects.get_or_create(user=teacher)[0].key

with override_settings(ALLOWED_HOSTS=['*']):
    client = Client(SERVER_NAME='127.0.0.1')
    
    subject = Subject.objects.first()
    student = User.objects.get(email="student1@test.com")
    
    data = {
        "subject": subject.id if subject else 1,
        "student": student.id,
        "date": "2026-01-25",
        "start_time": "09:00:00",
        "end_time": "09:45:00",
    }
    
    r = client.post('/api/scheduling/lessons/', 
                   data=json.dumps(data),
                   content_type='application/json',
                   HTTP_AUTHORIZATION=f'Token {teacher_token}')
    
    print(f"Status: {r.status_code}")
    print(f"Response: {r.content.decode()}")
