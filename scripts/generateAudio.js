import fs from 'fs/promises';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  throw new Error('Missing OPENAI_API_KEY in environment variables. Please check your .env file.');
}

async function generateAudio(deckKey) {
  try {
    const baseUrl = 'https://api.openai.com/v1/audio/speech';
    
    // Read the JSON file
    const jsonContent = await fs.readFile(
      path.join(process.cwd(), `decks/${deckKey}/audio/${deckKey}-array.json`),
      'utf-8'
    );
    
    // Parse the JSON array
    const lines = JSON.parse(jsonContent);

    // Process each line from the array
    for (const [index, line] of lines.entries()) {
      const response = await fetch(baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
          model: 'tts-1',
          input: line,
          voice: 'nova',
          response_format: 'mp3'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`API request failed: ${response.statusText}\n${JSON.stringify(errorData)}`);
      }

      const audioBuffer = Buffer.from(await response.arrayBuffer());
      
      // Save the audio file using the deck key in the filename
      const outputFileName = `${deckKey}-${index}`;
      await fs.writeFile(
        path.join(process.cwd(), `decks/${deckKey}/audio/oai`, `${outputFileName}.mp3`),
        audioBuffer
      );

      console.log(`Generated audio file: ${outputFileName}.mp3`);
    }

    console.log('Audio generation completed successfully!');
  } catch (error) {
    console.error('Error generating audio:', error);
  }
}

// Check if a deck key was provided as a command line argument
const deckKey = process.argv[2];
if (!deckKey) {
  console.error('Please provide a deck key as a command line argument.');
  process.exit(1);
}

generateAudio(deckKey); 