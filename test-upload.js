#!/usr/bin/env node

console.log('=== Testing Script ===');
console.log('Node version:', process.version);
console.log('Working directory:', process.cwd());

import fs from 'fs';
import path from 'path';

const videoPath = './exports/videos/FEN_HMP_001.mp4';

console.log('\n=== Checking video file ===');
if (fs.existsSync(videoPath)) {
  const stats = fs.statSync(videoPath);
  console.log('✓ File exists');
  console.log('  Path:', path.resolve(videoPath));
  console.log('  Size:', (stats.size / (1024 * 1024)).toFixed(2), 'MB');
} else {
  console.log('✗ File not found at:', path.resolve(videoPath));
}

console.log('\n=== Script complete ===');

