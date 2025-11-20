import { test as base } from '@playwright/test';

export const roles = {
  student: { email: process.env.E2E_STUDENT_EMAIL || 'test_student@example.com', password: process.env.E2E_STUDENT_PASSWORD || 'test123' },
  teacher: { email: process.env.E2E_TEACHER_EMAIL || 'test_teacher@example.com', password: process.env.E2E_TEACHER_PASSWORD || 'test123' },
  parent:  { email: process.env.E2E_PARENT_EMAIL  || 'test_parent@example.com',  password: process.env.E2E_PARENT_PASSWORD  || 'test123' },
  tutor:   { email: process.env.E2E_TUTOR_EMAIL   || 'test_tutor@example.com',   password: process.env.E2E_TUTOR_PASSWORD   || 'test123' },
};

export const test = base.extend<{ loginAs: (role: keyof typeof roles) => Promise<void>}>({
  loginAs: async ({ page, baseURL }, use) => {
    async function loginAs(role: keyof typeof roles) {
      const creds = roles[role];
      const resp = await page.request.post(`${process.env.VITE_DJANGO_API_URL || 'http://localhost:8000/api'}/auth/login/`, {
        data: { email: creds.email, password: creds.password },
      });
      if (!resp.ok()) throw new Error(`Login failed for ${role}: ${resp.status()}`);
      
      const data = await resp.json();
      const token = data.data.token;
      
      // Сначала переходим на страницу, чтобы localStorage был доступен
      await page.goto('/');
      
          // Устанавливаем токен в localStorage с правильными ключами
          await page.evaluate(({ token, email, role }) => {
            const userData = {
              id: 1,
              email: email,
              first_name: 'Test',
              last_name: 'User',
              role: role,
              role_display: role.charAt(0).toUpperCase() + role.slice(1),
              phone: '+79990000000',
              is_verified: true,
              date_joined: new Date().toISOString(),
              full_name: 'Test User'
            };
            
            // Сохраняем данные в формате, который ожидает secureStorage
            const now = Date.now();
            const ttl = 24 * 60 * 60 * 1000; // 24 часа
            
            // Формат SecureStorageItem
            const authTokenItem = {
              data: token,
              timestamp: now,
              expires: now + ttl
            };
            
            const userDataItem = {
              data: JSON.stringify(userData),
              timestamp: now,
              expires: now + ttl
            };
            
            const tokenExpiryItem = {
              data: (now + ttl).toString(),
              timestamp: now,
              expires: now + ttl
            };
            
            // Сохраняем как JSON (без шифрования для тестов)
            localStorage.setItem('bot_platform_auth_token', JSON.stringify(authTokenItem));
            localStorage.setItem('bot_platform_user_data', JSON.stringify(userDataItem));
            localStorage.setItem('bot_platform_token_expiry', JSON.stringify(tokenExpiryItem));
          }, { token, email: creds.email, role });
      
      await page.context().storageState({ path: `storage-${role}.json` });
    }
    await use(loginAs);
  }
});


