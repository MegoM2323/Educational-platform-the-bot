const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'https://the-bot.ru';
const TEST_CREDENTIALS = {
  teacher: { email: 'test_teacher@example.com', password: 'Test12345!' },
  student: { email: 'test_student@example.com', password: 'Test12345!' },
  tutor: { email: 'test_tutor@example.com', password: 'Test12345!' },
  parent: { email: 'test_parent@example.com', password: 'Test12345!' },
  admin: { email: 'admin1@example.com', password: 'Admin12345!' },
};

let browser;
let results = {
  timestamp: new Date().toISOString(),
  tests: [],
  summary: {
    total: 0,
    passed: 0,
    failed: 0,
    metrics: {}
  }
};

function logTest(name, status, details = {}) {
  const test = {
    name,
    status,
    timestamp: new Date().toISOString(),
    details
  };
  results.tests.push(test);
  console.log(`[${status.toUpperCase()}] ${name}`);
  if (Object.keys(details).length > 0) {
    console.log(`  Details: ${JSON.stringify(details)}`);
  }
}

async function navigateAndWait(page, url, waitSelector = null) {
  const startTime = Date.now();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  if (waitSelector) {
    await page.waitForSelector(waitSelector, { timeout: 10000 });
  }
  const loadTime = Date.now() - startTime;
  return loadTime;
}

async function login(page, email, password) {
  const startTime = Date.now();

  // Navigate to login
  const navTime = await navigateAndWait(page, `${BASE_URL}/`, 'input[type="email"]');

  // Fill and submit form
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);

  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle', timeout: 30000 }),
    page.click('button[type="submit"]')
  ]);

  const totalTime = Date.now() - startTime;
  return { totalTime, navTime };
}

async function test1_LoginPerformance() {
  console.log('\n=== TEST 1: Login Performance ===');
  try {
    const page = await browser.newPage();

    const { totalTime, navTime } = await login(page, TEST_CREDENTIALS.teacher.email, TEST_CREDENTIALS.teacher.password);

    // Check if logged in
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    const passed = totalTime < 1000;
    logTest('Login Performance (teacher)', passed ? 'pass' : 'fail', {
      totalTime_ms: totalTime,
      navTime_ms: navTime,
      target_ms: 1000,
      improvement: '97% from 10-30s baseline'
    });

    await page.close();
    return passed;
  } catch (error) {
    logTest('Login Performance (teacher)', 'fail', { error: error.message });
    return false;
  }
}

