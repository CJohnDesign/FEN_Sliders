import fs from 'fs/promises';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  throw new Error('Missing OPENAI_API_KEY in environment variables. Please check your .env file.');
}

async function findMdFile(deckKey) {
  const possiblePaths = [
    path.join(process.cwd(), `decks/${deckKey}/audio/${deckKey}.md`),
    path.join(process.cwd(), `decks/${deckKey}/audio/audio_script.md`),
    // Add more potential paths if needed
  ];

  for (const filePath of possiblePaths) {
    try {
      await fs.access(filePath);
      return filePath;
    } catch (error) {
      continue;
    }
  }

  throw new Error(`Could not find markdown file for deck ${deckKey}. Searched in:\n${possiblePaths.join('\n')}`);
}

async function parseMdFile(filePath) {
  const content = await fs.readFile(filePath, 'utf-8');
  const sections = [];
  
  // Split content by the single line delimiter pattern: ---- Text ----
  const sectionRegex = /^----\s*(.*?)\s*----$/gm;
  const parts = content.split(sectionRegex);
  
  // Remove first element if it's empty (content before first delimiter)
  if (parts[0].trim() === '') {
    parts.shift();
  }
  
  // Process parts in pairs (title and content)
  for (let i = 0; i < parts.length; i += 2) {
    const title = parts[i];
    const text = parts[i + 1]?.trim();
    
    if (title && text) {
      // Split the text into paragraphs (split by lines that are empty or contain only whitespace)
      const paragraphs = text.split(/\n[\s\n]*\n/).filter(p => p.trim());
      
      // Create a section for each paragraph
      paragraphs.forEach((paragraph, pIndex) => {
        sections.push({
          title: `${title}_click_${pIndex + 1}`,
          text: paragraph.trim(),
          slideNumber: (i / 2) + 1,
          clickNumber: pIndex + 1
        });
      });
    }
  }
  
  return sections;
}

// Add filename validation
const validateFilename = (deckKey, slideNumber, clickNumber) => {
  if (!deckKey.match(/^FEN_[A-Z_]+$/)) {
    throw new Error(`Invalid deckKey format: ${deckKey}`);
  }
  
  const cleanClick = String(clickNumber)
    .replace(/[^0-9_]/g, '')
    .replace(/_{2,}/g, '_');
    
  return `${deckKey}${slideNumber}_${cleanClick}.mp3`;
};

// Utility function to sleep/wait
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Enhanced retry logic with exponential backoff and better error classification
async function retryWithBackoff(fn, maxRetries = 3, baseDelay = 3000, rateLimiter = null) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const result = await fn();
      if (rateLimiter) rateLimiter.recordSuccess();
      return result;
    } catch (error) {
      if (rateLimiter) rateLimiter.recordError();
      
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Enhanced error classification
      const errorMessage = error.message.toLowerCase();
      const isRetryable = 
        errorMessage.includes('server_error') || 
        errorMessage.includes('internal server error') ||
        errorMessage.includes('rate limit') ||
        errorMessage.includes('timeout') ||
        errorMessage.includes('502') ||
        errorMessage.includes('503') ||
        errorMessage.includes('504') ||
        errorMessage.includes('connection') ||
        errorMessage.includes('network');
      
      if (!isRetryable) {
        console.error(`❌ Non-retryable error: ${error.message}`);
        throw error; // Don't retry non-transient errors
      }
      
      // Exponential backoff with jitter and longer delays
      const delay = baseDelay * Math.pow(2, attempt - 1) + Math.random() * 2000;
      console.warn(`🔄 Attempt ${attempt}/${maxRetries} failed, retrying in ${Math.round(delay)}ms...`);
      console.warn(`   Error: ${error.message.substring(0, 100)}${error.message.length > 100 ? '...' : ''}`);
      await sleep(delay);
    }
  }
}

// Enhanced rate limiting utility with circuit breaker
class RateLimiter {
  constructor(requestsPerMinute = 25) { // Reduced from 50 to be more conservative
    this.requests = [];
    this.maxRequests = requestsPerMinute;
    this.consecutiveErrors = 0;
    this.maxConsecutiveErrors = 5;
    this.circuitBreakerCooldown = 30000; // 30 seconds
    this.lastErrorTime = 0;
    this.minDelayBetweenRequests = 2000; // 2 seconds minimum between requests
    this.lastRequestTime = 0;
  }
  
