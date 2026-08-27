/**
 * Backup and restore for PulseHub state.
 *
 * Backs up `~/.pulsehub/` (state + archive) into a single tar.gz.
 * Restore unpacks it back.
 *
 * Uses system `tar` command (available on Linux, macOS, Git Bash on Windows).
 */

import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { execSync } from 'node:child_process'

const PULSEHUB_DIR = join(homedir(), '.pulsehub')

/**
 * Create a backup of `~/.pulsehub/` → `<output>.tar.gz`.
 */
export async function backup(outputPath?: string): Promise<{ path: string, sizeBytes: number }> {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  const path = outputPath ?? join(homedir(), `pulsehub-backup-${timestamp}.tar.gz`)

  if (!existsSync(PULSEHUB_DIR)) {
    throw new Error(`~/.pulsehub/ does not exist. Nothing to back up.`)
  }

  try {
    execSync(`tar -czf "${path}" -C "${homedir()}" .pulsehub`, {
      stdio: 'pipe',
      timeout: 60_000,
    })
    // Get file size (cross-platform: wc -c works on most systems)
    try {
      const sizeOutput = execSync(`wc -c < "${path}"`, { encoding: 'utf8' }).trim()
      return { path, sizeBytes: Number(sizeOutput) || 0 }
    }
    catch {
      return { path, sizeBytes: 0 }
    }
  }
  catch {
    throw new Error(
      `Backup requires 'tar' command. On Windows, use WSL or Git Bash.\n`
      + `Alternatively, manually copy ${PULSEHUB_DIR} to a safe location.`,
    )
  }
}

/**
 * Restore from a backup tar.gz → `~/.pulsehub/`.
 */
export async function restore(backupPath: string): Promise<void> {
  if (!existsSync(backupPath)) {
    throw new Error(`Backup file not found: ${backupPath}`)
  }

  try {
    execSync(`tar -xzf "${backupPath}" -C "${homedir()}"`, {
      stdio: 'pipe',
      timeout: 60_000,
    })
  }
  catch {
    throw new Error(
      `Restore requires 'tar' command. On Windows, use WSL or Git Bash.`,
    )
  }
}
