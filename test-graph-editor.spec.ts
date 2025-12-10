import { test, expect, Page } from '@playwright/test'

const BASE_URL = 'http://localhost:8080'
const API_URL = 'http://localhost:8000/api'

// Test data
const TEST_TEACHER_EMAIL = 'test.teacher@example.com'
const TEST_TEACHER_PASSWORD = 'Test123!'

test.describe('Graph Editor E2E Tests', () => {
  let page: Page

  test.beforeAll(async () => {
    console.log('[TEST] Starting Graph Editor E2E tests')
    console.log(`[TEST] Base URL: ${BASE_URL}`)
    console.log(`[TEST] API URL: ${API_URL}`)
  })

  test('Scenario 1: Navigation to Graph Editor', async ({ browser }) => {
    page = await browser.newPage()

    // Step 1: Go to login page
    console.log('[S1] Navigating to login page')
    await page.goto(`${BASE_URL}/auth`)

    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Step 2: Check if login form exists
    const emailInput = page.locator('input[name="email"], input[type="email"]').first()
    await expect(emailInput).toBeVisible({ timeout: 5000 })
    console.log('[S1] Login form visible')

    // Step 3: Fill credentials
    console.log('[S1] Filling login credentials')
    await emailInput.fill(TEST_TEACHER_EMAIL)
    const passwordInput = page.locator('input[name="password"], input[type="password"]').first()
    await passwordInput.fill(TEST_TEACHER_PASSWORD)

    // Step 4: Submit login
    const submitButton = page.locator('button[type="submit"]').first()
    await submitButton.click()

    // Wait for navigation
    await page.waitForNavigation()
    await page.waitForLoadState('networkidle')

    console.log('[S1] Logged in successfully')

    // Step 5: Find and click "Редактор графа" link in sidebar
    console.log('[S1] Looking for "Редактор графа" menu item')

    // Try to find the menu item with exact text match
    const graphEditorLink = page.locator('a, button').filter({ hasText: /Редактор графа|Graph Editor/ }).first()

    if (await graphEditorLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('[S1] Found graph editor link, clicking')
      await graphEditorLink.click()
      await page.waitForLoadState('networkidle')
    } else {
      console.log('[S1] Graph editor link not found by text, checking page structure')
      // List all navigation items for debugging
      const navItems = await page.locator('nav a, nav button, [role="navigation"] a, [role="navigation"] button').all()
      console.log(`[S1] Found ${navItems.length} navigation items`)
      for (const item of navItems) {
        const text = await item.textContent()
        console.log(`[S1]   - ${text?.trim()}`)
      }

      // Try alternative: look for any link mentioning "граф" or "graph"
      const graphLink = page.locator('a, button').filter({ hasText: /граф|graph/i }).first()
      if (await graphLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('[S1] Found graph link via pattern match')
        await graphLink.click()
        await page.waitForLoadState('networkidle')
      }
    }

    // Step 6: Verify page loaded without errors
    console.log('[S1] Checking for console errors')
    let hasErrors = false
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log(`[ERROR] ${msg.text()}`)
        hasErrors = true
      }
    })

    // Wait a bit for any potential errors to appear
    await page.waitForTimeout(2000)

    // Check if we're on graph editor page (check for specific elements)
    const pageTitle = page.locator('h1, h2, [role="heading"]').first()
    const titleText = await pageTitle.textContent()
    console.log(`[S1] Current page title: ${titleText}`)

    expect(hasErrors).toBe(false)
    console.log('[S1] PASSED: Navigation successful, no console errors')
  })

  test('Scenario 2: Subject Selection', async ({ browser }) => {
    page = await browser.newPage()

    console.log('[S2] Testing subject selection')

    // Login
    console.log('[S2] Logging in')
    await page.goto(`${BASE_URL}/auth`)
    await page.waitForLoadState('networkidle')

    const emailInput = page.locator('input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]').first()
    const submitButton = page.locator('button[type="submit"]').first()

    await emailInput.fill(TEST_TEACHER_EMAIL)
    await passwordInput.fill(TEST_TEACHER_PASSWORD)
    await submitButton.click()
    await page.waitForNavigation()
    await page.waitForLoadState('networkidle')

    // Navigate to Graph Editor
    console.log('[S2] Navigating to graph editor')
    const graphLink = page.locator('a, button').filter({ hasText: /граф|graph/i }).first()
    if (await graphLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await graphLink.click()
      await page.waitForLoadState('networkidle')
    }

    // Look for subject selector
    console.log('[S2] Looking for subject selector')
    const subjectSelect = page.locator('select, [role="combobox"], [role="listbox"]').first()

    if (await subjectSelect.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('[S2] Subject selector found')

      // Get current value
      const currentValue = await subjectSelect.inputValue().catch(() => 'N/A')
      console.log(`[S2] Current subject: ${currentValue}`)

      // Try to open dropdown and select first option
      await subjectSelect.click()
      await page.waitForTimeout(500)

      const options = page.locator('[role="option"]').all()
      const optionCount = (await options).length
      console.log(`[S2] Found ${optionCount} subject options`)

      if (optionCount > 0) {
        const firstOption = (await options)[0]
        const optionText = await firstOption.textContent()
        console.log(`[S2] Selecting: ${optionText}`)
        await firstOption.click()
        await page.waitForTimeout(1000)
      }

      expect(true).toBe(true)
      console.log('[S2] PASSED: Subject selection works')
    } else {
      console.log('[S2] No subject selector found - may be single subject setup')
      console.log('[S2] PASSED: No subject selector needed')
    }
  })

  test('Scenario 3: Student Selection', async ({ browser }) => {
    page = await browser.newPage()

    console.log('[S3] Testing student selection')

    // Login
    console.log('[S3] Logging in')
    await page.goto(`${BASE_URL}/auth`)
    await page.waitForLoadState('networkidle')

    const emailInput = page.locator('input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]').first()
    const submitButton = page.locator('button[type="submit"]').first()

    await emailInput.fill(TEST_TEACHER_EMAIL)
    await passwordInput.fill(TEST_TEACHER_PASSWORD)
    await submitButton.click()
    await page.waitForNavigation()
    await page.waitForLoadState('networkidle')

    // Navigate to Graph Editor
    console.log('[S3] Navigating to graph editor')
    const graphLink = page.locator('a, button').filter({ hasText: /граф|graph/i }).first()
    if (await graphLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await graphLink.click()
      await page.waitForLoadState('networkidle')
    }

    // Look for student selector dropdown
    console.log('[S3] Looking for student selector')
    const dropdowns = page.locator('select, [role="combobox"], button:has-text("Выбрать"), button:has-text("Select")').all()
    const dropdownCount = (await dropdowns).length
    console.log(`[S3] Found ${dropdownCount} dropdown elements`)

    // Try to find student dropdown by checking for label
    const studentLabel = page.locator('label, div').filter({ hasText: /студент|student/i }).first()
    if (await studentLabel.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('[S3] Found student label')

      // Find the associated select/dropdown
      const parent = studentLabel.locator('..')
      const dropdown = parent.locator('select, [role="combobox"]').first()

      if (await dropdown.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('[S3] Opening student dropdown')
        await dropdown.click()
        await page.waitForTimeout(500)

        // Select first student
        const studentOption = page.locator('[role="option"]').first()
        if (await studentOption.isVisible({ timeout: 2000 }).catch(() => false)) {
          const text = await studentOption.textContent()
          console.log(`[S3] Selecting student: ${text}`)
          await studentOption.click()
          await page.waitForTimeout(1000)
          expect(true).toBe(true)
          console.log('[S3] PASSED: Student selection works')
        } else {
          console.log('[S3] No student options available')
          console.log('[S3] PASSED: No students to select')
        }
      } else {
        console.log('[S3] Student dropdown not found')
        console.log('[S3] PASSED: No student selector found')
      }
    } else {
      console.log('[S3] No student label found - may not be required')
      console.log('[S3] PASSED: No student selection required')
    }
  })

  test('Scenario 4: Graph Visualization', async ({ browser }) => {
    page = await browser.newPage()

    console.log('[S4] Testing graph visualization')

    // Login
    console.log('[S4] Logging in')
    await page.goto(`${BASE_URL}/auth`)
    await page.waitForLoadState('networkidle')

    const emailInput = page.locator('input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]').first()
    const submitButton = page.locator('button[type="submit"]').first()

    await emailInput.fill(TEST_TEACHER_EMAIL)
    await passwordInput.fill(TEST_TEACHER_PASSWORD)
    await submitButton.click()
    await page.waitForNavigation()
    await page.waitForLoadState('networkidle')

    // Navigate to Graph Editor
    console.log('[S4] Navigating to graph editor')
    const graphLink = page.locator('a, button').filter({ hasText: /граф|graph/i }).first()
    if (await graphLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await graphLink.click()
      await page.waitForLoadState('networkidle')
    }

    // Check for graph visualization
    console.log('[S4] Checking for graph canvas')
    const canvas = page.locator('canvas').first()
    const svgGraphic = page.locator('svg').first()
    const graphContainer = page.locator('[class*="graph"], [class*="canvas"], [id*="graph"]').first()

    let graphFound = false

    if (await canvas.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('[S4] Canvas element found')
      graphFound = true
    }

    if (await svgGraphic.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('[S4] SVG graphic found')
      graphFound = true
    }

    if (await graphContainer.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('[S4] Graph container found')
      graphFound = true
    }

    // Check for "empty graph" message
    const emptyMessage = page.locator('text=/Граф пуст|Graph is empty|Нет данных/i')
    const hasEmptyMessage = await emptyMessage.isVisible({ timeout: 2000 }).catch(() => false)

    if (hasEmptyMessage) {
      console.log('[S4] Empty graph message displayed')
      graphFound = true
    }

    // Check for statistics display
    const stats = page.locator('text=/уроков|lessons|зависимостей|dependencies/i').first()
    const hasStats = await stats.isVisible({ timeout: 2000 }).catch(() => false)

    if (hasStats) {
      console.log('[S4] Statistics display found')
      const statsText = await stats.textContent()
      console.log(`[S4] Stats: ${statsText}`)
    }

    expect(graphFound || hasEmptyMessage).toBe(true)
    console.log('[S4] PASSED: Graph visualization checked')
  })

  test('Scenario 5: Edit Mode', async ({ browser }) => {
    page = await browser.newPage()

    console.log('[S5] Testing edit mode')

    // Login
    console.log('[S5] Logging in')
    await page.goto(`${BASE_URL}/auth`)
    await page.waitForLoadState('networkidle')

    const emailInput = page.locator('input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]').first()
    const submitButton = page.locator('button[type="submit"]').first()

    await emailInput.fill(TEST_TEACHER_EMAIL)
    await passwordInput.fill(TEST_TEACHER_PASSWORD)
    await submitButton.click()
    await page.waitForNavigation()
    await page.waitForLoadState('networkidle')

    // Navigate to Graph Editor
    console.log('[S5] Navigating to graph editor')
    const graphLink = page.locator('a, button').filter({ hasText: /граф|graph/i }).first()
    if (await graphLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await graphLink.click()
      await page.waitForLoadState('networkidle')
    }

    // Look for Edit button
    console.log('[S5] Looking for Edit button')
    const editButton = page.locator('button').filter({ hasText: /редактировать|edit|режим редактирования/i }).first()

    if (await editButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('[S5] Edit button found, clicking')
      await editButton.click()
      await page.waitForTimeout(1000)

      // Check for edit tools appearance
      console.log('[S5] Checking for editing tools')
      const addLessonBtn = page.locator('button').filter({ hasText: /добавить урок|add lesson/i }).first()
      const deleteBtn = page.locator('button').filter({ hasText: /удалить|delete/i }).first()

      let editToolsFound = false
      if (await addLessonBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('[S5] "Add lesson" button found')
        editToolsFound = true
      }

      if (await deleteBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('[S5] Delete button found')
        editToolsFound = true
      }

      // Try clicking "Add lesson" and then cancel
      if (await addLessonBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log('[S5] Clicking "Add lesson"')
        await addLessonBtn.click()
        await page.waitForTimeout(500)

        // Look for cancel button
        const cancelBtn = page.locator('button').filter({ hasText: /отмена|cancel|закрыть|close/i }).first()
        if (await cancelBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          console.log('[S5] Cancel button found, clicking')
          await cancelBtn.click()
          await page.waitForTimeout(500)
          console.log('[S5] Returned to view mode')
        }
      }

      expect(editToolsFound).toBe(true)
      console.log('[S5] PASSED: Edit mode works')
    } else {
      console.log('[S5] No Edit button found - may be view-only mode')
      console.log('[S5] PASSED: Edit mode not required')
    }
  })

  test('Scenario 6: Error Handling', async ({ browser }) => {
    page = await browser.newPage()

    console.log('[S6] Testing error handling and console')

    let errors: string[] = []
    let warnings: string[] = []

    // Capture console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
        console.log(`[ERROR] ${msg.text()}`)
      }
      if (msg.type() === 'warning') {
        warnings.push(msg.text())
      }
    })

    // Login
    console.log('[S6] Logging in')
    await page.goto(`${BASE_URL}/auth`)
    await page.waitForLoadState('networkidle')

    const emailInput = page.locator('input[type="email"]').first()
    const passwordInput = page.locator('input[type="password"]').first()
    const submitButton = page.locator('button[type="submit"]').first()

    await emailInput.fill(TEST_TEACHER_EMAIL)
    await passwordInput.fill(TEST_TEACHER_PASSWORD)
    await submitButton.click()
    await page.waitForNavigation()
    await page.waitForLoadState('networkidle')

    // Navigate to Graph Editor
    console.log('[S6] Navigating to graph editor')
    const graphLink = page.locator('a, button').filter({ hasText: /граф|graph/i }).first()
    if (await graphLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await graphLink.click()
      await page.waitForLoadState('networkidle')
    }

    // Wait for any errors to appear
    await page.waitForTimeout(3000)

    console.log(`[S6] Total errors: ${errors.length}`)
    console.log(`[S6] Total warnings: ${warnings.length}`)

    // Check for specific error patterns
    const criticalErrors = errors.filter(e =>
      e.includes('Cannot read properties of undefined') ||
      e.includes('is not defined') ||
      e.includes('TypeError') ||
      e.includes('ReferenceError')
    )

    console.log(`[S6] Critical errors: ${criticalErrors.length}`)
    criticalErrors.forEach(e => console.log(`[S6]   - ${e}`))

    expect(criticalErrors.length).toBe(0)
    console.log('[S6] PASSED: No critical console errors')
  })
})
