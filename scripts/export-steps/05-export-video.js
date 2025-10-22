#!/usr/bin/env node

/**
 * Step 4: Export Video
 * Exports video using existing video export script
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
const testMode = process.argv.includes('--test');

if (!deckId) {
  console.error(chalk.red('Error: Deck ID required'));
  console.error('Usage: node 04-export-video.js <DECK_ID> [--test]');
  process.exit(1);
}

console.log(chalk.bold.cyan('\n🎥 Step 4: Video Export'));
console.log(chalk.gray('─'.repeat(60)));

const timeEstimate = testMode ? '2-3 minutes' : '15-25 minutes';
console.log(chalk.gray(`\nEstimated time: ${timeEstimate}`));
console.log(chalk.gray('This process will:'));
console.log(chalk.gray('  1. Check slide/script synchronization'));
console.log(chalk.gray('  2. Start Slidev server on port 3030'));
console.log(chalk.gray('  3. Record presentation with Playwright'));
console.log(chalk.gray('  4. Encode as MP4 with audio'));
console.log(chalk.gray('  5. Save to exports/videos/\n'));

async function checkSync() {
  console.log(chalk.bold('\n📊 Step 4.1: Checking Sync'));
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

async function exportVideo() {
  try {
    const testFlag = testMode ? '--test' : '';
    const command = `npm run export-video ${deckId}${testFlag ? ' -- ' + testFlag : ''}`;
    
    console.log(chalk.gray(`Running: ${command}\n`));
    
    const { stdout, stderr } = await execAsync(command, {
      cwd: projectRoot,
      maxBuffer: 10 * 1024 * 1024 // 10MB buffer for long output
    });
    
    if (stdout) console.log(stdout);
    if (stderr && !stderr.includes('DeprecationWarning')) console.error(stderr);
    
    // Parse JSON output from video export
    const jsonMatch = stdout.match(/--- VIDEO_EXPORT_JSON ---\n([\s\S]*?)\n--- END_VIDEO_EXPORT_JSON ---/);
    
    if (jsonMatch) {
      const videoInfo = JSON.parse(jsonMatch[1]);
      
      console.log(chalk.green('\n✔ Video export completed'));
      console.log(chalk.gray(`  File: ${videoInfo.filename}`));
      console.log(chalk.gray(`  Size: ${videoInfo.sizeMB} MB`));
      console.log(chalk.gray(`  Duration: ${videoInfo.durationMin} minutes`));
      console.log(chalk.gray(`  Path: ${videoInfo.path}\n`));
      
      // Output structured info for parsing
      console.log('--- VIDEO_STEP_COMPLETE ---');
      console.log(JSON.stringify({
        deckId: videoInfo.deckId,
        filename: videoInfo.filename,
        path: videoInfo.path,
        size: videoInfo.size,
        sizeMB: videoInfo.sizeMB,
        duration: videoInfo.duration,
        durationMin: videoInfo.durationMin,
        resolution: videoInfo.resolution,
        status: 'completed'
      }, null, 2));
      console.log('--- END_VIDEO_STEP_COMPLETE ---\n');
      
    } else {
      // Fallback: try to find the file manually
      const match = stdout.match(/([A-Z_]+_\d{3}\.mp4)/);
      if (match) {
        const videoFilename = match[1];
        const videoPath = path.join(projectRoot, 'exports', 'videos', videoFilename);
        
        if (await fs.pathExists(videoPath)) {
          const stats = await fs.stat(videoPath);
          const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
          
          console.log(chalk.green('\n✔ Video export completed'));
          console.log(chalk.gray(`  File: ${videoFilename}`));
          console.log(chalk.gray(`  Size: ${sizeMB} MB`));
          console.log(chalk.gray(`  Path: ${videoPath}\n`));
          
          console.log('--- VIDEO_STEP_COMPLETE ---');
          console.log(JSON.stringify({
            deckId,
            filename: videoFilename,
            path: videoPath,
            size: stats.size,
            sizeMB: parseFloat(sizeMB),
            status: 'completed'
          }, null, 2));
          console.log('--- END_VIDEO_STEP_COMPLETE ---\n');
        } else {
          throw new Error('Video file not found after export');
        }
      } else {
        throw new Error('Could not parse video export output');
      }
    }
  } catch (error) {
    console.error(chalk.red('\n✗ Video export failed:'), error.message);
    if (error.stdout) console.log(error.stdout);
    if (error.stderr) console.error(error.stderr);
    process.exit(1);
  }
}

async function run() {
  try {
    // Step 4.1: Check sync before video export
    const syncPassed = await checkSync();
    if (!syncPassed) {
      console.log(chalk.bold.red('\n' + '='.repeat(60)));
      console.log(chalk.bold.red('   VIDEO EXPORT ABORTED'));
      console.log(chalk.bold.red('='.repeat(60)));
      console.log(chalk.yellow('\nFix the sync issues and run this step again.\n'));
      process.exit(1);
    }
    
    // Step 4.2: Export video
    await exportVideo();
    
  } catch (error) {
    console.log(chalk.bold.red('\n' + '='.repeat(60)));
    console.log(chalk.bold.red('   ✗ VIDEO EXPORT FAILED'));
    console.log(chalk.bold.red('='.repeat(60) + '\n'));
    process.exit(1);
  }
}

run();

