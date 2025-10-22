#!/usr/bin/env node

/**
 * Step 3: Generate Audio (Optional)
 * Checks sync, deletes old audio, then regenerates audio files from audio script
 */

import chalk from 'chalk';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs-extra';

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '../..');

const deckId = process.argv[2];

if (!deckId) {
  console.error(chalk.red('Error: Deck ID required'));
  console.error('Usage: node 03-generate-audio.js <DECK_ID>');
  process.exit(1);
}

console.log(chalk.bold.cyan('\n🎙️  Step 3: Audio Regeneration'));
console.log(chalk.gray('─'.repeat(60)));
console.log(chalk.yellow('\n⚠️  This will use ElevenLabs API and incur costs'));
console.log(chalk.gray(`Reading audio script from: decks/${deckId}/audio/audio_script.md\n`));

async function sanitizeScript() {
  console.log(chalk.bold('\n🧹 Step 3.1: Sanitizing Script'));
  console.log(chalk.gray('─'.repeat(60)));
  console.log(chalk.gray('Replacing forbidden words before text-to-speech generation...\n'));
  
  try {
    const { stdout, stderr } = await execAsync(
      `node scripts/sanitize-script.js ${deckId}`,
      { 
        cwd: projectRoot,
        maxBuffer: 10 * 1024 * 1024
      }
    );
    
    if (stdout) console.log(stdout);
    if (stderr && !stderr.includes('DeprecationWarning')) console.error(stderr);
    
    return true;
  } catch (error) {
    if (error.stdout) console.log(error.stdout);
    if (error.stderr && !error.stderr.includes('DeprecationWarning')) console.error(error.stderr);
    console.log(chalk.red('✗ Script sanitization failed!\n'));
    return false;
  }
}

async function checkSync() {
  console.log(chalk.bold('\n📊 Step 3.2: Checking Sync'));
  console.log(chalk.gray('─'.repeat(60)));
  console.log(chalk.gray('Running sync check to verify slides and script alignment...\n'));
  
  try {
    const { stdout, stderr } = await execAsync(
      `node scripts/deckSyncCounter.js ${deckId}`,
      { 
        cwd: projectRoot,
        maxBuffer: 10 * 1024 * 1024
      }
    );
    
    if (stdout) console.log(stdout);
    if (stderr && !stderr.includes('DeprecationWarning')) console.error(stderr);
    
    // Check if sync passed
    if (stdout.includes('✓') || stdout.includes('PASS') || !stdout.includes('ERROR')) {
      console.log(chalk.green('✔ Sync check passed!\n'));
      return true;
    } else {
      console.log(chalk.red('✗ Sync check failed!'));
      console.log(chalk.yellow('\n⚠️  Please fix the sync issues reported above and run again.\n'));
      return false;
    }
  } catch (error) {
    // If the script fails, show the error
    if (error.stdout) console.log(error.stdout);
    if (error.stderr) console.error(error.stderr);
    console.log(chalk.red('\n✗ Sync check failed!'));
    console.log(chalk.yellow('⚠️  Please fix the sync issues reported above and run again.\n'));
    return false;
  }
}

async function deleteOldAudio() {
  console.log(chalk.bold('\n🗑️  Step 3.3: Deleting Old Audio'));
  console.log(chalk.gray('─'.repeat(60)));
  
  const audioDir = path.join(projectRoot, 'decks', deckId, 'audio', 'oai');
  
  try {
    if (await fs.pathExists(audioDir)) {
      const files = await fs.readdir(audioDir);
      const mp3Files = files.filter(f => f.endsWith('.mp3'));
      
      if (mp3Files.length > 0) {
        console.log(chalk.gray(`Found ${mp3Files.length} audio file(s) to delete...\n`));
        
        for (const file of mp3Files) {
          await fs.remove(path.join(audioDir, file));
          console.log(chalk.gray(`  Deleted: ${file}`));
        }
        
        console.log(chalk.green('\n✔ Old audio files deleted\n'));
      } else {
        console.log(chalk.gray('No existing audio files to delete\n'));
      }
    } else {
      console.log(chalk.gray('Audio directory does not exist yet\n'));
    }
  } catch (error) {
    console.error(chalk.yellow(`⚠️  Warning: Could not delete old audio: ${error.message}\n`));
  }
}

async function generateAudio() {
  console.log(chalk.bold('\n🎵 Step 3.4: Generating New Audio'));
  console.log(chalk.gray('─'.repeat(60)));
  console.log(chalk.gray('Starting audio generation (this may take 2-5 minutes)...\n'));
  
  try {
    const { stdout, stderr } = await execAsync(
      `npm run generateAudio ${deckId}`,
      { 
        cwd: projectRoot,
        maxBuffer: 10 * 1024 * 1024 // 10MB buffer for long output
      }
    );
    
    if (stdout) console.log(stdout);
    if (stderr && !stderr.includes('DeprecationWarning')) console.error(stderr);
    
    console.log(chalk.green('\n✔ Audio regenerated successfully'));
    console.log(chalk.gray(`  Audio files saved to: decks/${deckId}/audio/oai/\n`));
    
    return true;
  } catch (error) {
    console.error(chalk.red('\n✗ Audio generation failed:'), error.message);
    if (error.stdout) console.log(error.stdout);
    if (error.stderr) console.error(error.stderr);
    throw error;
  }
}

async function run() {
  try {
    // Step 3.1: Sanitize script (replace forbidden words)
    await sanitizeScript();
    
    // Step 3.2: Check sync
    const syncPassed = await checkSync();
    if (!syncPassed) {
      console.log(chalk.bold.red('\n' + '='.repeat(60)));
      console.log(chalk.bold.red('   AUDIO GENERATION ABORTED'));
      console.log(chalk.bold.red('='.repeat(60)));
      console.log(chalk.yellow('\nFix the sync issues and run this step again.\n'));
      process.exit(1);
    }
    
    // Step 3.3: Delete old audio
    await deleteOldAudio();
    
    // Step 3.4: Generate new audio
    await generateAudio();
    
    console.log(chalk.bold.green('\n' + '='.repeat(60)));
    console.log(chalk.bold.green('   ✓ AUDIO REGENERATION COMPLETE'));
    console.log(chalk.bold.green('='.repeat(60) + '\n'));
    
    process.exit(0);
  } catch (error) {
    console.log(chalk.bold.red('\n' + '='.repeat(60)));
    console.log(chalk.bold.red('   ✗ AUDIO REGENERATION FAILED'));
    console.log(chalk.bold.red('='.repeat(60) + '\n'));
    process.exit(1);
  }
}

run();

