import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createClient } from '@supabase/supabase-js';
import chalk from 'chalk';
import ora from 'ora';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

// Load Supabase config
const configPath = path.join(__dirname, 'youtube.config.js');
const config = (await import(configPath)).default;

const SUPABASE_URL = config.supabase.url;
const SUPABASE_KEY = config.supabase.anonKey;
const SUPABASE_BUCKET = 'pdfs';

async function getNextVersionNumber(deckId) {
  try {
    const files = await fs.readdir(path.join(projectRoot, 'Exports'));
    const versionRegex = new RegExp(`${deckId}_(\\d{3})\\.pdf$`);
    
    const versions = files
      .filter(file => versionRegex.test(file))
      .map(file => parseInt(file.match(versionRegex)[1]));
    
    const maxVersion = Math.max(0, ...versions);
    return String(maxVersion + 1).padStart(3, '0');
  } catch {
    return '001';
  }
}

async function uploadToSupabase(pdfPath, deckId, version) {
  const spinner = ora('Uploading PDF to Supabase...').start();
  
  try {
    if (SUPABASE_KEY === 'YOUR_SUPABASE_ANON_KEY_HERE') {
      spinner.fail('Supabase not configured!');
      console.error(chalk.red('Update scripts/youtube.config.js with your Supabase anon key'));
      return null;
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
    const fileBuffer = await fs.readFile(pdfPath);
    const fileName = `${deckId}_${version}.pdf`;
    const filePath = `${fileName}`;

    const { data, error } = await supabase.storage
      .from(SUPABASE_BUCKET)
      .upload(filePath, fileBuffer, {
        contentType: 'application/pdf',
        upsert: true
      });

    if (error) throw error;

    const { data: { publicUrl } } = supabase.storage
      .from(SUPABASE_BUCKET)
      .getPublicUrl(filePath);

    spinner.succeed('Uploaded to Supabase');
    console.log(chalk.cyan(`   URL: ${publicUrl}`));
    
    return { publicUrl, filePath };
  } catch (error) {
    spinner.fail('Upload failed');
    console.error(chalk.red('Error:'), error.message);
    return null;
  }
}

async function runDeckOperation() {
  const [operation, deckId] = process.argv.slice(2);
  
  if (!operation || !deckId) {
    console.error('Usage: node deck-operations.js <operation> <deckId>');
    console.error('Operations: dev, build, export, preview');
    process.exit(1);
  }

  const commands = {
    dev: `slidev decks/${deckId}/slides.md --open`,
    build: `slidev build decks/${deckId}/slides.md --out dist/${deckId}`,
    preview: `slidev decks/${deckId}/slides.md --remote`,
    export: async () => {
      const version = await getNextVersionNumber(deckId);
      return `slidev export decks/${deckId}/slides.md --output Exports/${deckId}_${version}.pdf`;
    }
  };

  try {
    const command = commands[operation];
    if (!command) {
      throw new Error(`Unknown operation: ${operation}`);
    }

    const finalCommand = typeof command === 'function' ? await command() : command;
    
    // Execute the command using the native Node.js exec
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);

    console.log(chalk.blue(`\n📄 Running: ${finalCommand}\n`));
    
    const { stdout, stderr } = await execAsync(finalCommand);
    
    if (stderr && !stderr.includes('ExperimentalWarning')) {
      console.error(chalk.yellow('Warnings:'), stderr);
    }
    
    console.log(chalk.green('✅ Export completed'));

    // If this was an export operation, upload to Supabase and provide Google Drive instructions
    if (operation === 'export') {
      const version = await getNextVersionNumber(deckId);
      const previousVersion = String(parseInt(version) - 1).padStart(3, '0');
      const pdfPath = path.join(projectRoot, 'Exports', `${deckId}_${previousVersion}.pdf`);
      
      // Upload to Supabase
      const uploadResult = await uploadToSupabase(pdfPath, deckId, previousVersion);
      
      if (uploadResult) {
        console.log(chalk.cyan('\n' + '═'.repeat(50)));
        console.log(chalk.cyan.bold('  📤 READY TO UPLOAD TO GOOGLE DRIVE'));
        console.log(chalk.cyan('═'.repeat(50)));
        console.log('Use the Zapier Google Drive MCP to upload:');
        console.log(chalk.white(`  PDF URL: ${uploadResult.publicUrl}`));
        console.log(chalk.white(`  File Name: ${deckId}_${previousVersion} (without .pdf extension)`));
        console.log(chalk.white(`  Folder: ${deckId} (in Product Videos)`));
        console.log(chalk.yellow('\n  ⚠️  Note: Do NOT include .pdf extension in filename - it will be added automatically'));
        console.log(chalk.cyan('═'.repeat(50) + '\n'));
      }
    }
  } catch (error) {
    console.error(chalk.red(`Error: ${error.message}`));
    process.exit(1);
  }
}

runDeckOperation(); 