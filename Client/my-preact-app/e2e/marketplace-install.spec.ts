import { test, expect } from '@playwright/test';

test('install template adds workflow', async ({ page }) => {
  await page.route('**/api/marketplace/templates', route => {
    route.fulfill({ status: 200, body: JSON.stringify([{ template_id: 't1', name: 'Demo', category: 'cat', description: 'd', spec_json: {}, created_at: '', updated_at: '' }]) });
  });
  let installed = false;
  await page.route('**/api/marketplace/install*', route => {
    installed = true;
    route.fulfill({ status: 200, body: JSON.stringify({ flow_id: 'f1', name: 'Demo', is_active: false, created_at: '', updated_at: '' }) });
  });
  await page.route('**/api/flows', route => {
    const flows = installed ? [{ flow_id: 'f1', name: 'Demo', is_active: false, created_at: '', updated_at: '' }] : [];
    route.fulfill({ status: 200, body: JSON.stringify(flows) });
  });

  await page.goto('/');
  await page.getByText('Marketplace').click();
  await page.getByRole('button', { name: 'Instalar' }).click();
  await expect(page.getByText('Plantilla instalada')).toBeVisible();
  await page.goto('/#/workflows');
  await expect(page.getByText('Demo')).toBeVisible();
});