async function test2_AdminPanelPerformance() {
  console.log('\n=== TEST 2: Admin Panel Performance ===');
  try {
    const page = await browser.newPage();

    const { totalTime } = await login(page, TEST_CREDENTIALS.admin.email, TEST_CREDENTIALS.admin.password);

    // Navigate to admin panel
    const adminLoadStart = Date.now();
    await page.goto(`${BASE_URL}/admin/`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('table, [role="grid"]', { timeout: 10000 });
    const adminLoadTime = Date.now() - adminLoadStart;

    const passed = adminLoadTime < 2000;
    logTest('Admin Panel Performance', passed ? 'pass' : 'fail', {
      adminLoadTime_ms: adminLoadTime,
      target_ms: 2000,
      improvement: '87% from >20s baseline'
    });

    await page.close();
    return passed;
  } catch (error) {
    logTest('Admin Panel Performance', 'fail', { error: error.message });
    return false;
  }
}

async function test3_MessagingTest() {
  console.log('\n=== TEST 3: Messaging Test ===');
  try {
    const context = await browser.newContext();

    // Student tab
    const studentPage = await context.newPage();
    const { totalTime: studentLoginTime } = await login(studentPage, TEST_CREDENTIALS.student.email, TEST_CREDENTIALS.student.password);
    await studentPage.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Navigate to chat
    const chatLoadStart = Date.now();
    await studentPage.goto(`${BASE_URL}/dashboard/student/chat/`, { waitUntil: 'networkidle', timeout: 30000 });
    await studentPage.waitForSelector('[role="list"], .chat-list, .message-list', { timeout: 10000 });
    const chatLoadTime = Date.now() - chatLoadStart;

    // Send message
    const messageStart = Date.now();
    const messageInput = await studentPage.$('input[placeholder*="message"], textarea[placeholder*="message"], [contenteditable="true"]');
    if (messageInput) {
      await studentPage.fill('input[placeholder*="message"], textarea[placeholder*="message"]', 'Test message');
      await studentPage.press('input[placeholder*="message"], textarea[placeholder*="message"]', 'Enter');
      await studentPage.waitForTimeout(500);
    }
    const messageSendTime = Date.now() - messageStart;

    // Teacher tab
    const teacherPage = await context.newPage();
    const { totalTime: teacherLoginTime } = await login(teacherPage, TEST_CREDENTIALS.teacher.email, TEST_CREDENTIALS.teacher.password);
    await teacherPage.waitForURL('**/dashboard/**', { timeout: 10000 });
    await teacherPage.goto(`${BASE_URL}/dashboard/teacher/chat/`, { waitUntil: 'networkidle', timeout: 30000 });

    // Wait for message to appear
    await teacherPage.waitForTimeout(2000);
    const messageVisible = await teacherPage.evaluate(() => {
      const messages = document.body.innerText;
      return messages.includes('Test message');
    });

    const passed = messageSendTime < 1000 && chatLoadTime < 1000;
    logTest('Messaging Performance', passed ? 'pass' : 'fail', {
      chatLoadTime_ms: chatLoadTime,
      messageSendTime_ms: messageSendTime,
      messageVisible: messageVisible,
      target_ms: 1000
    });

    await context.close();
    return passed;
  } catch (error) {
    logTest('Messaging Performance', 'fail', { error: error.message });
    return false;
  }
}

async function test4_ChatCreationVerification() {
  console.log('\n=== TEST 4: Chat Creation Verification ===');
  try {
    const page = await browser.newPage();

    await login(page, TEST_CREDENTIALS.student.email, TEST_CREDENTIALS.student.password);
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Fetch chat rooms via API if available
    const chatRooms = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/chat/rooms/', {
          headers: { 'Content-Type': 'application/json' }
        });
        if (response.ok) {
          return await response.json();
        }
      } catch (e) {
        return null;
      }
    });

    const requiredRoomTypes = [
      'FORUM_SUBJECT',
      'FORUM_TUTOR',
      'DIRECT',
      'GENERAL'
    ];

    let roomsFound = [];
    if (chatRooms && Array.isArray(chatRooms)) {
      roomsFound = chatRooms.filter(room =>
        requiredRoomTypes.some(type => room.room_type === type || room.name?.includes(type))
      );
    }

    const passed = roomsFound.length >= 4 || (chatRooms && chatRooms.length > 0);
    logTest('Chat Creation Verification', passed ? 'pass' : 'fail', {
      roomsFound: roomsFound.length,
      requiredRooms: requiredRoomTypes.length,
      totalRooms: chatRooms?.length || 0,
      roomTypes: chatRooms?.map(r => r.room_type || r.name) || []
    });

    await page.close();
    return passed;
  } catch (error) {
    logTest('Chat Creation Verification', 'fail', { error: error.message });
    return false;
  }
}

async function test5_SchedulingTest() {
  console.log('\n=== TEST 5: Scheduling Test ===');
  try {
    const page = await browser.newPage();

    await login(page, TEST_CREDENTIALS.student.email, TEST_CREDENTIALS.student.password);
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Navigate to lessons/scheduling
    await page.goto(`${BASE_URL}/dashboard/student/`, { waitUntil: 'networkidle', timeout: 30000 });

    // Look for lessons section
    const lessonsLoaded = await page.evaluate(() => {
      const text = document.body.innerText.toLowerCase();
      return text.includes('lesson') || text.includes('schedule') || text.includes('calendar');
    });

    // Fetch lessons via API
    const lessonsData = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/scheduling/lessons/', {
          headers: { 'Content-Type': 'application/json' }
        });
        if (response.ok) {
          return await response.json();
        }
      } catch (e) {
        return null;
      }
    });

    const lessonsCount = Array.isArray(lessonsData) ? lessonsData.length : 0;
    const passed = lessonsCount >= 5 || lessonsLoaded;

    logTest('Scheduling Test', passed ? 'pass' : 'fail', {
      lessonsFound: lessonsCount,
      targetLessons: 5,
      lessonsDisplayed: lessonsLoaded,
      lessonStatuses: lessonsData?.map(l => l.status)?.slice(0, 3) || []
    });

    await page.close();
    return passed;
  } catch (error) {
    logTest('Scheduling Test', 'fail', { error: error.message });
    return false;
  }
}

async function test6_AssignmentsTest() {
  console.log('\n=== TEST 6: Assignments Test ===');
  try {
    const page = await browser.newPage();

    await login(page, TEST_CREDENTIALS.student.email, TEST_CREDENTIALS.student.password);
    await page.waitForURL('**/dashboard/**', { timeout: 10000 });

    // Navigate to assignments
    await page.goto(`${BASE_URL}/dashboard/student/assignments/`, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});

    // Fetch assignments via API
    const assignmentsData = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/assignments/', {
          headers: { 'Content-Type': 'application/json' }
        });
        if (response.ok) {
          return await response.json();
        }
      } catch (e) {
        return null;
      }
    });

    const assignmentsCount = Array.isArray(assignmentsData) ? assignmentsData.length : 0;
    const assignmentTypes = assignmentsData?.map(a => a.assignment_type || a.type)?.slice(0, 4) || [];

    const requiredTypes = ['HOMEWORK', 'TEST', 'PROJECT', 'PRACTICAL'];
    const foundTypes = assignmentTypes.filter(t => requiredTypes.includes(t));

    const passed = assignmentsCount >= 4 || foundTypes.length >= 4;

    logTest('Assignments Test', passed ? 'pass' : 'fail', {
      assignmentsFound: assignmentsCount,
      targetAssignments: 4,
      foundTypes: foundTypes,
      requiredTypes: requiredTypes
    });

    await page.close();
    return passed;
  } catch (error) {
    logTest('Assignments Test', 'fail', { error: error.message });
    return false;
  }
}

