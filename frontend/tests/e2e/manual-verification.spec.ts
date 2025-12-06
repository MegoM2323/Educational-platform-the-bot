/**
 * Manual Verification Test - Simple check for white screen bug
 */

import { test, expect } from '@playwright/test'

test('Manual verification - Check if page shows actual UI elements', async ({ page }) => {
  console.log('\n=== MANUAL VERIFICATION TEST ===\n')

  // Navigate to homepage
  await page.goto('http://localhost:8080')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(3000) // Give React time to render

  // Take screenshot
  await page.screenshot({ path: '/tmp/manual-homepage.png', fullPage: true })

  // Get body HTML to analyze
  const bodyHTML = await page.locator('body').innerHTML()
  console.log('Body HTML length:', bodyHTML.length)
  console.log('First 500 chars of HTML:', bodyHTML.substring(0, 500))

  // Check for React root
  const appDiv = await page.locator('#root').innerHTML()
  console.log('\n#root div HTML length:', appDiv.length)
  console.log('First 500 chars:', appDiv.substring(0, 500))

  // Check for visible elements
  const visibleElements = await page.locator('body *:visible').count()
  console.log('\nVisible elements count:', visibleElements)

  // Check specific UI elements
  const hasButton = await page.locator('button').count()
  const hasInput = await page.locator('input').count()
  const hasLink = await page.locator('a').count()
  const hasHeading = await page.locator('h1, h2, h3').count()

  console.log('\nUI Elements found:')
  console.log('  Buttons:', hasButton)
  console.log('  Inputs:', hasInput)
  console.log('  Links:', hasLink)
  console.log('  Headings:', hasHeading)

  // Navigate to /auth
  console.log('\n=== CHECKING /auth PAGE ===\n')
  await page.goto('http://localhost:8080/auth')
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(3000)

  await page.screenshot({ path: '/tmp/manual-auth.png', fullPage: true })

  const authHTML = await page.locator('#root').innerHTML()
  console.log('/auth #root HTML length:', authHTML.length)
  console.log('First 500 chars:', authHTML.substring(0, 500))

  const authButtons = await page.locator('button').count()
  const authInputs = await page.locator('input').count()
  console.log('\n/auth UI Elements:')
  console.log('  Buttons:', authButtons)
  console.log('  Inputs:', authInputs)

  // Check if ProtectedRoute is redirecting
  const currentURL = page.url()
  console.log('\nCurrent URL:', currentURL)

  console.log('\n=== TEST COMPLETE ===\n')
})
