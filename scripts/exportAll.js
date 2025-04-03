#!/usr/bin/env node

import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const execAsync = promisify(exec);
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = path.join(__dirname, '..');

// Function to fix Arrow component syntax in a file
async function fixArrowSyntax(filePath) {
  try {
    const content = await fs.readFile(filePath, 'utf8');
    
    // Fix Arrow v-bind syntax
    const fixedContent = content.replace(
      /<Arrow v-bind="\{\{([^}]+)\}\}"/g,
      '<Arrow v-bind="{$1}"'
    );
    
    if (content !== fixedContent) {
      await fs.writeFile(filePath, fixedContent);
      console.log(`Fixed Arrow syntax in ${filePath}`);
      return true;
    }
    
    return false;
  } catch (error) {
    console.error(`Error fixing Arrow syntax in ${filePath}:`, error);
    return false;
  }
}

// Function to check if server is ready by attempting to connect
async function waitForServer(port = 3030, maxAttempts = 30) {
  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const response = await fetch(`http://localhost:${port}`);
      if (response.ok) {
        console.log('Server is ready!');
        return true;
      }
    } catch (error) {
      await delay(1000); // Wait 1 second between attempts
      console.log(`Waiting for server... (${attempt + 1}/${maxAttempts})`);
    }
  }
  throw new Error('Server failed to start in time');
}

// Function to refresh page and wait before export
async function refreshAndWait(port = 3030) {
  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
  
  try {
    // First navigate to the presentation URL
    console.log('Navigating to presentation URL...');
    const presentationUrl = `http://localhost:${port}/?print=true`;
    await fetch(presentationUrl);
    
    // Wait 8 seconds for initial page load
    console.log('Waiting 8 seconds for initial page load...');
    await delay(8000);
    
    // Refresh attempt
    console.log('Triggering page refresh...');
    await fetch(presentationUrl);
    
    // Wait 5 seconds after refresh
    console.log('Waiting 5 seconds after refresh...');
    await delay(5000);
    
    // One final check to ensure we're on the right page
    console.log('Final page verification...');
    const response = await fetch(presentationUrl);
    if (!response.ok) {
      console.warn('Warning: Final page verification failed');
      return false;
    }
    
    console.log('Page should be fully loaded now');
    return true;
  } catch (error) {
    console.error('Error during refresh:', error);
    return false;
  }
}

// Function to check if PDF might be blank
async function checkPdfSize(deckId) {
  const pdfPath = path.join(projectRoot, 'exports', `${deckId}.pdf`);
  try {
    const stats = await fs.stat(pdfPath);
    const sizeInKb = stats.size / 1024;
    console.log(`PDF size for ${deckId}: ${sizeInKb.toFixed(2)}KB`);
    
    // If PDF is less than 10KB, it might be blank or have issues
    if (sizeInKb < 10) {
      console.warn(`Warning: PDF for ${deckId} is suspiciously small (${sizeInKb.toFixed(2)}KB)`);
      return false;
    }
    return true;
  } catch (error) {
    console.error(`Error checking PDF size for ${deckId}:`, error);
    return false;
  }
}

// Function to get package.json scripts
async function getPackageScripts() {
  const packageJsonPath = path.join(projectRoot, 'package.json');
  const packageJson = JSON.parse(await fs.readFile(packageJsonPath, 'utf8'));
  return packageJson.scripts || {};
}

// Function to update package.json scripts
async function updatePackageScripts(newScripts) {
  const packageJsonPath = path.join(projectRoot, 'package.json');
  const packageJson = JSON.parse(await fs.readFile(packageJsonPath, 'utf8'));
  
  packageJson.scripts = {
    ...packageJson.scripts,
    ...newScripts
  };
  
  await fs.writeFile(packageJsonPath, JSON.stringify(packageJson, null, 2));
}

// Function to ensure scripts exist for a deck
async function ensureDeckScripts(deckId) {
  const scripts = await getPackageScripts();
  const newScripts = {};
  let scriptsAdded = false;
  
  // Check and add dev script if needed
  const devScript = findMatchingScript('dev', deckId, scripts);
  if (!devScript) {
    newScripts[`dev:${deckId}`] = `slidev decks/${deckId}/slides.md`;
    scriptsAdded = true;
  }
  
  // Check and add export script if needed
  const exportScript = findMatchingScript('export', deckId, scripts);
  if (!exportScript) {
    newScripts[`export:${deckId}`] = `slidev export decks/${deckId}/slides.md --output exports/${deckId}.pdf`;
    scriptsAdded = true;
  }
  
  // Update package.json if new scripts were added
  if (scriptsAdded) {
    console.log(`Adding npm scripts for ${deckId}...`);
    await updatePackageScripts(newScripts);
    return true;
  }
  
  return false;
}

// Function to get all deck directories
async function getDeckDirectories() {
  const decksPath = path.join(projectRoot, 'decks');
  const entries = await fs.readdir(decksPath, { withFileTypes: true });
  
  return entries
    .filter(entry => entry.isDirectory() && !entry.name.startsWith('.'))
    .map(dir => dir.name);
}

