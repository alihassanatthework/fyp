const path = require('path');
const { test, expect } = require('@playwright/test');

// Credentials — must exist in the database the backend is using (@15).
const EMAIL = 'ali@gmail.com';
const PASSWORD = 'ali@1234';
const FIXTURE = path.join(__dirname, '..', 'fixtures', 'test_skin.jpg');

test('login → upload → diagnosis', async ({ page }) => {
  // 1) Login
  await page.goto('/');
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button:has-text("Login")');

  // Redirects away from the login screen on success.
  await expect(page).not.toHaveURL(/login/i, { timeout: 15_000 });

  // 2) Go to skin analysis and upload a real face image.
  await page.goto('/analysis?type=skin');
  await page.setInputFiles('input[type="file"]', FIXTURE);

  // 3) Run analysis.
  await page.click('button:has-text("Analyse Now")');

  // 4) Assert a result appears (the EfficientNet chart on the diagnosis page).
  await expect(page.getByText(/EfficientNet/i)).toBeVisible({ timeout: 90_000 });
});
