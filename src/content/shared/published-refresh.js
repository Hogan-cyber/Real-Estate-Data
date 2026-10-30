export const PUBLIC_DASHBOARD_URL = 'https://hogan-cyber.github.io/Real-Estate-Data/';
export const SOURCE_UPDATE_URL = 'https://github.com/Hogan-cyber/Real-Estate-Data/actions/workflows/monthly.yml';

export function isIndependentRefresh(shell) {
  return shell?.snapshot?.id === 'dashboard:3baf4fae-0f91-4930-b641-f7d01c531691' && !shell.hosted;
}

// Read-only public check. Starting a source crawl requires authenticated GitHub Actions.
export async function checkPublishedRefresh({ location, generatedAt, fetcher = fetch }) {
  const currentUrl = new URL(location);
  if (currentUrl.protocol === 'file:') {
    const online = new URL(PUBLIC_DASHBOARD_URL);
    online.search = currentUrl.search;
    online.hash = currentUrl.hash;
    return { reloadUrl: online.href };
  }
  const response = await fetcher(new URL('data/refresh_status.json', currentUrl).href, {
    cache: 'no-store', signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error('Published status is unavailable');
  const status = await response.json();
  const checkedAt = Date.parse(status.checked_at);
  if (status.market !== 'HK' || !Number.isFinite(checkedAt) || !Array.isArray(status.source_status)) {
    throw new Error('Invalid published status');
  }
  if (!Number.isFinite(Date.parse(generatedAt)) || checkedAt > Date.parse(generatedAt)) {
    currentUrl.searchParams.set('_refresh', String(Date.now()));
    return { reloadUrl: currentUrl.href };
  }
  const date = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Hong_Kong', day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(generatedAt));
  const warning = status.source_status.some((source) => source.status !== 'Verified')
    ? ' Check Data & Updates for source warnings.' : '';
  return { message: `No newer published data is available. Displayed sources checked ${date} HKT.${warning}` };
}
