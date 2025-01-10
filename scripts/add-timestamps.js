import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

function calculateTimestamp(words, wordsPerMinute) {
  const wordsPerSecond = wordsPerMinute / 60
  return Math.round(words / wordsPerSecond)
}

function isHeader(line) {
  return line.trim().startsWith('----') && line.trim().endsWith('----')
}

function addTimestampsToText(text, wordsPerMinute) {
  const words = text.trim().split(/\s+/)
  let result = ''
  let currentTime = 0
  let wordCount = 0
  
  for (let i = 0; i < words.length; i++) {
    wordCount++
    if (wordCount >= (wordsPerMinute / 60)) { // Add timestamp every second
      currentTime++
      result += `${words[i]} [${currentTime}s] `
      wordCount = 0
    } else {
      result += `${words[i]} `
    }
  }
  
  return result.trim()
}

function addTimestamps(content, wordsPerMinute) {
  const sections = content.split(/\n\n+/)
  
  return sections.map(section => {
    if (isHeader(section)) {
      return section // Return headers unchanged
    }
    
    return addTimestampsToText(section, wordsPerMinute)
  }).join('\n\n')
}

async function processAudioScript(deckId) {
  try {
    const baseDir = path.join(process.cwd(), 'decks', deckId, 'audio')
    const originalFile = path.join(baseDir, 'audio_script.md')
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
    const newFile = path.join(baseDir, `audio_script_${timestamp}.md`)

    if (!fs.existsSync(originalFile)) {
      console.error(`Could not find audio_script.md in ${baseDir}`)
      process.exit(1)
    }

    const content = await fs.promises.readFile(originalFile, 'utf8')
    const timestampedContent = addTimestamps(content, 178)
    await fs.promises.writeFile(newFile, timestampedContent)

    console.log(`Successfully created timestamped script: ${newFile}`)
  } catch (error) {
    console.error('Error processing audio script:', error)
    process.exit(1)
  }
}

const deckId = process.argv[2]

if (!deckId) {
  console.error('Please provide a deck ID')
  console.error('Usage: node add-timestamps.js DECK_ID')
  process.exit(1)
}

processAudioScript(deckId) 