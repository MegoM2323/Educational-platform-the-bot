from accounts.models import User

# Fix test user roles
test_users = [
    ('teacher@test.com', 'teacher'),
    ('tutor@test.com', 'tutor'),
    ('parent@test.com', 'parent'),
]

for email, role in test_users:
    try:
        user = User.objects.get(email=email)
        print(f"{email}: {user.role} -> {role}")
        user.role = role
        user.save()
        print(f"  ✅ Updated")
    except User.DoesNotExist:
        print(f"{email}: NOT FOUND")
