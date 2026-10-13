import { readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { SourceTextModule, SyntheticModule, createContext } from 'node:vm'
import assert from 'node:assert/strict'
import test from 'node:test'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { create } = require('zustand')
const source = await readFile(new URL('../services/api.ts', import.meta.url), 'utf8')
const compile = (code) => ts.transpileModule(code, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText
async function load(fetcher, tokens = { karpathys_token: 'access', karpathys_refresh_token: 'refresh' }) {
  const storage = new Map(Object.entries(tokens))
  const state = { user: { id: 'operator' }, cleared: 0,
    setUser(user, access, refresh) { storage.set('karpathys_token', access); storage.set('karpathys_refresh_token', refresh) },
    clearUser() { this.cleared++; storage.clear() } }
  const context = createContext({ fetch: fetcher, Headers, AbortSignal,
    localStorage: { getItem: (key) => storage.get(key) ?? null }, window: { location: { replace() {} } } })
  const compiledModule = new SourceTextModule(compile(source), { context })
  await compiledModule.link((name) => {
    if (name === '@/config/environment') return new SyntheticModule(['default'], function () {
      this.setExport('default', { apiUrl: 'https://api.example.invalid' })
    }, { context })
    if (name === '@/stores/auth.store') return new SyntheticModule(['useAuthStore'], function () {
      this.setExport('useAuthStore', { getState: () => state })
    }, { context })
    throw new Error('Unexpected dependency')
  })
  await compiledModule.evaluate()
  return { api: compiledModule.namespace.apiFetch, state }
}
for (const path of ['https://evil.invalid', 'http://evil.invalid', '//evil.invalid', '/\\evil.invalid']) {
  test(`deny bearer destination ${path}`, async () => {
    let requests = 0
    const { api } = await load(() => { requests++; throw new Error('network forbidden') })
    await assert.rejects(api(path), { status: 400 })
    assert.equal(requests, 0)
  })
}
for (const status of [400, 403, 404, 409, 429, 500, 502, 503]) {
  test(`HTTP ${status} remains failure`, async () => {
    const { api } = await load(async () => new Response('synthetic', { status }))
    await assert.rejects(api('/api/v1/leads'), { status })
  })
}
test('empty successful response', async () => {
  const { api } = await load(async () => new Response(null, { status: 204 }))
  assert.equal(await api('/api/v1/action'), undefined)
})
test('malformed successful JSON fails', async () => {
  const { api } = await load(async () => new Response('bad json'))
  await assert.rejects(api('/api/v1/leads'))
})
test('Headers, redirect rejection and bounded signal survive', async () => {
  const { api } = await load(async (url, options) => {
    assert.equal(url, 'https://api.example.invalid/api/v1/leads')
    assert.equal(options.headers.get('Authorization'), 'Bearer access')
    assert.equal(options.headers.get('X-Trace'), 'synthetic')
    assert.equal(options.redirect, 'error')
    assert.ok(options.signal instanceof AbortSignal)
    return new Response('{}')
  })
  await api('/api/v1/leads', { headers: new Headers({ 'X-Trace': 'synthetic' }) })
})
for (const concurrency of [20, 200]) test(`${concurrency} concurrent 401 requests use one refresh`, async () => {
  let refreshes = 0
  let accepted = 0
  const { api } = await load(async (url, options) => {
    if (url.endsWith('/auth/refresh')) {
      refreshes++
      await new Promise((resolve) => setImmediate(resolve))
      return new Response(JSON.stringify({ access_token: 'renewed', refresh_token: 'new-refresh' }))
    }
    if (options.headers.get('Authorization') === 'Bearer renewed') { accepted++; return new Response('{}') }
    return new Response('', { status: 401 })
  })
  await Promise.all(Array.from({ length: concurrency }, () => api('/api/v1/leads')))
  assert.equal(refreshes, 1)
  assert.equal(accepted, concurrency)
})
for (const fault of ['denied', 'network', 'missing']) {
  test(`refresh ${fault} releases all waiters`, async () => {
    const { api, state } = await load(async (url) => {
      if (url.endsWith('/auth/refresh')) {
        await new Promise((resolve) => setImmediate(resolve))
        if (fault === 'network') throw new Error('synthetic outage')
        return new Response('', { status: 403 })
      }
      return new Response('', { status: 401 })
    }, fault === 'missing' ? { karpathys_token: 'access' } : undefined)
    const results = await Promise.allSettled(Array.from({ length: 10 }, () => api('/api/v1/leads')))
    assert.ok(results.every((result) => result.status === 'rejected' && result.reason.status === 401))
    assert.ok(state.cleared > 0)
  })
}
test('real Zustand store resets session-specific evidence', async () => {
  const context = createContext({})
  const code = await readFile(new URL('../stores/sophia.store.ts', import.meta.url), 'utf8')
  const compiledModule = new SourceTextModule(compile(code), { context })
  await compiledModule.link(() => new SyntheticModule(['create'], function () { this.setExport('create', create) }, { context }))
  await compiledModule.evaluate()
  const store = compiledModule.namespace.useSophiaStore
  store.getState().setSessionId('a')
  store.getState().setSignals({ trust_score: 90 })
  store.getState().setContextPacket({ seller_name: 'Synthetic seller' })
  store.getState().setMode('human_takeover')
  store.getState().setSessionId('a')
  assert.equal(store.getState().signals.trust_score, 90)
  store.getState().setSessionId('b')
  assert.equal(store.getState().signals, null)
  assert.equal(store.getState().contextPacket, null)
  assert.equal(store.getState().mode, 'ai')
  store.getState().setSessionId(null)
  assert.equal(store.getState().sessionId, null)
})

test('account changes and logout clear conversation and approval identity', async () => {
  const storage = new Map()
  const context = createContext({ window: {}, localStorage: { setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) } })
  const modules = new Map()
  async function moduleFor(name) {
    if (modules.has(name)) return modules.get(name)
    if (name === 'zustand') return new SyntheticModule(['create'], function () { this.setExport('create', create) }, { context })
    const filename = name.replace('@/stores/', '')
    const code = await readFile(new URL(`../stores/${filename}.ts`, import.meta.url), 'utf8')
    const mod = new SourceTextModule(compile(code), { context })
    modules.set(name, mod)
    await mod.link(moduleFor)
    return mod
  }
  const mod = await moduleFor('@/stores/auth.store')
  await mod.evaluate()
  const auth = mod.namespace.useAuthStore
  const sophia = modules.get('@/stores/sophia.store').namespace.useSophiaStore
  const approvals = modules.get('@/stores/approval.store').namespace.useApprovalStore
  auth.getState().setUser({ id: 'one' }, 'token', 'refresh')
  sophia.getState().setSessionId('seller-one')
  approvals.getState().setPendingCount(3)
  auth.getState().setUser({ id: 'one' }, 'renewed', 'refresh')
  assert.equal(sophia.getState().sessionId, 'seller-one')
  auth.getState().setUser({ id: 'two' }, 'second', 'refresh')
  assert.equal(sophia.getState().sessionId, null)
  assert.equal(approvals.getState().pendingCount, 0)
  sophia.getState().setSessionId('seller-two')
  auth.getState().clearUser()
  assert.equal(sophia.getState().sessionId, null)
  assert.equal(auth.getState().status, 'unauthenticated')
  assert.equal(storage.size, 0)
})

async function loadSocket() {
  const sockets = []
  const timers = []
  class Socket {
    static OPEN = 1
    constructor(url) { this.url = url; sockets.push(this) }
    close() {}
  }
  const context = createContext({ URL, WebSocket: Socket, window: { location: { origin: 'https://dashboard.example.invalid', protocol: 'https:' } }, setTimeout: (fn) => { timers.push(fn); return timers.length }, clearTimeout() {} })
  const reconnect = new SourceTextModule(compile(await readFile(new URL('../lib/websocket/reconnect.ts', import.meta.url), 'utf8')), { context })
  await reconnect.link(() => { throw new Error('Unexpected dependency') })
  const client = new SourceTextModule(compile(await readFile(new URL('../lib/websocket/client.ts', import.meta.url), 'utf8')), { context })
  await client.link(() => reconnect)
  await client.evaluate()
  return { ...client.namespace, sockets, timers }
}
test('socket uses secure same origin and a ticket without JWT query', async () => {
  const { buildWsUrl } = await loadSocket()
  const url = new URL(buildWsUrl('', 'single-use-ticket'))
  assert.equal(url.origin, 'wss://dashboard.example.invalid')
  assert.equal(url.pathname, '/api/v1/realtime/ws')
  assert.equal(url.searchParams.get('ticket'), 'single-use-ticket')
  assert.equal(url.searchParams.has('token'), false)
  assert.throws(() => buildWsUrl('ws://insecure.example.invalid', 'ticket'))
  assert.throws(() => buildWsUrl('https://user:password@example.invalid', 'ticket'))
})
test('socket reconnect obtains a fresh ticket', async () => {
  const { WebSocketClient, sockets, timers } = await loadSocket()
  let requests = 0
  const client = new WebSocketClient(async () => `wss://example.invalid?ticket=${++requests}`, { onStatusChange() {}, onMessage() {} })
  client.connect()
  await new Promise(setImmediate)
  sockets[0].onclose({ code: 1006 })
  timers[0]()
  await new Promise(setImmediate)
  assert.equal(requests, 2)
  assert.notEqual(sockets[0].url, sockets[1].url)
  client.disconnect()
})
test('destroyed socket does not open after delayed ticket resolves', async () => {
  const { WebSocketClient, sockets } = await loadSocket()
  let resolve
  const client = new WebSocketClient(() => new Promise((done) => { resolve = done }), { onStatusChange() {}, onMessage() {} })
  client.connect()
  client.disconnect()
  resolve('wss://example.invalid?ticket=expired-session')
  await new Promise(setImmediate)
  assert.equal(sockets.length, 0)
})
