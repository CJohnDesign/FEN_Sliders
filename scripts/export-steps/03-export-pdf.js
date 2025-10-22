#!/usr/bin/env node

/**
 * Step 1: PDF Export
 * Exports PDF using Slidev's built-in export command
 * Handles server management internally to avoid EMFILE issues
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
  console.error('Usage: node 01-export-pdf.js <DECK_ID>');
  process.exit(1);
}

console.log(chalk.bold.cyan('\n📄 Step 1: PDF Export'));
console.log(chalk.gray('─'.repeat(60)));
console.log(chalk.gray('\nEstimated time: 30-60 seconds'));
console.log(chalk.gray('This process will:'));
console.log(chalk.gray('  1. Start Slidev export process'));
console.log(chalk.gray('  2. Export PDF with Playwright'));
console.log(chalk.gray('  3. Save to exports/ with auto-versioning'));
console.log(chalk.gray('  4. Clean up automatically\n'));

/**
 * Get next version number for PDF
 */
async function getNextVersion() {
  try {
    const exportsDir = path.join(projectRoot, 'exports');
    await fs.ensureDir(exportsDir);
    
    const files = await fs.readdir(exportsDir);
    const versionRegex = new RegExp(`^${deckId}_(\\d{3})\\.pdf$`);
    
    const versions = files
      .filter(file => versionRegex.test(file))
      .map(file => parseInt(file.match(versionRegex)[1]));
    
    const maxVersion = Math.max(0, ...versions);
    const nextVersion = String(maxVersion + 1).padStart(3, '0');
    
    return nextVersion;
  } catch (error) {
    return '001';
  }
}

/**
 * Main export function
 */
async function runExport() {
  try {
    // Step 1: Validate deck exists
    console.log(chalk.gray('[Step 1] Validating deck...'));
    const slidePath = path.join(projectRoot, 'decks', deckId, 'slides.md');
    if (!await fs.pathExists(slidePath)) {
      throw new Error(`Deck not found: ${slidePath}`);
    }
    console.log(chalk.green('✓ Deck validated'));
    
    // Step 2: Get version number
    console.log(chalk.gray('[Step 2] Getting version number...'));
    const version = await getNextVersion();
    const filename = `${deckId}_${version}.pdf`;
    const outputPath = path.join(projectRoot, 'exports', filename);
    console.log(chalk.gray(`Output: ${filename}`));
    
    // Step 3: Run Slidev export
    console.log(chalk.gray('[Step 3] Running Slidev PDF export...'));
    console.log(chalk.gray('This will start a temporary server and export the presentation\n'));
    
    const exportCommand = `npx slidev export "${slidePath}" --output "${outputPath}" --timeout 60000 --wait 3000`;
    
    console.log(chalk.gray(`Command: ${exportCommand}\n`));
    
    try {
      const { stdout, stderr } = await execAsync(exportCommand, {
        cwd: projectRoot,
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer
        timeout: 120000 // 2 minute timeout
      });
      
      // Show output
      if (stdout) {
        console.log(stdout);
      }
      
      // Filter out common warnings
      if (stderr && !stderr.includes('ExperimentalWarning') && !stderr.includes('punycode')) {
        console.error(chalk.yellow('Warnings:'), stderr);
      }
    } catch (error) {
      // If the command failed but might have produced output, check if file exists
      if (await fs.pathExists(outputPath)) {
        console.log(chalk.yellow('Export command had errors but PDF was created'));
      } else {
        throw error;
      }
    }
    
    // Step 4: Verify output
    console.log(chalk.gray('[Step 4] Verifying output...'));
    
    if (!await fs.pathExists(outputPath)) {
      throw new Error('PDF file was not created');
    }
    
    const stats = await fs.stat(outputPath);
    const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
    
    // Check if PDF is suspiciously small (likely blank)
    if (stats.size < 10000) { // Less than 10KB
      console.log(chalk.yellow('\n⚠️  Warning: PDF file is very small and may be blank'));
    }
    
    console.log(chalk.bold.green('\n✔ PDF export completed'));
    console.log(chalk.gray(`  File: ${filename}`));
    console.log(chalk.gray(`  Size: ${sizeMB} MB`));
    console.log(chalk.gray(`  Path: ${outputPath}\n`));
    
    // Output JSON for agent
    console.log('--- PDF_INFO_JSON ---');
    console.log(JSON.stringify({
      deckId,
      filename,
      path: outputPath,
      size: stats.size,
      sizeMB: parseFloat(sizeMB),
      status: 'completed'
    }, null, 2));
    console.log('--- END_PDF_INFO_JSON ---\n');
    
    process.exit(0);
  } catch (error) {
    console.error(chalk.red('\n✗ PDF export failed:'), error.message);
    
    if (error.code === 'ETIMEDOUT') {
      console.log(chalk.yellow('\nThe export timed out. This might happen with very long presentations.'));
      console.log(chalk.gray('Try increasing the timeout or export the deck manually.'));
    }
    
    if (error.message.includes('EMFILE')) {
      console.log(chalk.yellow('\nToo many files open error detected.'));
      console.log(chalk.gray('This is a system limit issue. You may need to:'));
      console.log(chalk.gray('  1. Close other applications'));
      console.log(chalk.gray('  2. Increase system file limits'));
      console.log(chalk.gray('  3. Restart your terminal'));
    }
    
    process.exit(1);
  }
}

runExport();
