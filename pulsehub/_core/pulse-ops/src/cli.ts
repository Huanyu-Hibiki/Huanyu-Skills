/**
 * CLI entrypoint for pulse-ops.
 *
 * Usage:
 *   pulsehub status              Show health dashboard
 *   pulsehub backup              Back up ~/.pulsehub/
 *   pulsehub restore <file>      Restore from backup
 *   pulsehub reset <platform>    Reset rate limit counter for a platform
 *   pulsehub resume <platform>   Resume a paused platform
 */

import { checkHealth } from './health.js'
import { backup, restore } from './backup.js'
import { resetPlatform, resetAll, getAllUsage } from './rate-limiter.js'
import { resume, getRecentEvents } from './anomaly.js'
import type { Platform } from '@pulsehub/types'

const VALID_PLATFORMS: Platform[] = ['bilibili', 'douyin', 'rednote', 'wechat_official', 'wechat_channels', 'zhihu']

async function main(): Promise<void> {
  const [command, ...args] = process.argv.slice(2)

  switch (command) {
    case 'status':
      return await cmdStatus()
    case 'backup':
      return await cmdBackup(args[0])
    case 'restore':
      return await cmdRestore(args[0])
    case 'reset':
      return cmdReset(args[0] as Platform)
    case 'resume':
      return cmdResume(args[0] as Platform)
    case 'limits':
      return cmdLimits()
    case 'help':
    case '--help':
    case '-h':
    case undefined:
      return printHelp()
    default:
      process.stderr.write(`Unknown command: ${command}\n`)
      printHelp()
      process.exit(1)
  }
}

// ─── Commands ──────────────────────────────────────────────────────────────

async function cmdStatus(): Promise<void> {
  process.stderr.write('Checking PulseHub health...\n\n')
  const report = await checkHealth()

  const statusIcon = report.overallStatus === 'healthy' ? '✅' : report.overallStatus === 'warning' ? '⚠️' : '❌'
  console.log(`${statusIcon}  PulseHub Status: ${report.overallStatus.toUpperCase()}`)
  console.log(`   ${report.timestamp}\n`)

  // Services
  console.log('─'.repeat(60))
  console.log('Services:')
  for (const svc of report.services) {
    const icon = svc.status === 'up' ? '✅' : svc.status === 'degraded' ? '⚠️' : svc.status === 'down' ? '❌' : '—'
    const latency = svc.latencyMs ? ` (${svc.latencyMs}ms)` : ''
    console.log(`  ${icon} ${svc.name}: ${svc.status}${latency}`)
    if (svc.details) console.log(`     ${svc.details}`)
  }
  console.log('')

  // Platforms
  console.log('─'.repeat(60))
  console.log('Platforms:')
  for (const p of report.platforms) {
    const usageBar = renderBar(p.rateLimit.usagePercent)
    const pauseTag = p.paused ? ` ⛔ PAUSED (${p.pauseReason}, ${p.pauseMinutesRemaining}min left)` : ''
    console.log(`  ${p.platform.padEnd(18)} ${usageBar} ${p.rateLimit.used}/${p.rateLimit.limit}${pauseTag}`)
  }
  console.log('')

  // Archive
  console.log('─'.repeat(60))
  console.log('Project Archive:')
  if (!report.archive.exists) {
    console.log('  ⚠️  No archive found (~/.pulsehub/archive/ missing)')
    console.log('     Run pulse-init to create one.')
  }
  else if (report.archive.projects.length === 0) {
    console.log('  ⚠️  Archive directory exists but no projects initialized')
  }
  else {
    for (const project of report.archive.projects) {
      const completeness = report.archive.completeness[project] ?? 0
      const icon = completeness === 100 ? '✅' : completeness >= 50 ? '⚠️' : '❌'
      const missing = report.archive.missing[project] ?? []
      console.log(`  ${icon} ${project}: ${completeness}% complete`)
      if (missing.length > 0) {
        console.log(`     Missing: ${missing.join(', ')}`)
      }
    }
  }
  console.log('')

  // Anomalies
  if (report.recentAnomalies > 0) {
    console.log('─'.repeat(60))
    console.log(`⚠️  ${report.recentAnomalies} anomalies in the last hour`)
    const events = getRecentEvents(5)
    for (const e of events) {
      console.log(`  ${e.timestamp} [${e.platform}] ${e.type}: ${e.details ?? ''}`)
    }
    console.log('')
  }
}

