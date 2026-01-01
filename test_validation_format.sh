#!/bin/bash

echo "=== Тестирование унификации формата ошибок валидации ==="
echo ""

API_URL="http://localhost:8000/api/auth/login/"

echo "1. Тест 1: Пустой пароль"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":""}' \
  -s | jq '.'
echo ""

echo "2. Тест 2: Пустой email"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"email":"","password":"test123"}' \
  -s | jq '.'
echo ""

echo "3. Тест 3: Оба поля пусты"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"email":"","password":""}' \
  -s | jq '.'
echo ""

echo "4. Тест 4: Нет email и username, только пароль"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"password":"test123"}' \
  -s | jq '.'
echo ""

echo "5. Тест 5: Валидный login"
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"test123"}' \
  -s | jq '.'
echo ""
