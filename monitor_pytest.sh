#!/bin/bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Ждем завершения pytest
echo "Waiting for pytest to complete..."
while ps aux | grep "python -m pytest" | grep -v grep > /dev/null; do
  echo "[$(date '+%H:%M:%S')] pytest running..."
  sleep 30
done

echo "[$(date '+%H:%M:%S')] pytest completed!"
sleep 2

# Проверяем xml файл
if [ -f FINAL_RESULTS.xml ]; then
  echo "Generating final reports..."
  
  # Базовая статистика
  total_tests=$(grep -o "tests=" FINAL_RESULTS.xml | head -1 | cut -d'"' -f2)
  passed=$(grep -c " PASSED " FINAL_PYTEST.log)
  failed=$(grep -c " FAILED " FINAL_PYTEST.log)
  errors=$(grep -c " ERROR " FINAL_PYTEST.log)
  
  echo "Total tests: $total_tests"
  echo "Passed: $passed"
  echo "Failed: $failed"
  echo "Errors: $errors"
fi
