/**
 * pulse-resolve CLI entrypoint.
 *
 * Usage:
 *   pulse-resolve <url>
 *   pulse-resolve --input urls.txt --output resolved.json
 *   echo "<url>" | pulse-resolve --stdin
 */

import { readFileSync, writeFileSync } from 'node:fs'
import { stdin } from 'node:process'
import type { ResolvedLink } from '@pulsehub/types'
import { resolveLink } from './resolvers/index.js'

interface CliOptions {
  input?: string
  output?: string
  stdin?: boolean
}

function parseArgs(argv: string[]): { urls: string[], options: CliOptions } {
  const urls: string[] = []
  const options: CliOptions = {}

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (arg === '--input') {
      options.input = argv[++i]
    }
    else if (arg === '--output') {
      options.output = argv[++i]
    }
    else if (arg === '--stdin') {
      options.stdin = true
    }
    else if (!arg.startsWith('--')) {
      urls.push(arg)
    }
  }

  return { urls, options }
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = []
  for await (const chunk of stdin) {
    chunks.push(chunk as Buffer)
  }
  return Buffer.concat(chunks).toString('utf8')
}

async function main(): Promise<void> {
  const { urls: argvUrls, options } = parseArgs(process.argv.slice(2))

  let urls = argvUrls

  if (options.stdin) {
    const text = await readStdin()
    urls = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  }
  else if (options.input) {
    const text = readFileSync(options.input, 'utf8')
    urls = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  }

  if (urls.length === 0) {
    console.error('Usage: pulse-resolve <url> [--input file] [--stdin] [--output file]')
    process.exit(1)
  }

  const results = await Promise.all(urls.map(url => resolveLink(url)))
  const resolved: ResolvedLink[] = []
  const failed: string[] = []

  results.forEach((result, index) => {
    if (result) {
      resolved.push(result)
    }
    else {
      failed.push(urls[index])
    }
  })

  const output = JSON.stringify(resolved, null, 2)

  if (options.output) {
    writeFileSync(options.output, output, 'utf8')
    console.error(`Wrote ${resolved.length} resolved links to ${options.output}`)
  }
  else {
    console.log(output)
  }

  if (failed.length > 0) {
    console.error(`\nFailed to resolve ${failed.length} URL(s):`)
    for (const url of failed) {
      console.error(`  ${url}`)
    }
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
