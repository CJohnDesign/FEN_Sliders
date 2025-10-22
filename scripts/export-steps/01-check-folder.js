#!/usr/bin/env node

/**
 * Step 1: Check/Prepare Google Drive Folder Info
 * Returns folder information for the agent to handle MCP calls
 */

import chalk from 'chalk';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const deckId = process.argv[2];

if (!deckId) {
  console.error(chalk.red('Error: Deck ID required'));
  console.error('Usage: node 01-check-folder.js <DECK_ID>');
  process.exit(1);
}

console.log(chalk.bold.cyan('\n📁 Step 1: Google Drive Folder Preparation'));
console.log(chalk.gray('─'.repeat(60)));

// Return the folder name that needs to be checked/created
const folderInfo = {
  deckId,
  folderName: deckId,
  parentFolder: 'FEN Decks', // Optional: parent folder to organize all decks
  status: 'pending_agent_action',
  instructions: [
    `1. Search for folder named "${deckId}" using mcp_Zapier_google_drive_find_a_folder`,
    `2. If not found, create it using mcp_Zapier_google_drive_create_folder`,
    `3. Return the folder ID for use in subsequent steps`
  ]
};

console.log(chalk.gray('\nFolder to check/create:'));
console.log(chalk.white(`  Name: ${folderInfo.folderName}`));
console.log(chalk.white(`  Parent: ${folderInfo.parentFolder}`));

console.log(chalk.yellow('\n⏸  Waiting for agent to handle folder check/creation...'));
console.log(chalk.gray('\nAgent should use Zapier MCP tools:'));
console.log(chalk.gray('  - mcp_Zapier_google_drive_find_a_folder'));
console.log(chalk.gray('  - mcp_Zapier_google_drive_create_folder (if needed)'));

// Output JSON for the agent to parse
console.log('\n--- FOLDER_INFO_JSON ---');
console.log(JSON.stringify(folderInfo, null, 2));
console.log('--- END_FOLDER_INFO_JSON ---\n');

process.exit(0);

