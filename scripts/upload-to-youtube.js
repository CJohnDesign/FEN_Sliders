#!/usr/bin/env node

/**
 * Upload videos to YouTube using Google API
 * Uses the same authentication as google-docs-api.js
 * 
 * Automatically extracts title from slides.md H1 heading
 * Uploads as unlisted, not made for kids
 * 
 * ⚠️ CURRENTLY BLOCKED:
 * This feature is fully implemented and ready to use, but currently blocked by:
 * - Limited FirstEnroll access (guest/contributor only, not admin)
 * - YouTube API upload requires channel management permissions
 * - Would require re-authenticating with FirstEnroll admin account
 * 
 * This script will remain in the codebase and can be activated when:
 * - Full admin access to FirstEnroll is granted, OR
 * - A FirstEnroll admin authenticates and shares the token
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { google } from 'googleapis';
import chalk from 'chalk';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.join(__dirname, '..');

// Scopes for YouTube API
const SCOPES = [
  'https://www.googleapis.com/auth/youtube.upload',
  'https://www.googleapis.com/auth/drive.file',
  'https://www.googleapis.com/auth/drive'
];

const TOKEN_PATH = path.join(projectRoot, 'token.json');
const CREDENTIALS_PATH = path.join(projectRoot, 'credentials.json');

/**
 * Load saved credentials if they exist
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
 * Authenticate with Google APIs
 */
async function authorize() {
  let client = await loadSavedCredentialsIfExist();
  if (client) {
    console.log(chalk.green('🔑 Using saved authentication token...'));
    return client;
  }
  
  console.log(chalk.red('\n❌ No authentication token found!'));
  console.log(chalk.yellow('\nYou need to re-authenticate with YouTube scope.'));
  console.log(chalk.gray('1. Delete token.json'));
  console.log(chalk.gray('2. Run any Google Docs/Drive script to re-authenticate'));
  console.log(chalk.gray('3. Make sure YouTube Data API v3 is enabled in GCP\n'));
  process.exit(1);
}

/**
 * Extract H1 title and subtitle from slides.md
 */
