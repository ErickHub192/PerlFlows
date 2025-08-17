import { test, expect } from '@playwright/test';

test('mode toggle persists after reload', async ({ page }) => {
  await page.goto('/');

  const toggle = page.getByRole('checkbox', { name: /Workflows AI/i });
  await toggle.check();

  await page.reload();

  await expect(toggle).toBeChecked();
});
