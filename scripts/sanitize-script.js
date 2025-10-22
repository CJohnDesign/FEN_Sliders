#!/usr/bin/env node

/**
 * Sanitize Audio Script
 * 
 * Replaces forbidden words with acceptable alternatives before text-to-speech generation.
 * Preserves proper casing in replacements.
 * 
 * FORBIDDEN WORDS:
 * - "comprehensive" → "extensive" (never use comprehensive in any context)
 * 
 * Usage: node scripts/sanitize-script.js <deckId>
 */

import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import chalk from 'chalk';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

/**
 * Word replacements with case preservation
 * Format: [searchWord, replacementWord]
 */
const REPLACEMENTS = [
  ['comprehensive', 'extensive'],
  ['Comprehensive', 'Extensive'],
  ['COMPREHENSIVE', 'EXTENSIVE'],
];

/**
 * Sanitize text by replacing forbidden words
 */
function sanitizeText(text) {
  let sanitized = text;
  let changesMade = [];
  
  REPLACEMENTS.forEach(([search, replace]) => {
    const regex = new RegExp(search, 'g');
    const matches = text.match(regex);
    
    if (matches) {
      sanitized = sanitized.replace(regex, replace);
      changesMade.push({
        from: search,
        to: replace,
        count: matches.length
      });
    }
  });
  
  return { sanitized, changesMade };
}

/**
 * Main function
 */
async function main() {
  const deckId = process.argv[2];
  
  if (!deckId) {
    console.error(chalk.red('Error: Deck ID required'));
    console.error('Usage: node sanitize-script.js <DECK_ID>');
    process.exit(1);
  }
  
  const scriptPath = path.join(projectRoot, 'decks', deckId, 'audio', 'audio_script.md');
  
  console.log(chalk.bold.cyan('\n🧹 Sanitizing Audio Script'));
  console.log(chalk.gray('─'.repeat(60)));
  console.log(chalk.gray(`Deck: ${deckId}`));
  console.log(chalk.gray(`File: ${scriptPath}\n`));
  
  // Check if file exists
  if (!await fs.pathExists(scriptPath)) {
    console.error(chalk.red(`✗ Audio script not found: ${scriptPath}`));
    process.exit(1);
  }
  
  // Read file
  const originalContent = await fs.readFile(scriptPath, 'utf-8');
  
  // Sanitize
  const { sanitized, changesMade } = sanitizeText(originalContent);
  
  // Report changes
  if (changesMade.length === 0) {
    console.log(chalk.green('✔ No forbidden words found. Script is clean!\n'));
    process.exit(0);
  }
  
  console.log(chalk.yellow(`⚠️  Found forbidden words:\n`));
  
  let totalChanges = 0;
  changesMade.forEach(change => {
    console.log(chalk.gray(`  "${change.from}" → "${change.to}" (${change.count} occurrence${change.count > 1 ? 's' : ''})`));
    totalChanges += change.count;
  });
  
  console.log(chalk.yellow(`\n  Total replacements: ${totalChanges}\n`));
  
  // Write sanitized content back
  await fs.writeFile(scriptPath, sanitized, 'utf-8');
  
  console.log(chalk.green('✔ Audio script sanitized successfully!\n'));
  console.log(chalk.gray('The forbidden words have been replaced.'));
  console.log(chalk.gray('You can now proceed with audio generation.\n'));
  
  process.exit(0);
}

main().catch(error => {
  console.error(chalk.red('\n✗ Error:'), error.message);
  process.exit(1);
});

