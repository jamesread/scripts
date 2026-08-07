import path from 'node:path'
import { createRequire } from 'node:module'
import { existsSync } from 'node:fs'

const frontend = process.env.JWRAPP_FRONTEND
if (!frontend) {
  throw new Error('jwrapp: JWRAPP_FRONTEND must point at the frontend directory')
}

const require = createRequire(path.join(frontend, 'package.json'))
const { mergeConfig, loadConfigFromFile } = require('vite')

const target = process.env.VITE_API_PROXY || 'http://127.0.0.1:8080'

const candidates = [
  'vite.config.js',
  'vite.config.mjs',
  'vite.config.ts',
  'vite.config.mts',
  'vite.config.cjs',
]

let configFile
for (const name of candidates) {
  const p = path.join(frontend, name)
  if (existsSync(p)) {
    configFile = p
    break
  }
}

if (!configFile) {
  throw new Error(`jwrapp: no vite.config.* found in ${frontend}`)
}

const loaded = await loadConfigFromFile(
  { command: 'serve', mode: 'development' },
  configFile,
)

const base = loaded?.config ?? {}
const proxy = { ...(base.server?.proxy ?? {}) }

for (const key of Object.keys(proxy)) {
  proxy[key] = {
    ...proxy[key],
    target,
    changeOrigin: true,
  }
}

if (Object.keys(proxy).length === 0) {
  proxy['/api'] = { target, changeOrigin: true }
}

// Always proxy production hashed bundles + upload/media to the Go backend.
// Vite's SPA middleware returns 404 for /assets/*.js when Sec-Fetch-Dest: script
// (common after a cached dist index.html or service worker on the same origin).
for (const path of ['/assets', '/upload', '/media', '/oauth2callback', '/mcp', '/llms.txt']) {
  if (!proxy[path]) {
    proxy[path] = { target, changeOrigin: true }
  }
}

export default mergeConfig(base, {
  server: { proxy },
})
