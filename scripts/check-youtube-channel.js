#!/usr/bin/env node

/**
 * Check which YouTube channel you're authenticated as
 * Use this to verify you're uploading to the correct channel (e.g., FirstEnroll)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { google } from 'googleapis';
import chalk from 'chalk';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.join(__dirname, '..');

const TOKEN_PATH = path.join(projectRoot, 'token.json');

/**
 * Load saved credentials
 */
async function loadSavedCredentialsIfExist() {
  try {
    const content = fs.readFileSync(TOKEN_PATH, 'utf-8');
    const credentials = JSON.parse(content);
    return google.auth.fromJSON(credentials);
  } catch (err) {
    return null;
  }
}

/**
 * Main function
 */
async function main() {
  console.log(chalk.bold.cyan('\n📺 YouTube Channel Check'));
  console.log(chalk.gray('─'.repeat(60)));
  
  try {
    // Load credentials
    const auth = await loadSavedCredentialsIfExist();
    
    if (!auth) {
      console.log(chalk.red('\n❌ No authentication token found!'));
      console.log(chalk.gray('\nYou need to authenticate first:'));
      console.log(chalk.gray('  rm token.json'));
      console.log(chalk.gray('  node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos"'));
      process.exit(1);
    }
    
    const youtube = google.youtube({ version: 'v3', auth });
    
    // Get list of channels for this user
    console.log(chalk.cyan('\nFetching your YouTube channels...\n'));
    
    const response = await youtube.channels.list({
      part: ['snippet', 'contentDetails', 'statistics'],
      mine: true,
    });
    
    if (!response.data.items || response.data.items.length === 0) {
      console.log(chalk.yellow('⚠️  No YouTube channels found for this account'));
      console.log(chalk.gray('\nThis Google account may not have a YouTube channel.'));
      console.log(chalk.gray('Make sure you\'re authenticated with the correct Google account.'));
      process.exit(1);
    }
    
    console.log(chalk.green(`✔ Found ${response.data.items.length} channel(s):\n`));
    
    response.data.items.forEach((channel, index) => {
      console.log(chalk.bold(`${index + 1}. ${channel.snippet.title}`));
      console.log(chalk.gray(`   Channel ID: ${channel.id}`));
      console.log(chalk.gray(`   Custom URL: ${channel.snippet.customUrl || 'N/A'}`));
      console.log(chalk.gray(`   Subscribers: ${channel.statistics.subscriberCount || '0'}`));
      console.log(chalk.gray(`   Videos: ${channel.statistics.videoCount || '0'}`));
      console.log(chalk.cyan(`   View: https://www.youtube.com/channel/${channel.id}`));
      console.log();
    });
    
    // Highlight the default channel
    console.log(chalk.yellow('📌 The first channel listed is your default upload channel.'));
    console.log(chalk.gray('   Videos will be uploaded to: ') + chalk.bold(response.data.items[0].snippet.title));
    
    if (response.data.items[0].snippet.title.toLowerCase().includes('firstenroll')) {
      console.log(chalk.green('\n✔ You\'re authenticated as FirstEnroll! Ready to upload.'));
    } else {
      console.log(chalk.yellow('\n⚠️  You\'re NOT authenticated as FirstEnroll'));
      console.log(chalk.gray('\nTo switch to FirstEnroll:'));
      console.log(chalk.gray('  1. Go to https://studio.youtube.com/'));
      console.log(chalk.gray('  2. Click profile icon → Switch account → Select FirstEnroll'));
      console.log(chalk.gray('  3. Delete token.json'));
      console.log(chalk.gray('  4. Re-authenticate with: node scripts/google-docs-api.js FEN_STG --folder=FEN_STG --parent-folder="Product Videos"'));
    }
    
    console.log();
    
  } catch (error) {
    console.error(chalk.red('\n✗ Error:'), error.message);
    
    if (error.message.includes('insufficient') || error.message.includes('scope')) {
      console.error(chalk.yellow('\n⚠️  Missing YouTube permissions'));
      console.error(chalk.gray('You need to re-authenticate with YouTube scope:'));
      console.error(chalk.gray('  1. rm token.json'));
      console.error(chalk.gray('  2. Re-authenticate to get YouTube permissions'));
    }
    
    process.exit(1);
  }
}

main();

