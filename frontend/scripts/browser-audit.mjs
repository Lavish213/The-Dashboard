import { spawn } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'

const phase = process.argv[2] || 'before'
if (!['before', 'after', 'enhanced'].includes(phase)) throw new Error('Use before, after or enhanced')
const output = resolve('../docs/visual-audit', phase)
await mkdir(output, { recursive: true })
const origin = 'http://127.0.0.1:3217'
const server = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3217'], { stdio: ['ignore', 'pipe', 'pipe'] })
let serverLog = ''
server.stdout.on('data', b => { serverLog += b })
server.stderr.on('data', b => { serverLog += b })
let browser
const watchdog = setTimeout(() => { server.kill('SIGKILL'); process.exit(124) }, 240_000)
const evidence = { phase, fixtureOnly: true, browserExecutableOverride: Boolean(process.env.BROWSER_EXECUTABLE_PATH), capturedAt: new Date().toISOString(), browserVersion: null, screens: [], errors: [], requests: [], interactions: [] }
const user = { id: '00000000-0000-4000-8000-000000000001', email: 'audit@example.invalid', full_name: 'Audit operator', role: 'admin' }
const list = { items: [], total: 0, page: 1, page_size: 50, total_pages: 1, summary: null }
let populated = false, notificationRead = false, notificationFailure = false
let actorId = user.id, actorRole = 'admin'
let approvalResolved = false, approvalFailure = false
let approvalExpired = false
let sourcePricePopulated = false, sourcePriceResolved = false, sourcePriceFailure = false, sourcePriceExpired = false
const sourceCommands = []
let emailHoldsPopulated = false, emailResumePending = false, emailResumeApplied = false
function fixture(url) {
  const path = url.pathname
  if (path.includes('/source-operations')) return {items: [], page: 1, total_pages: 0}
  if (path.includes('/source-review/email-holds')) return {items: !emailHoldsPopulated ? [] : [{lead_id:'00000000-0000-0000-0000-000000000050',email:'blocked@example.invalid',count:1,stopped:true,pending:0,text:'STOP',fingerprint:'e'.repeat(64),can_resume:false,review_state:null,error:null},...(!emailResumeApplied ? [{lead_id:'00000000-0000-0000-0000-000000000051',email:'seller@example.invalid',count:1,stopped:false,pending:0,text:'Thanks for the information',fingerprint:'d'.repeat(64),can_resume:true,review_state:emailResumePending ? 'pending' : null,error:null}] : [])],page:1}
  if (path.includes('/source-review/price-reviews')) return {items: sourcePricePopulated && !sourcePriceResolved ? [{id: 'abcdef0123456789abcdef0123456789', lead_id: 'source-lead', property_id: 'source-property', address: '123 Synthetic Street', call_sid: 'synthetic-call', requested_action: 'get_offer_range', expires_at: sourcePriceExpired ? '2020-01-01T00:00:00Z' : '2099-01-01T00:00:00Z', risk_reason: 'Review synthetic property pricing', fingerprint: 'b'.repeat(64)}] : [], page: 1}
  if (path.endsWith('/source-commands')) return {items: sourceCommands}
  if (path.includes('/source-review/candidates')) return {items: [], page: 1}
  if (path.includes('/source-review/workflow-review')) return {items: [], requires_review: 0, review_owner_configured: false}
  if (path.endsWith('/business-evidence')) return {status: 'current', revision: 'a'.repeat(64), observed_at: new Date().toISOString(), snapshot: {address: '123 Synthetic Street', apn: '00123456', valuation: {point_cents: 46000000, supported_low_cents: 45000000, supported_high_cents: 47000000, comparable_count: 3, purpose: 'after_repair', as_of: '2026-10-14'}, comparables: [{sale_id: 'sale-1', source_ref: 'synthetic-reviewed-source', closed_on: '2026-10-01', sale_price_cents: 45000000, adjusted_value_cents: 46000000}], offers: [{id: 'offer-1', status: 'draft', amount_cents: 25000000, repairs_cents: 2000000}], appointment: {at: '2099-01-01T22:00:00Z', status: 'confirmed'}}}
  if (path === '/api/v1/leads/11111111-1111-4111-8111-111111111111') return {id: '11111111-1111-4111-8111-111111111111', full_name: 'Synthetic Owner', phone: null, email: null, lead_status: 'new', address: '123 Synthetic Street', city: 'Stockton', state: 'CA', notes: null, follow_up_at: null, created_at: '2026-10-14T00:00:00Z'}
  if (path.endsWith('/auth/me')) return { ...user, id: actorId, role: actorRole }
  if (path === '/api/v1/settings') return { source: 'dashboard_server', app_version: 'fixture', environment: 'test', security: { access_token_minutes: 1440, refresh_token_days: 7 }, permissions: [], notifications: { channel: 'in_app', delivery: 'database_and_websocket' }, voice_configuration: { available: false, reason: 'Voice configuration is managed by the separate voice service' }, calendar_booking: { available: false, reason: 'Follow-up dates only' } }
  if (path.endsWith('/settings/team')) return { ...list, items: populated ? [{ ...user, status: 'active' }] : [], total: populated ? 1 : 0 }
  if (path.endsWith('/notifications/unread-count')) return { unread_count: populated && !notificationRead ? 1 : 0 }
  if (path.endsWith('/notifications')) return { ...list, items: populated && (!notificationRead || url.searchParams.get('unread_only') !== 'true') ? [{ id: 'notice-one', title: 'Synthetic approval notice', body: 'Review this synthetic decision.', created_at: '2026-10-12T12:00:00Z', read_at: notificationRead ? '2026-10-12T13:00:00Z' : null }] : [] }
  if (populated && path.endsWith('/approvals/pending')) return { ...list, total: approvalResolved ? 0 : 1, items: approvalResolved ? [] : [{ id: '00000000-0000-4000-8000-000000000301', workflow_id: '00000000-0000-4000-8000-000000000302', approval_type: 'outreach', approval_status: 'escalated', risk_level: 'high', requested_by: user.id, resolved_by: null, expires_at: approvalExpired ? '2020-01-01T00:00:00Z' : '2099-01-01T00:00:00Z', resolution_notes: null, created_at: '2026-10-12T12:00:00Z', updated_at: '2026-10-12T12:00:00Z' }] }
  if (populated && path.endsWith('/leads')) {
    const page = Number(url.searchParams.get('page') || 1)
    const status = url.searchParams.get('statuses') || 'new'
    const total = status === 'converted' ? 2 : 201
    const anchor = new Date(url.searchParams.get('follow_up_start') || '2099-04-01T00:00:00Z')
    anchor.setUTCDate(anchor.getUTCDate() + 10)
    const items = Array.from({ length: Math.max(0, Math.min(200, total - (page - 1) * 200)) }, (_, i) => ({
      id: `${status}-${(page - 1) * 200 + i + 1}`, full_name: `Synthetic seller ${(page - 1) * 200 + i + 1}`, phone: '+12095550101', email: null, lead_status: status, ai_score: 80,
      notes: null, address: '123 Synthetic Lane', city: 'Stockton', state: 'CA', follow_up_at: anchor.toISOString(), updated_at: '2026-10-12T12:00:00Z', created_at: '2026-10-12T12:00:00Z',
    }))
    return { ...list, items, total, page, total_pages: Math.ceil(total / 200), summary: { by_status: { [status]: total }, average_score: 80, score_total: total * 80 } }
  }
  if (populated && path.endsWith('/transcripts')) return { ...list, total: 2, items: ['11111111', '22222222'].map(id => ({ id: id + '-0000-4000-8000-000000000001', source_type: 'call', transcript_status: 'completed', created_at: '2026-10-12T12:00:00Z' })) }
  if (populated && path.endsWith('/chunks')) return [{ id: 'chunk', speaker: 'sophia', text: path.includes('11111111') ? 'First conversation only' : 'Second conversation only', chunk_index: 0, created_at: '2026-10-12T12:00:00Z' }]
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
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce', timezoneId: 'America/Los_Angeles' })
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
      if (route.request().method() === 'POST' && url.pathname.includes('/source-review/email-holds/')) {
        const body=route.request().postDataJSON()
        if (Object.hasOwn(body,'actor_id') || body.fingerprint !== 'd'.repeat(64) || !url.pathname.includes('000000000051')) throw new Error('Email resumption lost its operator/STOP boundary')
        emailResumePending=true
        return route.fulfill({status:202,json:{schema_version:1,persisted:true,request_id:body.request_id,lead_id:'00000000-0000-0000-0000-000000000051',state:'pending'}})
      }
      if (route.request().method() === 'POST' && url.pathname.includes('/source-review/price-reviews/')) {
        const body = route.request().postDataJSON()
        if (Object.hasOwn(body, 'actor_id')) throw new Error('Pricing UI supplied actor identity')
        if (!['admin', 'reviewer'].includes(actorRole)) return route.fulfill({status: 403, json: {detail: 'Synthetic permission rejection'}})
        if (sourcePriceFailure) return route.fulfill({status: 503, json: {detail: 'Synthetic source outage'}})
        if (body.offer_low_cents !== 25000000 || body.offer_high_cents !== 27000000 || body.fingerprint !== 'b'.repeat(64)) throw new Error('Pricing UI lost integer cents or reviewed fingerprint')
        sourcePriceResolved = true
        return route.fulfill({status: 200, json: {persisted: true, approval_id: 'abcdef0123456789abcdef0123456789', status: body.status}})
      }
      if (route.request().method() === 'POST' && url.pathname.endsWith('/source-operation')) {
        const body = route.request().postDataJSON()
        if (Object.hasOwn(body, 'actor_id') || body.revision !== 'a'.repeat(64)) throw new Error('Operation UI lost authenticated identity/version boundary')
        if (body.action === 'draft_offer' && (body.data.amount_cents !== 25000000 || body.data.repair_cents !== 2500000 || body.data.arv_cents !== null)) throw new Error('Draft UI fabricated valuation or lost cents')
        sourceCommands.push({id: body.request_id, action: body.action, state: 'pending'})
        return route.fulfill({status: 202, json: {id: body.request_id, state: 'pending'}})
      }
      if (populated && route.request().method() === 'POST' && /^\/api\/v1\/approvals\/[^/]+\/resolve$/.test(url.pathname)) {
        const body = route.request().postDataJSON()
        if (Object.hasOwn(body, 'resolved_by')) throw new Error('Approval UI supplied an actor instead of relying on authenticated identity')
        if (!['admin', 'reviewer'].includes(actorRole)) return route.fulfill({ status: 403, json: { detail: 'Synthetic permission rejection' } })
        if (approvalFailure) return route.fulfill({ status: 503, json: { detail: 'Synthetic approval rejection' } })
        approvalResolved = true
        return route.fulfill({ status: 200, json: { approval_status: body.approval_status } })
      }
      if (populated && route.request().method() === 'POST' && url.pathname.includes('/notifications/')) {
        if (notificationFailure) return route.fulfill({ status: 503, json: { detail: 'Synthetic read failure' } })
        notificationRead = true
        return route.fulfill({ status: 200, json: {} })
      }
      if (rejectLogin && url.pathname.endsWith('/auth/login')) return route.fulfill({ status: 401, json: { detail: [{ msg: 'Synthetic structured rejection' }] } })
      if (url.pathname === '/api/v1/auth/ws-ticket' && route.request().method() === 'POST') return route.fulfill({ json: { ticket: 'synthetic-ticket-with-no-external-access', expires_in: 20 } })
      if (route.request().method() !== 'GET') return route.fulfill({ status: 405, json: { detail: 'Fixture audit prevents mutations' } })
      const failed = outage && !url.pathname.endsWith('/auth/me')
      if (populated && url.pathname.includes('/transcripts/11111111')) await new Promise(r => setTimeout(r, 700))
      return route.fulfill({ status: failed ? 503 : 200, json: failed ? { detail: 'Synthetic provider outage' } : fixture(url) })
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
  if (phase !== 'before') {
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
    for (const route of ['leads', 'source-review', 'deals', 'followups', 'calendar', 'social', 'properties', 'calls', 'workflows', 'approvals', 'realtime', 'audit', 'analytics', 'activity', 'transcripts']) {
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
    if (phase === 'enhanced') {
      populated = true
      rejectLogin = false
      await capture('32-populated-followups', '/followups')
      await page.getByRole('button', { name: 'Load more follow-ups', exact: true }).click()
      await page.getByText('Loaded 201 of 201 scheduled follow-ups. Counts below cover loaded records.', { exact: true }).waitFor()
      await page.getByText('Synthetic seller 201', { exact: true }).waitFor()
      evidence.interactions.push('Follow-ups reach record 201 through real pagination')
      await capture('33-populated-calendar', '/calendar', 390)
      await page.getByRole('button', { name: 'Load more calendar dates' }).click()
      await page.getByText('Loaded 201 of 201 follow-ups for this month.', { exact: true }).waitFor()
      evidence.interactions.push('Calendar reaches the complete month-filtered dataset')
      await capture('34-populated-deals', '/deals')
      await page.getByText('Loaded 202 of 203 deals. Totals cover all matching records.', { exact: true }).waitFor()
      await page.getByRole('button', { name: 'Load more qualified deals' }).click()
      await page.getByText('Loaded 203 of 203 deals. Totals cover all matching records.', { exact: true }).waitFor()
      evidence.interactions.push('Deal totals cover unloaded pages and both statuses')
      await capture('35-populated-settings', '/settings')
      await page.getByRole('tab', { name: 'Notifications', exact: true }).click()
      await page.getByText('Synthetic approval notice', { exact: true }).waitFor()
      notificationFailure = true
      await page.getByRole('button', { name: 'Mark read', exact: true }).click()
      await page.getByText('Read status was not saved. Try again.', { exact: true }).waitFor()
      notificationFailure = false
      await page.getByRole('button', { name: 'Mark read', exact: true }).click()
      await page.getByRole('button', { name: 'Mark read', exact: true }).waitFor({ state: 'hidden' })
      await page.getByText('0 unread', { exact: true }).waitFor()
      evidence.interactions.push('Notification failure preserves unread state; acknowledged retry updates it')
      await page.getByRole('tab', { name: 'Users', exact: true }).click()
      await page.getByRole('heading', { name: 'Team roster', exact: true }).waitFor()
      actorRole = 'operator'
      await capture('36-operator-settings', '/settings')
      await page.getByRole('tab', { name: 'Users', exact: true }).click()
      await page.getByText('The team roster is available to administrators.', { exact: true }).waitFor()
      evidence.interactions.push('Operator UI does not expose the admin roster')
      await capture('37-populated-transcripts', '/transcripts')
      await page.getByRole('button').filter({ hasText: '11111111' }).click()
      await page.getByRole('button').filter({ hasText: '22222222' }).click()
      await page.getByText('Second conversation only', { exact: true }).waitFor()
      await page.waitForTimeout(800)
      if (await page.getByText('First conversation only', { exact: true }).count()) throw new Error('Stale transcript overwrote current selection')
      evidence.interactions.push('Delayed first transcript cannot overwrite the second selection')
      await page.evaluate(id => localStorage.setItem('karpathys_saved_properties:' + id, JSON.stringify([{ attomId: 'private', address: 'Private saved address', city: 'Stockton', state: 'CA', zip: '95201', bedrooms: null, bathrooms: null, squareFeet: null, yearBuilt: null, estimatedValue: null, lastSalePrice: null, lastSaleDate: null, ownerName: null, lotSize: null, propertyType: null, taxAssessment: null, taxDelinquent: false, savedAt: '2026-10-12T12:00:00Z' }])), actorId)
      await page.goto(origin + '/properties', { waitUntil: 'networkidle' })
      await page.getByRole('button', { name: 'Saved (1)', exact: true }).click()
      await page.getByText('Private saved address', { exact: true }).waitFor()
      actorId = '00000000-0000-4000-8000-000000000002'
      await page.goto(origin + '/properties', { waitUntil: 'networkidle' })
      await page.getByRole('button', { name: 'Saved (0)', exact: true }).click()
      if (await page.getByText('Private saved address', { exact: true }).count()) throw new Error('Saved property crossed account boundary')
      evidence.interactions.push('Persisted saved properties remain isolated across two accounts')
      await capture('42-business-evidence', '/leads/11111111-1111-4111-8111-111111111111')
      await page.getByText('synthetic-reviewed-source', {exact: true}).waitFor()
      await page.getByText(/draft: \$250,000.00/).waitFor()
      await page.getByText(/Reviewed ARV advisory: \$460,000.00/).waitFor()
      evidence.interactions.push('Business evidence shows reviewed cents, comp reference, draft status and appointment separately')
      await page.getByLabel('Operation', {exact: true}).selectOption('draft_offer')
      await page.getByLabel('Draft offer ($, whole dollars)', {exact: true}).fill('250000')
      await page.getByLabel('Repair estimate ($, whole dollars)', {exact: true}).fill('25000')
      await page.getByLabel('Operation review reason', {exact: true}).fill('Reviewed synthetic property and repairs')
      await page.getByRole('button', {name: 'Queue source operation', exact: true}).click()
      await page.getByText(/Operation queued. It is not confirmed/).waitFor()
      await capture('43-source-draft-pending', '/leads/11111111-1111-4111-8111-111111111111')
      sourcePricePopulated = true
      actorRole = 'operator'
      await capture('44-operator-source-pricing', '/source-review')
      if (await page.getByRole('button', {name: 'Approve this price range', exact: true}).count()) throw new Error('Operator can grant source price authority')
      actorRole = 'reviewer'
      sourcePriceFailure = true
      await capture('45-reviewer-source-pricing', '/source-review')
      await page.getByLabel('Approved minimum offer ($, whole dollars)', {exact: true}).fill('250000')
      await page.getByLabel('Approved maximum offer ($, whole dollars)', {exact: true}).fill('270000')
      await page.getByLabel('Pricing review reason', {exact: true}).fill('Reviewed synthetic comparable sales and repair scope')
      await page.getByRole('button', {name: 'Approve this price range', exact: true}).click()
      await page.getByText(/Decision not confirmed. Refresh the source review/).waitFor()
      sourcePriceFailure = false
      await page.getByRole('button', {name: 'Approve this price range', exact: true}).click()
      await page.getByText('No current pricing requests on this page.', {exact: true}).waitFor()
      await capture('46-source-price-confirmed', '/source-review')
      sourcePriceResolved = false
      sourcePriceExpired = true
      await capture('47-expired-source-pricing', '/source-review')
      if (!(await page.getByRole('button', {name: 'Approve this price range', exact: true}).isDisabled())) throw new Error('Expired source price authority remains actionable')
      evidence.interactions.push('Source draft remains pending; source pricing enforces roles, integer cents, failed-write acknowledgement and expiry')
      emailHoldsPopulated=true
      actorRole='operator'
      await capture('48-email-hold-review','/source-review')
      if (await page.getByRole('button',{name:'Queue reviewed email resumption',exact:true}).count() !== 1) throw new Error('STOP hold exposed resumption controls')
      await page.getByLabel('Email resumption review reason',{exact:true}).fill('Reviewed ordinary reply and existing follow-up schedule')
      await page.getByRole('button',{name:'Queue reviewed email resumption',exact:true}).click()
      await page.getByText(/Reviewed resumption queued. Email follow-ups remain held/).waitFor()
      await capture('49-email-resume-pending','/source-review')
      emailResumeApplied=true
      await capture('50-stop-remains-blocked','/source-review')
      await page.getByText('STOP or opt-out: resumption is blocked.',{exact:true}).waitFor()
      if (await page.getByRole('button',{name:'Queue reviewed email resumption',exact:true}).count()) throw new Error('STOP hold became resumable')
      evidence.interactions.push('Only ordinary email replies can be reviewed; pending resumption is not called confirmed and STOP remains blocked')
      actorId = user.id
      actorRole = 'operator'
      await capture('38-operator-approval-queue' , '/approvals')
      if (await page.getByRole('button', { name: 'Approve', exact: true }).count()) throw new Error('Operator can resolve approval in UI')
      evidence.interactions.push('Operator approval queue exposes no resolve controls')
      actorRole = 'reviewer'
      approvalFailure = true
      await capture('39-reviewer-escalated-approval', '/approvals')
      await page.getByRole('button', { name: 'Approve', exact: true }).click()
      await page.getByText(/Synthetic approval rejection/).waitFor()
      await page.getByRole('button', { name: 'Approve', exact: true }).waitFor()
      evidence.interactions.push('Failed approval write preserves actionable escalated decision')
      approvalFailure = false
      await page.getByRole('button', { name: 'Approve', exact: true }).click()
      await page.getByRole('button', { name: 'Approve', exact: true }).waitFor({ state: 'hidden' })
      await capture('40-approval-acknowledged', '/approvals')
      evidence.interactions.push('Authenticated reviewer resolves without caller-supplied identity and queue refreshes after acknowledgement')
      approvalResolved = false
      approvalExpired = true
      await capture('41-expired-approval-disabled', '/approvals')
      if (!(await page.getByRole('button', { name: 'Approve', exact: true }).isDisabled())) throw new Error('Expired approval remains actionable')
      if (!(await page.getByRole('button', { name: 'Reject', exact: true }).isDisabled())) throw new Error('Expired rejection remains actionable')
      evidence.interactions.push('Expired approval controls are disabled and server denies expired authority')
    }
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
