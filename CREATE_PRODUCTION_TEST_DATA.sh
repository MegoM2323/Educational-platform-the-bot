#!/bin/bash

# Script to create test data in production database
# Usage: ./CREATE_PRODUCTION_TEST_DATA.sh <db_host> <db_name> <db_user> <db_password>

DB_HOST="${1:-localhost}"
DB_NAME="${2:-thebot}"
DB_USER="${3:-postgres}"
DB_PASSWORD="${4:-}"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    Creating Production Test Data - THE_BOT Platform        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Database: $DB_HOST / $DB_NAME"
echo "User: $DB_USER"
echo ""

# SQL script with hashed passwords
# Passwords are hashed using Django's default hasher
# Pattern: pbkdf2_sha256$600000$salt$hash

cat > /tmp/create_test_users.sql << 'EOF'
-- Create test users for THE_BOT platform
-- Passwords: password123 for regular users, admin123 for admin

-- Admin User
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_staff, is_superuser, date_joined, username)
VALUES
  ('admin@thebot.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Администратор', 'Система', true, true, true, NOW(), 'admin')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Teacher: Anna (Математика)
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_teacher, date_joined, username)
VALUES
  ('anna.smirnova@school.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Анна', 'Смирнова', true, true, NOW(), 'anna_smirnova')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Teacher: Igor (Русский язык)
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_teacher, date_joined, username)
VALUES
  ('igor.vasiliev@school.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Игорь', 'Васильев', true, true, NOW(), 'igor_vasiliev')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Student: Ivan
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_student, date_joined, username)
VALUES
  ('ivan.petrov@school.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Иван', 'Петров', true, true, NOW(), 'ivan_petrov')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Student: Maria
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_student, date_joined, username)
VALUES
  ('maria.sidorova@school.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Мария', 'Сидорова', true, true, NOW(), 'maria_sidorova')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Student: Petr
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_student, date_joined, username)
VALUES
  ('petr.ivanov@school.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Петр', 'Иванов', true, true, NOW(), 'petr_ivanov')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Tutor: Dmitry
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_tutor, date_joined, username)
VALUES
  ('dmitry.kozlov@school.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Дмитрий', 'Козлов', true, true, NOW(), 'dmitry_kozlov')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Parent: Sergey
INSERT INTO accounts_user
  (email, password, first_name, last_name, is_active, is_parent, date_joined, username)
VALUES
  ('sergey.petrov@family.com', 'pbkdf2_sha256$600000$e2e9f7d8c3b2a1f4$hashed_password', 'Сергей', 'Петров', true, true, NOW(), 'sergey_petrov')
ON CONFLICT (email) DO UPDATE SET is_active = true;

-- Show created users
SELECT
  email,
  first_name,
  CASE WHEN is_staff THEN 'ADMIN'
       WHEN is_teacher THEN 'TEACHER'
       WHEN is_student THEN 'STUDENT'
       WHEN is_tutor THEN 'TUTOR'
       WHEN is_parent THEN 'PARENT'
       ELSE 'USER' END as role
FROM accounts_user
WHERE email LIKE '%@%'
ORDER BY email;
EOF

if [ -z "$DB_PASSWORD" ]; then
    echo "Executing SQL without password (trusted connection)..."
    PGPASSWORD="" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_test_users.sql
else
    echo "Executing SQL with password..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_test_users.sql
fi

echo ""
echo "✅ Test data creation completed"
echo ""
echo "Now update passwords in Django shell:"
echo "  python manage.py shell"
echo "  from django.contrib.auth import get_user_model"
echo "  User = get_user_model()"
echo "  for user in User.objects.all():"
echo "      if user.email.endswith('@thebot.com'): user.set_password('admin123')"
echo "      else: user.set_password('password123')"
echo "      user.save()"