// Function to find matching script
function findMatchingScript(scriptType, deckId, scripts) {
  // Try different variations of the script name
  const variations = [
    `${scriptType}:${deckId}`,                    // dev:FEN_US
    `${scriptType}:${deckId.toLowerCase()}`,      // dev:fen_us
  ];
  
  // Only try suffix variations if the deckId contains an underscore
  if (deckId.includes('_')) {
    const suffix = deckId.split('_')[1];
    if (suffix) {
      variations.push(
        `${scriptType}:${suffix}`,     // dev:US
        `${scriptType}:${suffix.toLowerCase()}` // dev:us
      );
    }
  }
  
  for (const variation of variations) {
    if (scripts[variation]) {
      return variation;
    }
  }
  
  return null;
}

// Function to check if scripts exist for a deck
async function checkDeckScripts(deckId, scripts) {
  const devScript = findMatchingScript('dev', deckId, scripts);
  const exportScript = findMatchingScript('export', deckId, scripts);
  
  if (!devScript) {
    console.log(`Warning: No dev script found for ${deckId}`);
    return { exists: false };
  }
  
  if (!exportScript) {
    console.log(`Warning: No export script found for ${deckId}`);
    return { exists: false };
  }
  
  return { 
    exists: true,
    devScript,
    exportScript
  };
}

// Function to process a single deck
async function processDeck(deckId, scripts) {
  console.log(`\n=== Processing deck: ${deckId} ===`);
  
  // Fix Arrow syntax in slides.md
  const slidesPath = path.join(projectRoot, 'decks', deckId, 'slides.md');
  try {
    await fixArrowSyntax(slidesPath);
  } catch (error) {
    console.error(`Error fixing Arrow syntax in ${deckId}:`, error);
  }
  
  // Check if required scripts exist
  let scriptInfo = await checkDeckScripts(deckId, scripts);
  if (!scriptInfo.exists) {
    console.log(`Adding missing scripts for ${deckId}...`);
    const added = await ensureDeckScripts(deckId);
    if (added) {
      // Reload scripts after adding new ones
      scripts = await getPackageScripts();
      scriptInfo = await checkDeckScripts(deckId, scripts);
      if (!scriptInfo.exists) {
        console.log(`Failed to add scripts for ${deckId}`);
        return false;
      }
    }
  }
  
  let devProcess = null;
  
  try {
    // Start the dev server
    console.log(`Starting dev server for ${deckId}...`);
    devProcess = exec(`npm run ${scriptInfo.devScript}`);
    
    // Log server output for debugging
    devProcess.stdout?.on('data', (data) => console.log(`Dev Server: ${data}`));
    devProcess.stderr?.on('data', (data) => console.error(`Dev Server Error: ${data}`));
    
    // Wait for server to be ready
    await waitForServer();
    console.log('Dev server is ready');
    
    // Refresh page and wait before export
    await refreshAndWait();
    
    // Run the export command with print mode
    console.log(`Exporting ${deckId} to PDF...`);
    await execAsync(`npm run ${scriptInfo.exportScript} -- --with-clicks --timeout 30000`);
    
    // Check if PDF might be blank
    const pdfSizeOk = await checkPdfSize(deckId);
    if (!pdfSizeOk) {
      console.log('PDF may be blank or have issues. Consider re-running the export for this deck.');
    } else {
      console.log(`Successfully exported ${deckId}`);
    }
    
    return pdfSizeOk;
  } catch (error) {
    console.error(`Error processing ${deckId}:`, error);
    return false;
  } finally {
    // Cleanup - kill the dev server and any remaining processes
    if (devProcess) {
      devProcess.kill();
    }
    
    try {
      if (process.platform === 'win32') {
        await execAsync('FOR /F "tokens=5" %P IN (\'netstat -a -n -o ^| findstr :3030\') DO TaskKill.exe /PID %P /F');
      } else {
        await execAsync('lsof -ti:3030 | xargs kill -9');
      }
    } catch (error) {
      // Ignore errors in cleanup
      console.log('No leftover processes found');
    }
  }
}

// Main function to process all decks
async function processAllDecks() {
  try {
    // Ensure exports directory exists
    const exportsDir = path.join(projectRoot, 'exports');
    try {
      await fs.mkdir(exportsDir, { recursive: true });
      console.log('Ensured exports directory exists at:', exportsDir);
    } catch (error) {
      console.error('Error creating exports directory:', error);
      process.exit(1);
    }

    const deckDirectories = await getDeckDirectories();
    let scripts = await getPackageScripts();
    
    console.log(`Found ${deckDirectories.length} decks to process`);
    
    let successful = 0;
    let failed = 0;
    let skipped = 0;
    
    for (const deckId of deckDirectories) {
      const success = await processDeck(deckId, scripts);
      if (success) {
        successful++;
      } else {
        failed++;
      }
      
      // Add a small delay between processing decks
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    console.log('\n=== Export Summary ===');
    console.log(`Total decks found: ${deckDirectories.length}`);
    console.log(`Successfully exported: ${successful}`);
    console.log(`Failed to export: ${failed}`);
    console.log(`Skipped (missing scripts): ${skipped}`);
    
  } catch (error) {
    console.error('Error in main process:', error);
    process.exit(1);
  }
}

// Run the main function
processAllDecks().catch(console.error); 