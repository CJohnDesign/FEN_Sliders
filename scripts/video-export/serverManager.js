import { spawn, exec } from 'child_process';
import { promisify } from 'util';
import fetch from 'node-fetch';
import path from 'path';
import { fileURLToPath } from 'url';

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..', '..');

/**
 * Kill any process running on port 3030
 */
export async function killPortProcess(port = 3030) {
  try {
    console.log(`Checking for processes on port ${port}...`);
    
    // Use lsof to find process using the port with a timeout
    const { stdout } = await execAsync(`lsof -ti :${port} 2>/dev/null || true`);
    
    if (stdout && stdout.trim()) {
      const pids = stdout.trim().split('\n').filter(pid => pid);
      console.log(`Found ${pids.length} process(es) using port ${port}, killing...`);
      
      for (const pid of pids) {
        try {
          // Kill the process and its children
          await execAsync(`kill -9 ${pid} 2>/dev/null || true`);
          console.log(`✓ Killed process ${pid}`);
        } catch (error) {
          // Ignore errors - process might already be dead
        }
      }
      
      // Wait a moment for port to be released
      await new Promise(resolve => setTimeout(resolve, 1000));
      console.log(`✓ Port ${port} is now available`);
    } else {
      console.log(`✓ Port ${port} is available`);
    }
  } catch (error) {
    // Any error is fine - port is probably available
    console.log(`✓ Port ${port} check complete`);
  }
}

/**
 * Start Slidev server on port 3030
 * Returns server process handle
 */
export async function startServer(deckId) {
  return new Promise((resolve, reject) => {
    const slidePath = path.join(projectRoot, 'decks', deckId, 'slides.md');
    
    console.log(`Starting Slidev server for ${deckId}...`);
    console.log(`Slide path: ${slidePath}`);
    
    // Start Slidev server with explicit port
    const serverProcess = spawn('npx', ['slidev', slidePath, '--port', '3030'], {
      cwd: projectRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: false
    });

    let serverReady = false;
    let resolved = false; // Prevent multiple resolves

    serverProcess.stdout.on('data', (data) => {
      const output = data.toString();
      
      // Look for ready indicators
      if (output.includes('http://localhost:3030') || 
          output.includes('ready in') ||
          output.includes('Local:')) {
        serverReady = true;
      }
    });

    serverProcess.stderr.on('data', (data) => {
      // Ignore experimental warnings
      const msg = data.toString();
      if (!msg.includes('ExperimentalWarning')) {
        console.error('Server stderr:', msg);
      }
    });

    serverProcess.on('error', (error) => {
      if (!resolved) {
        resolved = true;
        reject(new Error(`Failed to start server: ${error.message}`));
      }
    });

    serverProcess.on('exit', (code) => {
      if (!serverReady && code !== 0 && !resolved) {
        resolved = true;
        reject(new Error(`Server exited with code ${code}`));
      }
    });

    // Wait for server to be ready with aggressive timeout
    const maxWaitTime = 30000; // 30 seconds
    const checkInterval = 500;
    let elapsed = 0;
    let checkCount = 0;

    const checkServer = setInterval(async () => {
      elapsed += checkInterval;
      checkCount++;

      if (elapsed >= maxWaitTime) {
        clearInterval(checkServer);
        if (!resolved) {
          resolved = true;
          serverProcess.kill();
          reject(new Error('Server start timeout after 30 seconds'));
        }
        return;
      }

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1000);
        
        const response = await fetch('http://localhost:3030', {
          method: 'GET',
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok || response.status === 304) {
          clearInterval(checkServer);
          if (!resolved) {
            resolved = true;
            console.log('✓ Server ready on http://localhost:3030');
            
            // Give it a tiny bit more time to fully initialize
            setTimeout(() => {
              resolve(serverProcess);
            }, 1000);
          }
        }
      } catch (error) {
        // Server not ready yet, keep checking (but don't log every attempt)
        if (checkCount % 10 === 0) {
          console.log(`Still waiting for server... (${elapsed/1000}s)`);
        }
      }
    }, checkInterval);
  });
}

/**
 * Stop Slidev server gracefully
 */
export async function stopServer(serverProcess) {
  if (!serverProcess) {
    return;
  }

  return new Promise((resolve) => {
    console.log('Stopping Slidev server...');
    
    // Try graceful shutdown first
    serverProcess.kill('SIGTERM');
    
    const forceKillTimeout = setTimeout(() => {
      console.log('Force killing server...');
      serverProcess.kill('SIGKILL');
      resolve();
    }, 5000);

    serverProcess.on('exit', () => {
      clearTimeout(forceKillTimeout);
      console.log('✓ Server stopped');
      resolve();
    });
  });
}

/**
 * Check if port 3030 is available
 */
export async function checkPortAvailable() {
  try {
    const response = await fetch('http://localhost:3030', {
      method: 'GET',
      timeout: 1000
    });
    // If we get a response, port is in use
    return false;
  } catch (error) {
    // Port is available
    return true;
  }
}