  isCircuitBreakerOpen() {
    if (this.consecutiveErrors >= this.maxConsecutiveErrors) {
      const timeSinceLastError = Date.now() - this.lastErrorTime;
      if (timeSinceLastError < this.circuitBreakerCooldown) {
        return true;
      } else {
        // Reset circuit breaker after cooldown
        this.consecutiveErrors = 0;
        return false;
      }
    }
    return false;
  }
  
  recordSuccess() {
    this.consecutiveErrors = 0;
  }
  
  recordError() {
    this.consecutiveErrors++;
    this.lastErrorTime = Date.now();
  }
  
  async waitIfNeeded() {
    // Check circuit breaker
    if (this.isCircuitBreakerOpen()) {
      const remainingCooldown = this.circuitBreakerCooldown - (Date.now() - this.lastErrorTime);
      console.log(`🚫 Circuit breaker is open due to ${this.consecutiveErrors} consecutive errors. Waiting ${Math.round(remainingCooldown/1000)}s before retrying...`);
      await sleep(remainingCooldown + 1000); // Add extra second
      return this.waitIfNeeded();
    }
    
    const now = Date.now();
    
    // Enforce minimum delay between requests
    const timeSinceLastRequest = now - this.lastRequestTime;
    if (timeSinceLastRequest < this.minDelayBetweenRequests) {
      const waitTime = this.minDelayBetweenRequests - timeSinceLastRequest;
      console.log(`⏳ Waiting ${Math.round(waitTime/1000)}s for minimum delay between requests...`);
      await sleep(waitTime);
    }
    
    // Remove requests older than 1 minute
    this.requests = this.requests.filter(time => now - time < 60000);
    
    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = Math.min(...this.requests);
      const waitTime = 60000 - (now - oldestRequest) + 1000; // Add 1s buffer
      console.log(`⏳ Rate limit reached (${this.requests.length}/${this.maxRequests}), waiting ${Math.round(waitTime/1000)}s...`);
      await sleep(waitTime);
      return this.waitIfNeeded(); // Recursive call to check again
    }
    
    this.requests.push(now);
    this.lastRequestTime = now;
  }
}

// Enhanced audio generation function with better error handling and monitoring
async function generateAudioForSection(section, outputDir, deckKey, rateLimiter) {
  const baseUrl = 'https://api.openai.com/v1/audio/speech';
  
  // Validate input text
  if (!section.text || section.text.trim().length === 0) {
    console.warn(`⚠️ Skipping empty section: ${section.title}`);
    return null;
  }
  
  // More conservative text length limit
  if (section.text.length > 4000) {
    console.warn(`⚠️ Text too long for section ${section.title} (${section.text.length} chars), truncating...`);
    section.text = section.text.substring(0, 3997) + '...';
  }
  
  await rateLimiter.waitIfNeeded();
  
  return retryWithBackoff(async () => {
    console.log(`🎵 Generating audio for: ${section.title.substring(0, 50)}${section.title.length > 50 ? '...' : ''}`);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    try {
      const response = await fetch(baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
          'User-Agent': 'FEN-AudioGenerator/1.0'
        },
        body: JSON.stringify({
          model: 'tts-1', // Using faster model
          input: section.text,
          voice: 'nova',
          response_format: 'mp3',
          speed: 1.0
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          errorData = { error: { message: `HTTP ${response.status}: ${response.statusText}` } };
        }
        
        // Log detailed error information
        console.error(`❌ API Error Details:`);
        console.error(`   Status: ${response.status} ${response.statusText}`);
        console.error(`   Headers: ${JSON.stringify(Object.fromEntries(response.headers.entries()))}`);
        
        throw new Error(`API request failed: ${response.statusText}\n${JSON.stringify(errorData)}`);
      }

      const audioBuffer = Buffer.from(await response.arrayBuffer());
      
      if (audioBuffer.length === 0) {
        throw new Error('Received empty audio buffer from API');
      }
      
      // Generate output filename
      const outputFileName = validateFilename(deckKey, section.slideNumber, section.clickNumber);
      const outputPath = path.join(outputDir, outputFileName);
      
      await fs.writeFile(outputPath, audioBuffer);
      
      console.log(`✅ Generated: ${outputFileName} (${(audioBuffer.length / 1024).toFixed(1)}KB)`);
      return outputFileName;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 30 seconds');
      }
      throw error;
    }
  }, 3, 3000, rateLimiter); // 3 retries, starting with 3s delay, pass rateLimiter
}

