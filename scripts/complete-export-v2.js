#!/usr/bin/env node

/**
 * Complete Export Orchestrator V2
 * Runs export steps in sequence, pausing for agent to handle MCP calls
 */

import { Command } from 'commander';
import chalk from 'chalk';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

const program = new Command();

program
  .name('complete-export-v2')
  .description('Complete export workflow with agent orchestration')
  .version('2.0.0');

program
  .argument('<deckId>', 'Deck ID to export (e.g., FEN_STG)')
  .argument('[step]', 'Specific step to run (folder|docs|audio|video|all)', 'all')
  .option('--test', 'Test mode for video (60 seconds only)')
  .option('--regenerate-audio', 'Include audio regeneration')
  .option('--folder-id <id>', 'Folder ID from previous step')
  .action(async (deckId, step, options) => {
    try {
      await validateDeck(deckId);
      
      console.log(chalk.bold.cyan(`\n${'='.repeat(60)}`));
      console.log(chalk.bold.cyan(`   COMPLETE EXPORT V2: ${deckId}`));
      console.log(chalk.bold.cyan(`${'='.repeat(60)}\n`));
      
      // Run specific step or all steps
      switch(step) {
        case 'folder':
          await runStep('01-check-folder.js', [deckId]);
          break;
          
        case 'docs':
          await runStep('02-check-docs.js', [deckId, options.folderId || ''].filter(Boolean));
          break;
          
        case 'audio':
          await runStep('03-generate-audio.js', [deckId]);
          break;
          
        case 'video':
          const videoArgs = [deckId];
          if (options.test) videoArgs.push('--test');
          await runStep('04-export-video.js', videoArgs);
          break;
          
        case 'all':
          await runAllSteps(deckId, options);
          break;
          
        default:
          console.error(chalk.red(`Unknown step: ${step}`));
          console.error(chalk.gray('Valid steps: folder, docs, audio, video, all'));
          process.exit(1);
      }
      
    } catch (error) {
      console.error(chalk.red('\n✗ Export failed:'), error.message);
      process.exit(1);
    }
  });

async function runStep(scriptName, args = []) {
  const scriptPath = path.join(__dirname, 'export-steps', scriptName);
  const command = `node ${scriptPath} ${args.join(' ')}`;
  
  try {
    const { stdout, stderr } = await execAsync(command, {
      cwd: projectRoot,
      maxBuffer: 10 * 1024 * 1024
    });
    
    if (stdout) console.log(stdout);
    if (stderr && !stderr.includes('DeprecationWarning')) console.error(stderr);
    
    return { stdout, stderr };
  } catch (error) {
    if (error.stdout) console.log(error.stdout);
    if (error.stderr) console.error(error.stderr);
    throw error;
  }
}

async function runAllSteps(deckId, options) {
  console.log(chalk.bold.yellow('\n📋 RUNNING ALL STEPS'));
  console.log(chalk.gray('The agent will need to handle MCP calls between steps\n'));
  
  // Step 1: Folder
  console.log(chalk.bold('\n' + '='.repeat(60)));
  await runStep('01-check-folder.js', [deckId]);
  console.log(chalk.bold.yellow('\n⏸  PAUSED: Agent needs to handle folder MCP calls'));
  console.log(chalk.gray('After folder is ready, run: npm run complete-export-v2 ' + deckId + ' docs [--folder-id ID]\n'));
  
  // Note: In practice, the agent would handle MCP calls here and then continue
  // For now, we exit and let the agent orchestrate the next steps
  console.log(chalk.bold.cyan('\n' + '='.repeat(60)));
  console.log(chalk.bold.cyan('   NEXT: Agent should handle folder creation'));
  console.log(chalk.bold.cyan('   THEN: Run docs step'));
  console.log(chalk.bold.cyan('='.repeat(60) + '\n'));
}

async function validateDeck(deckId) {
  const deckPath = path.join(projectRoot, 'decks', deckId);
  const slidesPath = path.join(deckPath, 'slides.md');
  
  if (!await fs.pathExists(slidesPath)) {
    throw new Error(
      `Deck not found: ${deckId}\n` +
      `Expected: ${slidesPath}`
    );
  }
  
  return true;
}

program.parse();

