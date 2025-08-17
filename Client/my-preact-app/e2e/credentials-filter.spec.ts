import { test, expect } from '@playwright/test';

// Verifica que el modal de credenciales solicite las credenciales filtrando por chat_id

test('credentials modal filters by chat_id', async ({ page }) => {
  let requestedChat = '';
  await page.route('**/api/credentials*', route => {
    const url = new URL(route.request().url());
    requestedChat = url.searchParams.get('chat_id') || '';
    route.fulfill({ status: 200, body: '[]', headers: { 'Content-Type': 'application/json' } });
  });

  await page.goto('/#/chat/test-chat');
  await page.getByText('Credenciales').click();

  await expect.poll(() => requestedChat).toBe('test-chat');
});