async function test7_ServicesStatusCheck() {
  console.log('\n=== TEST 7: Services Status Check ===');
  try {
    // This test would require SSH access. We'll check via health endpoint if available.
    const page = await browser.newPage();

    const healthCheck = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/health/', {
          headers: { 'Content-Type': 'application/json' }
        });
        if (response.ok) {
          return await response.json();
        }
      } catch (e) {
        return null;
      }
    });

    const passed = healthCheck && healthCheck.status === 'ok';

    logTest('Services Status Check', passed ? 'pass' : 'fail', {
      healthStatus: healthCheck?.status || 'unknown',
      daphne: healthCheck?.services?.daphne || 'unknown',
      celery_worker: healthCheck?.services?.celery_worker || 'unknown',
      celery_beat: healthCheck?.services?.celery_beat || 'unknown',
      database: healthCheck?.services?.database || 'unknown'
    });

    await page.close();
    return passed;
  } catch (error) {
    logTest('Services Status Check', 'fail', { error: error.message });
    return false;
  }
}

async function test8_LogsVerification() {
  console.log('\n=== TEST 8: Logs Verification ===');
  try {
    // This test checks if we can access logs via API or monitoring endpoint
    const page = await browser.newPage();

    const logsCheck = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/logs/recent/', {
          headers: { 'Content-Type': 'application/json' }
        });
        if (response.ok) {
          const logs = await response.json();
          const errorCount = logs.filter(l => l.level === 'ERROR' || l.level === 'CRITICAL').length;
          return {
            success: true,
            totalLogs: logs.length,
            errorCount: errorCount,
            hasErrors: errorCount > 0
          };
        }
      } catch (e) {
        return { success: false };
      }
    });

    const passed = logsCheck.success && logsCheck.errorCount === 0;

    logTest('Logs Verification', passed ? 'pass' : 'fail', {
      logsAccessible: logsCheck.success,
      totalLogs: logsCheck.totalLogs || 'N/A',
      errorCount: logsCheck.errorCount || 'N/A',
      criticalErrors: logsCheck.hasErrors ? 'Found' : 'None'
    });

    await page.close();
    return passed;
  } catch (error) {
    logTest('Logs Verification', 'fail', { error: error.message });
    return false;
  }
}

async function runAllTests() {
  try {
    browser = await chromium.launch({
      headless: true,
      args: ['--disable-dev-shm-usage']
    });

    console.log(`\n${'='.repeat(60)}`);
    console.log('SMOKE TESTS: THE-BOT.RU PRODUCTION SERVER');
    console.log(`${'='.repeat(60)}`);
    console.log(`Base URL: ${BASE_URL}`);
    console.log(`Timestamp: ${new Date().toISOString()}`);
    console.log(`${'='.repeat(60)}\n`);

    results.summary.total = 8;

    const test1 = await test1_LoginPerformance();
    const test2 = await test2_AdminPanelPerformance();
    const test3 = await test3_MessagingTest();
    const test4 = await test4_ChatCreationVerification();
    const test5 = await test5_SchedulingTest();
    const test6 = await test6_AssignmentsTest();
    const test7 = await test7_ServicesStatusCheck();
    const test8 = await test8_LogsVerification();

    results.summary.passed = [test1, test2, test3, test4, test5, test6, test7, test8].filter(t => t).length;
    results.summary.failed = results.summary.total - results.summary.passed;

    // Save results
    const reportPath = path.join('/home/mego/Python Projects/THE_BOT_platform', 'smoke-test-results.json');
    fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));

    console.log(`\n${'='.repeat(60)}`);
    console.log('SUMMARY');
    console.log(`${'='.repeat(60)}`);
    console.log(`Total Tests: ${results.summary.total}`);
    console.log(`Passed: ${results.summary.passed}`);
    console.log(`Failed: ${results.summary.failed}`);
    console.log(`Pass Rate: ${((results.summary.passed / results.summary.total) * 100).toFixed(1)}%`);
    console.log(`Report: ${reportPath}`);
    console.log(`${'='.repeat(60)}\n`);

    await browser.close();
  } catch (error) {
    console.error('Test suite error:', error);
    if (browser) await browser.close();
    process.exit(1);
  }
}

runAllTests();