function extractMetadataFromSlides(deckId) {
  try {
    const slidesPath = path.join(projectRoot, 'decks', deckId, 'slides.md');
    const content = fs.readFileSync(slidesPath, 'utf-8');
    const lines = content.split('\n');
    
    let title = deckId;
    let description = '';
    
    // Find first H1 heading (# Title)
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      if (line.match(/^#\s+.+$/)) {
        // Extract title (remove # and trim)
        title = line.replace(/^#\s+/, '').trim();
        
        // Look for subtitle in next non-empty lines (skip blank lines and components)
        for (let j = i + 1; j < lines.length && j < i + 5; j++) {
          const nextLine = lines[j].trim();
          // Skip empty lines and Vue components
          if (nextLine && !nextLine.startsWith('<') && !nextLine.startsWith('---')) {
            // Remove markdown bold markers
            description = nextLine.replace(/\*\*/g, '').trim();
            break;
          }
        }
        break;
      }
    }
    
    return { title, description };
  } catch (error) {
    console.log(chalk.yellow(`Warning: Could not extract metadata from slides.md: ${error.message}`));
    return { title: deckId, description: '' };
  }
}

/**
 * Get current YouTube channel info
 */
async function getChannelInfo(youtube) {
  const response = await youtube.channels.list({
    part: ['snippet'],
    mine: true,
  });
  
  if (!response.data.items || response.data.items.length === 0) {
    throw new Error('No YouTube channel found for this account');
  }
  
  return response.data.items[0];
}

/**
 * Upload video to YouTube
 */
async function uploadVideo(auth, videoPath, deckId, customTitle = null, customDescription = null) {
  const youtube = google.youtube({ version: 'v3', auth });
  
  // Get channel info first
  console.log(chalk.cyan('\n🔍 Verifying YouTube channel...'));
  const channelInfo = await getChannelInfo(youtube);
  const channelName = channelInfo.snippet.title;
  
  console.log(chalk.green(`✔ Authenticated as: ${chalk.bold(channelName)}\n`));
  
  // Warn if not FirstEnroll
  if (!channelName.toLowerCase().includes('firstenroll')) {
    console.log(chalk.yellow('⚠️  WARNING: You are NOT uploading to FirstEnroll!'));
    console.log(chalk.gray(`   Current channel: ${channelName}`));
    console.log(chalk.gray('\n   To switch to FirstEnroll:'));
    console.log(chalk.gray('   1. Run: node scripts/check-youtube-channel.js'));
    console.log(chalk.gray('   2. Follow the instructions to switch accounts\n'));
    process.exit(1);
  }
  
  // Extract metadata from slides.md if not provided
  const metadata = extractMetadataFromSlides(deckId);
  const title = customTitle || metadata.title;
  const description = customDescription || metadata.description || `${title}\n\nGenerated from ${deckId}`;
  
  console.log(chalk.cyan('📺 Uploading to YouTube...'));
  console.log(chalk.gray(`  Channel: ${chalk.bold(channelName)}`));
  console.log(chalk.gray(`  Title: ${title}`));
  console.log(chalk.gray(`  Description: ${description.substring(0, 60)}${description.length > 60 ? '...' : ''}`));
  console.log(chalk.gray(`  Privacy: Unlisted`));
  console.log(chalk.gray(`  Made for Kids: No`));
  console.log(chalk.gray(`  File: ${path.basename(videoPath)}\n`));
  
  const fileSize = fs.statSync(videoPath).size;
  const fileSizeMB = (fileSize / (1024 * 1024)).toFixed(2);
  
  console.log(chalk.gray(`  Size: ${fileSizeMB} MB`));
  console.log(chalk.gray('  This may take a few minutes...\n'));
  
  try {
    const response = await youtube.videos.insert(
      {
        part: ['snippet', 'status'],
        requestBody: {
          snippet: {
            title: title,
            description: description,
            categoryId: '22', // People & Blogs category
          },
          status: {
            privacyStatus: 'unlisted',
            selfDeclaredMadeForKids: false,
          },
        },
        media: {
          body: fs.createReadStream(videoPath),
        },
      },
      {
        // Upload progress callback
        onUploadProgress: (evt) => {
          const progress = (evt.bytesRead / fileSize) * 100;
          process.stdout.write(`\r  Uploading: ${progress.toFixed(1)}%`);
        },
      }
    );
    
    console.log('\n');
    return response.data;
  } catch (error) {
    throw new Error(`YouTube upload failed: ${error.message}`);
  }
}

/**
 * Main function
 */
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 1) {
    console.error(chalk.red('Usage: node upload-to-youtube.js <videoPath> [title] [description]'));
    console.error('');
    console.error('Examples:');
    console.error(chalk.gray('  node upload-to-youtube.js exports/videos/FEN_STG_002.mp4'));
    console.error(chalk.gray('  node upload-to-youtube.js exports/videos/FEN_STG_002.mp4 "Custom Title"'));
    console.error(chalk.gray('  node upload-to-youtube.js exports/videos/FEN_STG_002.mp4 "Title" "Description"'));
    console.error('');
    console.error(chalk.yellow('Note: If no title is provided, it will be extracted from slides.md'));
    process.exit(1);
  }
  
  const [videoPath, customTitle, description] = args;
  
  // Check if video exists
  if (!fs.existsSync(videoPath)) {
    console.error(chalk.red(`❌ Video file not found: ${videoPath}`));
    process.exit(1);
  }
  
  // Extract deck ID from filename (e.g., FEN_STG_002.mp4 -> FEN_STG)
  const fileName = path.basename(videoPath, path.extname(videoPath));
  const deckId = fileName.replace(/_\d{3}$/, ''); // Remove version number
  
  console.log(chalk.bold.cyan('\n📤 YouTube Upload'));
  console.log(chalk.gray('─'.repeat(60)));
  console.log(chalk.gray(`  Deck: ${deckId}`));
  console.log(chalk.gray(`  File: ${path.basename(videoPath)}`));
  console.log();
  
  try {
    // Authenticate
    const auth = await authorize();
    
    // Upload video
    const video = await uploadVideo(auth, videoPath, deckId, customTitle, description);
    
    console.log(chalk.bold.green('\n✔ Upload successful!'));
    console.log(chalk.gray('─'.repeat(60)));
    console.log(chalk.gray(`  Video ID: ${video.id}`));
    console.log(chalk.gray(`  Title: ${video.snippet.title}`));
    console.log(chalk.gray(`  Privacy: ${video.status.privacyStatus}`));
    console.log(chalk.cyan(`  Watch: https://www.youtube.com/watch?v=${video.id}`));
    console.log(chalk.cyan(`  Studio: https://studio.youtube.com/video/${video.id}/edit`));
    console.log(chalk.gray('─'.repeat(60)));
    console.log();
    
    // Output JSON for agent
    console.log('--- YOUTUBE_INFO_JSON ---');
    console.log(JSON.stringify({
      videoId: video.id,
      title: video.snippet.title,
      privacy: video.status.privacyStatus,
      watchUrl: `https://www.youtube.com/watch?v=${video.id}`,
      studioUrl: `https://studio.youtube.com/video/${video.id}/edit`,
      deckId,
      status: 'success'
    }, null, 2));
    console.log('--- END_YOUTUBE_INFO_JSON ---\n');
    
    process.exit(0);
  } catch (error) {
    console.error(chalk.red('\n✗ Upload failed:'), error.message);
    
    if (error.message.includes('quota')) {
      console.error(chalk.yellow('\n⚠️  YouTube API quota exceeded'));
      console.error(chalk.gray('YouTube has daily upload quotas. Try again tomorrow.'));
    }
    
    if (error.message.includes('permission') || error.message.includes('scope')) {
      console.error(chalk.yellow('\n⚠️  Missing YouTube permissions'));
      console.error(chalk.gray('You need to re-authenticate with YouTube scope:'));
      console.error(chalk.gray('1. Delete token.json'));
      console.error(chalk.gray('2. Re-authenticate to get YouTube permissions'));
    }
    
    process.exit(1);
  }
}

main();

