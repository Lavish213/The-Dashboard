import { spawn } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'

const phase = process.argv[2] || 'before'
if (!['before', 'after'].includes(phase)) throw new Error('Use before or after')
const output = resolve('../docs/visual-audit', phase)
await mkdir(output, { recursive: true })
const origin = 'http://127.0.0.1:3217'
const server = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3217'], { stdio: ['ignore', 'pipe', 'pipe'] })
let serverLog = ''
server.stdout.on('data', b => { serverLog += b })
server.stderr.on('data', b => { serverLog += b })
let browser
const watchdog = setTimeout(() => { server.kill('SIGKILL'); process.exit(124) }, 180_000)
const evidence = { phase, fixtureOnly: true, browserExecutableOverride: Boolean(process.env.BROWSER_EXECUTABLE_PATH), capturedAt: new Date().toISOString(), browserVersion: null, screens: [], errors: [], requests: [], interactions: [] }
const user = { id: '00000000-0000-4000-8000-000000000001', email: 'audit@example.invalid', full_name: 'Audit operator', role: 'admin' }
const list = { items: [], total: 0, page: 1, page_size: 50, total_pages: 1 }
function fixture(path) {
  if (path.endsWith('/auth/me')) return user
  if (path.endsWith('/analytics')) {
    if (path.includes('/social/')) return { total_posts: 8, posted: 3, total_leads_generated: 2, by_platform: { facebook: 4, instagram: 4 } }
    return { leads: { total: 42, by_status: { new: 14, contacted: 12, qualified: 10, converted: 6 } }, calls: { total: 120, completed: 96, no_answer: 12, voicemail: 6, failed: 6, contact_rate: 80, avg_duration_seconds: 165 }, workflows: { total: 24, active: 7, completed: 17, failed: 0 } }
  }
  if (path.endsWith('/realtime/active-call')) return { active: null, recent: [] }
  if (path.endsWith('/ready')) return { status: 'ready' }
  return list
}
try {
  for (let i = 0; i < 100; i++) {
    try { if ((await fetch(origin)).ok) break } catch {}
    if (i === 99) throw new Error('Next server not ready: ' + serverLog)
    await new Promise(r => setTimeout(r, 100))
  }
  browser = await chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH || undefined })
  evidence.browserVersion = browser.version()
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' })
  await context.addInitScript(() => {
    localStorage.setItem('karpathys_token', 'synthetic-audit-token')
    if (!localStorage.getItem('theme')) localStorage.setItem('theme', 'dark')
  })
  let outage = false
  let rejectLogin = false
  await context.route('**/*', async route => {
    const url = new URL(route.request().url())
    if (url.pathname.startsWith('/api/')) {
      evidence.requests.push({ method: route.request().method(), path: url.pathname, outage })
      if (rejectLogin && url.pathname.endsWith('/auth/login')) return route.fulfill({ status: 401, json: { detail: [{ msg: 'Synthetic structured rejection' }] } })
      if (route.request().method() !== 'GET') return route.fulfill({ status: 405, json: { detail: 'Fixture audit prevents mutations' } })
      const failed = outage && !url.pathname.endsWith('/auth/me')
      return route.fulfill({ status: failed ? 503 : 200, json: failed ? { detail: 'Synthetic provider outage' } : fixture(url.pathname) })
    }
    if (url.origin === origin) return route.continue()
    return route.abort('blockedbyclient')
  })
  const page = await context.newPage()
  page.setDefaultTimeout(6000)
  page.setDefaultNavigationTimeout(10000)
  page.on('pageerror', error => evidence.errors.push(error.message))
  async function capture(name, path, width = 1440, menu = false) {
    await page.setViewportSize({ width, height: width < 768 ? 844 : 1000 })
    await page.goto(origin + path, { waitUntil: 'networkidle' })
    await page.locator('h1').first().waitFor()
    if (outage) await page.waitForTimeout(2500)
    if (menu) await page.getByRole('button', { name: 'Open navigation menu' }).click()
    await page.screenshot({ path: resolve(output, name + '.png'), fullPage: true, animations: 'disabled' })
    const text = await page.locator('body').innerText()
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    const overflow = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth, main: document.querySelector('main')?.scrollWidth }))
    evidence.screens.push({ name, path, width, text, overflow, violations: axe.violations.map(v => ({ id: v.id, impact: v.impact, description: v.description, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) })) })
    console.log('Captured', name, 'axe:', axe.violations.length)
  }
  await capture('01-dashboard-desktop', '/dashboard')
  await capture('02-settings-desktop', '/settings')
  await capture('03-dashboard-mobile', '/dashboard', 390)
  await capture('04-mobile-menu', '/dashboard', 390, true)
  await capture('05-settings-mobile', '/settings', 390)
  outage = true
  await capture('06-dashboard-outage', '/dashboard')
  if (phase === 'after') {
    const idle = evidence.screens.find(s => s.name === '01-dashboard-desktop')
    if (idle.text.includes('AI Active')) throw new Error('Idle session falsely advertised active')
    const failed = evidence.screens.find(s => s.name === '06-dashboard-outage')
    if (!failed.text.includes('Social data unavailable')) throw new Error('Social outage not disclosed')
    const settings = evidence.screens.find(s => s.name === '02-settings-desktop')
    if (settings.text.includes('ElevenLabs') || settings.text.includes('Auto-confirm appointments')) throw new Error('Unverified settings remain')
    outage = false
    await page.goto(origin + '/settings', { waitUntil: 'networkidle' })
    await page.getByRole('tab', { name: 'Users', exact: true }).click()
    await page.getByText(user.email, { exact: true }).waitFor()
    evidence.interactions.push('Settings displays authenticated account')
    await page.getByRole('tab', { name: 'Security', exact: true }).click()
    await page.getByRole('link', { name: 'Open audit log', exact: true }).click()
    await page.waitForURL('**/audit')
    evidence.interactions.push('Security audit destination')
    await page.goto(origin + '/dashboard', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Collapse sidebar' }).click()
    await page.getByRole('button', { name: 'Expand sidebar' }).click()
    evidence.interactions.push('Sidebar collapses and expands')
    await page.getByRole('button', { name: 'Open command palette' }).click()
    await page.getByRole('dialog').waitFor()
    await page.keyboard.press('Escape')
    evidence.interactions.push('Command palette opens and dismisses')
    await page.getByRole('button', { name: 'Switch to light mode' }).click()
    await capture('07-dashboard-light', '/dashboard')
    await page.getByRole('button', { name: 'Switch to dark mode' }).click()
    for (const route of ['leads', 'deals', 'followups', 'calendar', 'social', 'properties', 'calls', 'workflows', 'approvals', 'realtime', 'audit', 'analytics', 'activity', 'transcripts']) {
      await capture('route-' + route, '/' + route)
    }
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(origin + '/dashboard', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Open navigation menu' }).click()
    await page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('link', { name: 'Calls', exact: true }).click()
    await page.waitForURL('**/calls')
    await page.getByRole('dialog').waitFor({ state: 'hidden' })
    evidence.interactions.push('Mobile navigation selects Calls and closes')
    for (const route of ['calendar', 'calls', 'leads', 'approvals']) await capture('mobile-' + route, '/' + route, 390)
    outage = true
    for (const route of ['analytics', 'transcripts', 'deals', 'followups', 'calendar', 'social']) {
      await capture('outage-' + route, '/' + route)
      if (!(await page.getByRole('alert').count())) throw new Error(route + ' failed without a visible alert')
    }
    outage = false
    await page.goto(origin + '/settings', { waitUntil: 'networkidle' })
    await page.getByRole('tab', { name: 'Users', exact: true }).click()
    await page.getByRole('button', { name: 'Sign out', exact: true }).click()
    await page.waitForURL('**/login')
    if (await page.evaluate(() => localStorage.getItem('karpathys_token'))) throw new Error('Logout retained token')
    evidence.interactions.push('Logout clears credentials and redirects to login')
    rejectLogin = true
    await page.getByLabel('Email', { exact: true }).fill(user.email)
    await page.getByLabel('Password', { exact: true }).fill('synthetic-test-only')
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await page.getByRole('alert').getByText('Login failed (401)', { exact: true }).waitFor()
    evidence.interactions.push('Structured sign-in rejection remains readable without crashing')
    const violations = evidence.screens.filter(s => s.violations.length)
    if (violations.length) throw new Error('Accessibility violations: ' + violations.map(s => s.name).join(', '))
    if (evidence.errors.length) throw new Error('Browser runtime errors: ' + evidence.errors.join('; '))
  }
} finally {
  await writeFile(resolve(output, 'evidence.json'), JSON.stringify(evidence, null, 2))
  await writeFile(resolve(output, 'server.log'), serverLog)
  await browser?.close()
  server.kill('SIGTERM')
  clearTimeout(watchdog)
}