async function cmdBackup(output?: string): Promise<void> {
  process.stderr.write('Backing up ~/.pulsehub/...\n')
  try {
    const result = await backup(output)
    console.log(`✅ Backup created: ${result.path}`)
    if (result.sizeBytes > 0) {
      console.log(`   Size: ${(result.sizeBytes / 1024).toFixed(1)} KB`)
    }
  }
  catch (error) {
    process.stderr.write(`❌ Backup failed: ${error instanceof Error ? error.message : error}\n`)
    process.exit(1)
  }
}

async function cmdRestore(file?: string): Promise<void> {
  if (!file) {
    process.stderr.write('Usage: pulsehub restore <backup-file.tar.gz>\n')
    process.exit(1)
  }
  process.stderr.write(`Restoring from ${file}...\n`)
  try {
    await restore(file)
    console.log('✅ Restore complete. ~/.pulsehub/ updated.')
  }
  catch (error) {
    process.stderr.write(`❌ Restore failed: ${error instanceof Error ? error.message : error}\n`)
    process.exit(1)
  }
}

function cmdReset(platform?: Platform): void {
  if (!platform) {
    resetAll()
    console.log('✅ All rate limit counters reset.')
    return
  }
  if (!VALID_PLATFORMS.includes(platform)) {
    process.stderr.write(`Invalid platform: ${platform}\nValid: ${VALID_PLATFORMS.join(', ')}\n`)
    process.exit(1)
  }
  resetPlatform(platform)
  console.log(`✅ Rate limit counter reset for ${platform}.`)
}

function cmdResume(platform?: Platform): void {
  if (!platform || !VALID_PLATFORMS.includes(platform)) {
    process.stderr.write(`Usage: pulsehub resume <platform>\nValid: ${VALID_PLATFORMS.join(', ')}\n`)
    process.exit(1)
  }
  resume(platform)
  console.log(`✅ ${platform} resumed (anomaly pause cleared).`)
}

function cmdLimits(): void {
  const usage = getAllUsage()
  console.log('Daily Rate Limits:')
  for (const [platform, check] of Object.entries(usage)) {
    const bar = renderBar(check.used / check.limit * 100)
    console.log(`  ${platform.padEnd(18)} ${bar} ${check.used}/${check.limit} (remaining: ${check.remaining})`)
  }
}

function printHelp(): void {
  console.log(`
PulseHub Ops CLI

Usage:
  pulsehub status              Show health dashboard
  pulsehub backup [output]     Back up ~/.pulsehub/ to tar.gz
  pulsehub restore <file>      Restore from backup
  pulsehub reset [platform]    Reset rate limit (all or one platform)
  pulsehub resume <platform>   Clear anomaly pause for a platform
  pulsehub limits              Show rate limit usage only

Platforms:
  ${VALID_PLATFORMS.join(', ')}

Environment:
  PULSE_STATE_DIR      Override state directory (default: ~/.pulsehub/state)
  PULSE_ARCHIVE_DIR    Override archive directory (default: ~/.pulsehub/archive)
  RSSHUB_BASE_URL      Override RSSHub URL (default: http://localhost:1200)
  PULSE_LOG_LEVEL      debug | info | warn | error (default: info)
`)
}

function renderBar(percent: number): string {
  const width = 20
  const filled = Math.round((percent / 100) * width)
  const empty = width - filled
  const bar = '█'.repeat(filled) + '░'.repeat(empty)
  const pct = String(Math.round(percent)).padStart(3)
  return `${bar} ${pct}%`
}

main().catch((error) => {
  process.stderr.write(`Fatal: ${error instanceof Error ? error.message : error}\n`)
  process.exit(1)
})
