import test from 'node:test';
import assert from 'node:assert/strict';
import { checkPublishedRefresh, isIndependentRefresh, SOURCE_UPDATE_URL } from '../src/content/shared/published-refresh.js';

const generatedAt = '2026-10-27T06:35:15.049011+00:00';
const snapshot = { id: 'dashboard:3baf4fae-0f91-4930-b641-f7d01c531691', generatedAt };
const location = 'https://hogan-cyber.github.io/Real-Estate-Data/?tab=sales&t=filters#chart';
const status = (checked_at = generatedAt) => ({ market: 'HK', checked_at, source_status: [{ status: 'Verified' }] });
const response = (body, ok = true) => async () => ({ ok, json: async () => body });

test('independent refresh applies only to the standalone HK dashboard', () => {
  assert.equal(isIndependentRefresh({ snapshot, hosted: false }), true);
  assert.equal(isIndependentRefresh({ snapshot, hosted: true }), false);
  assert.equal(isIndependentRefresh({ snapshot: { id: 'other' } }), false);
  assert.equal(isIndependentRefresh(null), false);
  assert.equal(new URL(SOURCE_UPDATE_URL).hostname, 'github.com');
});
test('checks the public status without cache and does not invent a new refresh timestamp', async () => {
  const result = await checkPublishedRefresh({ location, generatedAt, fetcher: async (url, options) => {
    assert.equal(new URL(url).pathname, '/Real-Estate-Data/data/refresh_status.json');
    assert.equal(options.cache, 'no-store');
    return { ok: true, json: async () => status() };
  } });
  assert.equal(result.reloadUrl, undefined);
  assert.match(result.message, /No newer published data/);
  assert.match(result.message, /27 Oct 2026/);
});
test('newer publication reload preserves the selected tab, filters and anchor', async () => {
  const result = await checkPublishedRefresh({ location, generatedAt, fetcher: response(status('2026-10-30T01:00:00Z')) });
  const url = new URL(result.reloadUrl);
  assert.equal(url.origin, new URL(location).origin);
  assert.equal(url.searchParams.get('tab'), 'sales');
  assert.equal(url.searchParams.get('t'), 'filters');
  assert.equal(url.hash, '#chart');
  assert.ok(url.searchParams.get('_refresh'));
});
test('older publication never replaces a newer displayed snapshot', async () => {
  const result = await checkPublishedRefresh({ location, generatedAt, fetcher: response(status('2026-10-20T01:00:00Z')) });
  assert.equal(result.reloadUrl, undefined);
});
test('failed, malformed or unrelated public status is rejected', async () => {
  for (const fetcher of [response({}, false), response({}), response({ ...status(), market: 'US' }), response({ ...status(), checked_at: 'bad' }), async () => { throw new Error('offline'); }]) {
    await assert.rejects(checkPublishedRefresh({ location, generatedAt, fetcher }));
  }
});
test('source failures remain visible even when the website is current', async () => {
  const data = status(); data.source_status.push({ status: 'Failed' });
  const result = await checkPublishedRefresh({ location, generatedAt, fetcher: response(data) });
  assert.match(result.message, /Check Data & Updates for source warnings/);
});
test('offline copies open the public website without ChatGPT or a fetch', async () => {
  const result = await checkPublishedRefresh({ location: 'file:///tmp/dashboard.html?tab=sales', generatedAt, fetcher: () => { throw new Error('must not fetch'); } });
  assert.equal(new URL(result.reloadUrl).hostname, 'hogan-cyber.github.io');
  assert.equal(new URL(result.reloadUrl).searchParams.get('tab'), 'sales');
});
