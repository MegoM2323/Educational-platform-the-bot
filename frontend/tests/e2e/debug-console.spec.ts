/**
 * Debug Console Errors - Capture full error details
 */

import { test } from '@playwright/test'

test('Capture all console errors', async ({ page }) => {
  const allLogs: any[] = []

  page.on('console', msg => {
    const log = {
      type: msg.type(),
      text: msg.text(),
      location: msg.location(),
    }
    allLogs.push(log)

    if (msg.type() === 'error') {
      console.log('\n=== CONSOLE ERROR ===')
      console.log('Type:', msg.type())
      console.log('Text:', msg.text())
      console.log('Location:', msg.location())
      console.log('=====================\n')
    }
  })

  page.on('pageerror', error => {
    console.log('\n=== PAGE ERROR ===')
    console.log('Message:', error.message)
    console.log('Stack:', error.stack)
    console.log('==================\n')
  })

  console.log('Navigating to homepage...')
  await page.goto('http://localhost:8080')

  // Wait for errors to appear
  await page.waitForTimeout(5000)

  console.log('\nTotal logs:', allLogs.length)
  console.log('Error logs:', allLogs.filter(l => l.type === 'error').length)

  // Take screenshot
  await page.screenshot({ path: '/tmp/debug-screenshot.png' })

  console.log('\nAll error logs:')
  allLogs.filter(l => l.type === 'error').forEach((log, i) => {
    console.log(`\nError ${i + 1}:`)
    console.log('  Text:', log.text)
    console.log('  Location:', log.location)
  })
})
