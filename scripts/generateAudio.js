import fs from 'fs/promises';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  throw new Error('Missing OPENAI_API_KEY in environment variables. Please check your .env file.');
}

async function generateAudioWithTimestamps() {
  try {
    // Initialize API endpoint
    const baseUrl = 'https://api.openai.com/v1/audio/speech';
    
    // Read the text file
    const textContent = await fs.readFile(
      path.join(process.cwd(), 'decks/FEN_MF1/audio/FEN_MF1.txt'),
      'utf-8'
    );

    // Split the text into lines and filter empty lines
    const lines = textContent.split('\n').filter(line => line.trim());

    let currentTimestamp = 0;

    // Process each line
    for (const [index, line] of lines.entries()) {
      const response = await fetch(baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
          model: 'tts-1',  // or 'tts-1-hd' for higher quality
          input: line,
          voice: 'nova',  // Options: 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'
          response_format: 'mp3'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`API request failed: ${response.statusText}\n${JSON.stringify(errorData)}`);
      }

      const audioBuffer = Buffer.from(await response.arrayBuffer());
      
      // Estimate duration (OpenAI doesn't provide timestamps)
      // Rough estimate: ~150 words per minute
      const wordCount = line.split(' ').length;
      const estimatedDuration = (wordCount / 150) * 60;
      
      // Format timestamp for filename
      const minutes = Math.floor(currentTimestamp / 60);
      const seconds = Math.floor(currentTimestamp % 60);
      const timestampStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

      // Save the audio file with timestamp in filename
      const outputFileName = `${timestampStr}_audio_${index + 1}.mp3`;
      await fs.writeFile(
        path.join(process.cwd(), 'decks/FEN_MF1/audio', outputFileName),
        audioBuffer
      );

      // Generate timestamp entry with estimated duration
      const timestampEntry = `${timestampStr} - ${line}`;
      console.log(`Generated audio for timestamp ${timestampStr}: ${line} (Estimated Duration: ${estimatedDuration.toFixed(2)}s)`);
      
      // Update the timestamp for the next file
      currentTimestamp += Math.ceil(estimatedDuration);
    }

    console.log('Audio generation completed successfully!');
  } catch (error) {
    console.error('Error generating audio:', error);
  }
}

generateAudioWithTimestamps(); 