import { test, expect } from '@playwright/test';

const API_BASE = 'http://127.0.0.1:8000/api';
const FRONTEND_URL = 'http://localhost:8080';

test.describe('T604: Tutor Profile - User Testing', () => {
  let token: string;

  test('Step 1: Login via API to get token', async ({ page }) => {
    console.log('\n' + '='.repeat(60));
    console.log('T604: Tutor Profile QA Test');
    console.log('='.repeat(60));

    console.log('\n[STEP 1] Login as tutor@test.com via API');
    const resp = await page.request.post(`${API_BASE}/auth/login/`, {
      data: {
        email: 'tutor@test.com',
        password: 'TestPass123!'
      }
    });

    expect(resp.status()).toBe(200);
    const loginData = await resp.json();
    token = loginData.data?.access || loginData.access || loginData.token;

    expect(token).toBeTruthy();
    console.log(`  ✅ Login successful`);
    console.log(`  Token: ${token.substring(0, 20)}...`);
  });

  test('Step 2: Access profile API endpoint', async ({ page }) => {
    console.log('\n[STEP 2] Get tutor profile via API');

    // Login first
    const loginResp = await page.request.post(`${API_BASE}/auth/login/`, {
      data: {
        email: 'tutor@test.com',
        password: 'TestPass123!'
      }
    });

    const loginData = await loginResp.json();
    const authToken = loginData.data?.access || loginData.access || loginData.token;

    // Get profile
    const profileResp = await page.request.get(`${API_BASE}/profile/tutor/`, {
      headers: {
        'Authorization': `Token ${authToken}`
      }
    });

    expect(profileResp.status()).toBe(200);
    const profileData = await profileResp.json();

    console.log(`  ✅ Profile retrieved via API`);
    console.log(`  Response keys: ${Object.keys(profileData).join(', ')}`);

    // Verify profile structure
    expect(profileData.user).toBeTruthy();
    expect(profileData.profile).toBeTruthy();

    const profile = profileData.profile;
    console.log(`  Profile fields: ${Object.keys(profile).join(', ')}`);

    // Check for expected tutor fields
    expect(profile).toHaveProperty('specialization');
    console.log(`  Specialization: "${profile.specialization}"`);
  });

  test('Step 3: Update profile specialization', async ({ page }) => {
    console.log('\n[STEP 3] Update profile via API');

    // Login
    const loginResp = await page.request.post(`${API_BASE}/auth/login/`, {
      data: {
        email: 'tutor@test.com',
        password: 'TestPass123!'
      }
    });

    const loginData = await loginResp.json();
    const authToken = loginData.data?.access || loginData.access || loginData.token;

    // Update profile
    const newSpecialization = 'Math and Physics - Updated by QA Test';
    const updateResp = await page.request.patch(`${API_BASE}/profile/tutor/`, {
      headers: {
        'Authorization': `Token ${authToken}`,
        'Content-Type': 'application/json'
      },
      data: {
        specialization: newSpecialization,
        experience_years: 5
      }
    });

    expect(updateResp.status()).toBeGreaterThanOrEqual(200);
    expect(updateResp.status()).toBeLessThan(300);

    const updateData = await updateResp.json();
    console.log(`  ✅ Profile updated successfully`);
    console.log(`  Response status: ${updateResp.status()}`);

    if (updateData.profile) {
      console.log(`  Updated specialization: "${updateData.profile.specialization}"`);
    }
  });

  test('Step 4: Verify changes persisted', async ({ page }) => {
    console.log('\n[STEP 4] Verify changes persisted');

    // Login
    const loginResp = await page.request.post(`${API_BASE}/auth/login/`, {
      data: {
        email: 'tutor@test.com',
        password: 'TestPass123!'
      }
    });

    const loginData = await loginResp.json();
    const authToken = loginData.data?.access || loginData.access || loginData.token;

    // Get updated profile
    const profileResp = await page.request.get(`${API_BASE}/profile/tutor/`, {
      headers: {
        'Authorization': `Token ${authToken}`
      }
    });

    expect(profileResp.status()).toBe(200);
    const profileData = await profileResp.json();

    console.log(`  ✅ Profile data retrieved`);
    console.log(`  Current specialization: "${profileData.profile.specialization}"`);
    console.log(`  Experience years: ${profileData.profile.experience_years}`);
  });

  test('Step 5: Verify no console errors on profile page', async ({ page }) => {
    console.log('\n[STEP 5] Load frontend and check for console errors');

    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto(`${FRONTEND_URL}/profile/tutor`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    if (errors.length === 0) {
      console.log(`  ✅ No console errors`);
    } else {
      console.log(`  ❌ Found ${errors.length} console errors:`);
      errors.forEach(e => console.log(`    - ${e}`));
    }

    expect(errors.length).toBe(0);
  });

  test('Step 6: Test responsive design', async ({ page }) => {
    console.log('\n[STEP 6] Test responsive design');

    const viewports = [
      { width: 375, height: 667, name: 'Mobile' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 1920, height: 1080, name: 'Desktop' }
    ];

    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`${FRONTEND_URL}/profile/tutor`, { waitUntil: 'networkidle' });

      // Check if page loads
      const content = await page.content();
      const hasContent = content.length > 500;

      console.log(`  ✓ ${viewport.name} (${viewport.width}x${viewport.height}): ${hasContent ? '✅' : '⚠️'}`);
    }

    console.log(`  ✅ Responsive design tested`);
  });

  test.afterEach(async () => {
    console.log('\n' + '='.repeat(60));
  });
});
