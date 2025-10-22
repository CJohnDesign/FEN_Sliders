#!/usr/bin/env node

/**
 * Step 2: Check/Prepare Google Docs Info
 * Returns docs information for the agent to handle MCP calls
 */

import chalk from 'chalk';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '../..');

const deckId = process.argv[2];
const folderId = process.argv[3]; // Optional: folder ID from step 1

if (!deckId) {
  console.error(chalk.red('Error: Deck ID required'));
  console.error('Usage: node 02-check-docs.js <DECK_ID> [FOLDER_ID]');
  process.exit(1);
}

console.log(chalk.bold.cyan('\n📄 Step 2: Google Docs Preparation'));
console.log(chalk.gray('─'.repeat(60)));

async function prepareDocs() {
  try {
    // Read local files
    const scriptPath = path.join(projectRoot, 'decks', deckId, 'audio', 'audio_script.md');
    const slidesPath = path.join(projectRoot, 'decks', deckId, 'slides.md');
    
    if (!await fs.pathExists(scriptPath) || !await fs.pathExists(slidesPath)) {
      console.error(chalk.red(`\n✗ Error: Missing local files for ${deckId}`));
      console.error(chalk.gray(`  Expected: ${scriptPath}`));
      console.error(chalk.gray(`  Expected: ${slidesPath}`));
      process.exit(1);
    }
    
    const scriptContent = await fs.readFile(scriptPath, 'utf-8');
    const slidesContent = await fs.readFile(slidesPath, 'utf-8');
    
    const docsInfo = {
      deckId,
      folderId: folderId || null,
      script: {
        name: `${deckId}-Script`,
        content: scriptContent,
        length: scriptContent.length,
        localPath: scriptPath
      },
      slides: {
        name: `${deckId}-Slides`,
        content: slidesContent,
        length: slidesContent.length,
        localPath: slidesPath
      },
      status: 'pending_agent_action',
      instructions: [
        `1. Search for document "${deckId}-Script" using mcp_Zapier_google_docs_find_a_document`,
        `2. If found, get content using mcp_Zapier_google_docs_get_document_content and compare`,
        `3. If not found or content differs, create/update using mcp_Zapier_google_docs_create_document_from_text`,
        `4. Repeat for "${deckId}-Slides" document`,
        `5. Optionally upload to Google Drive folder if folderId provided`
      ]
    };
    
    console.log(chalk.gray('\nDocuments to check/create:'));
    console.log(chalk.white(`  Script: ${docsInfo.script.name} (${docsInfo.script.length} chars)`));
    console.log(chalk.white(`  Slides: ${docsInfo.slides.name} (${docsInfo.slides.length} chars)`));
    
    if (folderId) {
      console.log(chalk.white(`  Folder ID: ${folderId}`));
    }
    
    console.log(chalk.yellow('\n⏸  Waiting for agent to handle docs check/creation...'));
    console.log(chalk.gray('\nAgent should use Zapier MCP tools:'));
    console.log(chalk.gray('  - mcp_Zapier_google_docs_find_a_document'));
    console.log(chalk.gray('  - mcp_Zapier_google_docs_get_document_content'));
    console.log(chalk.gray('  - mcp_Zapier_google_docs_create_document_from_text'));
    
    // Write content to temp files for agent to use
    const tempDir = path.join(projectRoot, 'temp', 'docs-export');
    await fs.ensureDir(tempDir);
    
    const tempScriptPath = path.join(tempDir, `${deckId}-script-temp.txt`);
    const tempSlidesPath = path.join(tempDir, `${deckId}-slides-temp.txt`);
    
    await fs.writeFile(tempScriptPath, scriptContent, 'utf-8');
    await fs.writeFile(tempSlidesPath, slidesContent, 'utf-8');
    
    // Output JSON for the agent to parse
    console.log('\n--- DOCS_INFO_JSON ---');
    const outputInfo = {
      ...docsInfo,
      script: { 
        ...docsInfo.script, 
        content: '[SEE_TEMP_FILE]',
        tempFilePath: tempScriptPath
      },
      slides: { 
        ...docsInfo.slides, 
        content: '[SEE_TEMP_FILE]',
        tempFilePath: tempSlidesPath
      }
    };
    console.log(JSON.stringify(outputInfo, null, 2));
    console.log('--- END_DOCS_INFO_JSON ---\n');
    
    console.log(chalk.gray('Note: Full content written to temp files for agent to use.\n'));
    console.log(chalk.gray(`  Script temp file: ${tempScriptPath}`));
    console.log(chalk.gray(`  Slides temp file: ${tempSlidesPath}\n`));
    
    process.exit(0);
  } catch (error) {
    console.error(chalk.red('\n✗ Error preparing docs:'), error.message);
    process.exit(1);
  }
}

prepareDocs();

