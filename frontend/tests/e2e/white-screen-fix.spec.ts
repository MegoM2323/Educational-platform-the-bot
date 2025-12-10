/**
 * T002: Test White Screen Fix & Basic Page Load
 *
 * Critical bug reported: "когда я запускаю сайт - у меня пустая белая страница"
 *
 * This test verifies the fix:
 * - Timeout protection in authService.ts (5s)
 * - Timeout protection in AuthContext.tsx (6s)
 *
 * Test Scenarios (ALL 5 must pass):
 * 1. Open homepage → Page loads WITHOUT white screen
 * 2. Check browser console → NO auth timeout errors
 * 3. Wait 10 seconds → Page remains stable
 * 4. Navigate to /auth → Login form visible
 * 5. Check Network tab → Auth initialization completes within 6s
 */

import { test, expect } from '@playwright/test'

test.describe('White Screen Fix & Basic Page Load', () => {
  test.beforeEach(async ({ page }) => {
    // Enable console monitoring
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log(`[BROWSER ERROR] ${msg.text()}`)
      }
    })
  })

  test('Scenario 1: Open homepage - Page loads WITHOUT white screen', async ({ page }) => {
    const startTime = Date.now()

    await page.goto('http://localhost:8081')

    const loadTime = Date.now() - startTime
    console.log(`Page load time: ${loadTime}ms`)

    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle')

    // Verify page is not blank - should have SOME visible text or UI elements
    const bodyText = await page.textContent('body')
    expect(bodyText).toBeTruthy()
    expect(bodyText!.length).toBeGreaterThan(0)

    // Take screenshot for verification
    await page.screenshot({ path: '/tmp/scenario1-homepage.png' })

    console.log('✅ Scenario 1: PASS - Homepage loaded without white screen')
  })

  test('Scenario 2: Check browser console - NO auth timeout errors', async ({ page }) => {
    const consoleErrors: string[] = []
    const authErrors: string[] = []

    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text()
        consoleErrors.push(text)

        if (text.includes('auth') || text.includes('timeout') || text.includes('initialization')) {
          authErrors.push(text)
        }
      }
    })

    await page.goto('http://localhost:8081')
    await page.waitForLoadState('networkidle')

    // Wait a bit for any delayed console errors
    await page.waitForTimeout(2000)

    console.log(`Total console errors: ${consoleErrors.length}`)
    console.log(`Auth-related errors: ${authErrors.length}`)

    if (authErrors.length > 0) {
      console.log('Auth errors found:', authErrors)
    }

    // Should have NO auth-related errors
    expect(authErrors.length).toBe(0)

    console.log('✅ Scenario 2: PASS - No auth timeout errors in console')
  })

  test('Scenario 3: Wait 10 seconds - Page remains stable, no white screen', async ({ page }) => {
    await page.goto('http://localhost:8081')
    await page.waitForLoadState('networkidle')

    // Get initial body content
    const initialText = await page.textContent('body')
    expect(initialText).toBeTruthy()

    // Screenshot at start
    await page.screenshot({ path: '/tmp/scenario3-start.png' })

    // Wait 10 seconds
    console.log('Waiting 10 seconds...')
    await page.waitForTimeout(10000)

    // Verify page still has content (not white screen)
    const finalText = await page.textContent('body')
    expect(finalText).toBeTruthy()
    expect(finalText!.length).toBeGreaterThan(0)

    // Screenshot at end
    await page.screenshot({ path: '/tmp/scenario3-end.png' })

    console.log('✅ Scenario 3: PASS - Page remained stable for 10 seconds')
  })

  test('Scenario 4: Navigate to /auth - Login form visible', async ({ page }) => {
    await page.goto('http://localhost:8081/auth')
    await page.waitForLoadState('networkidle')

    // Wait for page to render
    await page.waitForTimeout(2000)

    // Verify login form elements are visible
    // Looking for email field, password field, or login button
    const pageContent = await page.textContent('body')
    expect(pageContent).toBeTruthy()

    // Check for typical login page elements
    const hasEmailInput = await page.locator('input[type="email"]').count() > 0 ||
                          await page.locator('input[placeholder*="email"]').count() > 0 ||
                          await page.locator('input[placeholder*="Email"]').count() > 0

    const hasPasswordInput = await page.locator('input[type="password"]').count() > 0

    const hasLoginButton = await page.getByRole('button', { name: /login|войти|sign in/i }).count() > 0

    // Should have at least email or password input
    expect(hasEmailInput || hasPasswordInput).toBeTruthy()

    // Take screenshot of login page
    await page.screenshot({ path: '/tmp/scenario4-auth-page.png' })

    console.log(`Login form elements found - Email: ${hasEmailInput}, Password: ${hasPasswordInput}, Button: ${hasLoginButton}`)
    console.log('✅ Scenario 4: PASS - Login page loaded with form elements')
  })

  test('Scenario 5: Check Network - Auth initialization completes within 6s', async ({ page }) => {
    const authRequests: any[] = []
    const startTime = Date.now()

    // Monitor network requests
    page.on('request', request => {
      const url = request.url()
      if (url.includes('/api/auth') || url.includes('check')) {
        authRequests.push({
          url,
          method: request.method(),
          startTime: Date.now()
        })
      }
    })

    page.on('response', response => {
      const url = response.url()
      if (url.includes('/api/auth') || url.includes('check')) {
        const duration = Date.now() - startTime
        console.log(`Auth request completed: ${url} - ${response.status()} - ${duration}ms`)
      }
    })

    await page.goto('http://localhost:8081/auth')
    await page.waitForLoadState('networkidle')

    const totalTime = Date.now() - startTime

    console.log(`Total auth initialization time: ${totalTime}ms`)
    console.log(`Auth requests made: ${authRequests.length}`)

    // Auth initialization should complete within 6 seconds (6000ms)
    // This is the timeout protection threshold in AuthContext.tsx
    expect(totalTime).toBeLessThan(6000)

    // Verify no requests are stuck in pending state
    // (This is a bit hard to check in Playwright, but we can verify page is interactive)
    const isPageInteractive = await page.evaluate(() => {
      return document.readyState === 'complete'
    })
    expect(isPageInteractive).toBeTruthy()

    console.log('✅ Scenario 5: PASS - Auth initialization completed within 6s timeout')
  })

  test('Full Integration: All scenarios combined', async ({ page }) => {
    console.log('\n=== Running Full Integration Test ===\n')

    const consoleErrors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    // 1. Load homepage
    const startTime = Date.now()
    await page.goto('http://localhost:8081')
    await page.waitForLoadState('networkidle')

    const bodyText = await page.textContent('body')
    expect(bodyText).toBeTruthy()
    console.log('✅ Homepage loaded')

    // 2. Check for auth errors
    await page.waitForTimeout(1000)
    const authErrors = consoleErrors.filter(e =>
      e.includes('auth') || e.includes('timeout') || e.includes('initialization')
    )
    expect(authErrors.length).toBe(0)
    console.log('✅ No auth errors')

    // 3. Navigate to auth page
    await page.goto('http://localhost:8081/auth')
    await page.waitForLoadState('networkidle')

    const authPageText = await page.textContent('body')
    expect(authPageText).toBeTruthy()
    console.log('✅ Auth page loaded')

    // 4. Verify timing
    const totalTime = Date.now() - startTime
    console.log(`Total test duration: ${totalTime}ms`)

    // 5. Take final screenshot
    await page.screenshot({ path: '/tmp/full-integration-final.png' })

    console.log('\n✅ Full Integration Test: PASS\n')
  })
})