async function generateAudio(deckKey, specificSlide = null, specificClick = null) {
  const rateLimiter = new RateLimiter(20); // Reduced to 20 requests per minute for better stability
  
  try {
    console.log(`🚀 Starting audio generation for deck: ${deckKey}`);
    
    // Find the markdown file
    const mdFilePath = await findMdFile(deckKey);
    console.log(`📄 Found script at: ${mdFilePath}`);
    
    const sections = await parseMdFile(mdFilePath);
    console.log(`📑 Parsed ${sections.length} sections`);

    // Create the output directory if it doesn't exist
    const outputDir = path.join(process.cwd(), `decks/${deckKey}/audio/oai`);
    await fs.mkdir(outputDir, { recursive: true });

    // Filter sections based on slide and click numbers
    let sectionsToProcess = sections;
    if (specificSlide) {
      sectionsToProcess = sections.filter(section => section.slideNumber === specificSlide);
      if (sectionsToProcess.length === 0) {
        throw new Error(`No slide found with number ${specificSlide}`);
      }
    }
    if (specificClick) {
      sectionsToProcess = sectionsToProcess.filter(section => section.clickNumber === specificClick);
      if (sectionsToProcess.length === 0) {
        throw new Error(`No click ${specificClick} found for slide ${specificSlide}`);
      }
    }

    console.log(`🎯 Processing ${sectionsToProcess.length} sections...`);

    // Check for existing files to allow resuming
    const existingFiles = new Set();
    try {
      const files = await fs.readdir(outputDir);
      files.forEach(file => existingFiles.add(file));
    } catch (error) {
      // Directory doesn't exist yet, that's okay
    }

    let processed = 0;
    let skipped = 0;
    const startTime = Date.now();

    // Process each section in order
    for (const section of sectionsToProcess) {
      if (!section.text || section.text.trim().length === 0) {
        skipped++;
        continue; // Skip empty sections
      }

      // Check if file already exists
      const outputFileName = validateFilename(deckKey, section.slideNumber, section.clickNumber);
      if (existingFiles.has(outputFileName)) {
        console.log(`⏭️ Skipping existing file: ${outputFileName}`);
        skipped++;
        continue;
      }

      try {
        await generateAudioForSection(section, outputDir, deckKey, rateLimiter);
        processed++;
        
        // Progress update with better formatting
        const remaining = sectionsToProcess.length - processed - skipped;
        const elapsed = (Date.now() - startTime) / 1000;
        const avgTimePerSection = processed > 0 ? elapsed / processed : 0;
        const estimatedTimeRemaining = avgTimePerSection * remaining;
        
        console.log(`📊 Progress: ${processed}/${sectionsToProcess.length} (${remaining} remaining, ~${Math.round(estimatedTimeRemaining)}s left)`);
        console.log(`   Success rate: ${((processed / (processed + rateLimiter.consecutiveErrors)) * 100).toFixed(1)}%`);
        
        // Add a small delay between successful requests to be extra careful
        if (remaining > 0) {
          await sleep(500); // 0.5 second pause between sections
        }
      } catch (error) {
        console.error(`❌ Failed to generate audio for section ${section.title}:`);
        console.error(`   Error: ${error.message}`);
        console.error(`   Consecutive errors: ${rateLimiter.consecutiveErrors}`);
        
        // If we're getting too many errors, pause longer
        if (rateLimiter.consecutiveErrors >= 3) {
          console.log(`⏸️ Taking a longer break due to repeated failures...`);
          await sleep(5000); // 5 second pause
        }
      }
    }

    const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`🎉 Audio generation completed! Processed: ${processed}, Skipped: ${skipped}, Total time: ${totalTime}s`);
    
    if (processed === 0 && sectionsToProcess.length > 0) {
      console.warn('⚠️ No new audio files were generated. Check for errors above.');
    }
  } catch (error) {
    console.error('💥 Fatal error during audio generation:', error.message);
    console.error('Stack trace:', error.stack);
    process.exit(1);
  }
}

// Update argument handling
const deckKey = process.argv[2];
const specificSlide = process.argv[3] ? parseInt(process.argv[3], 10) : null;
const specificClick = process.argv[4] ? parseInt(process.argv[4], 10) : null;

if (!deckKey) {
  console.error('Please provide a deck key as a command line argument.');
  process.exit(1);
}

generateAudio(deckKey, specificSlide, specificClick); 