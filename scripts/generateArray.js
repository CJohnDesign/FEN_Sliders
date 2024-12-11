import fs from 'fs/promises';
import path from 'path';
import dotenv from 'dotenv';

dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  throw new Error('Missing OPENAI_API_KEY in environment variables. Please check your .env file.');
}

async function generateArray(deckKey) {
  try {
    const baseUrl = 'https://api.openai.com/v1/chat/completions';
    
    // Read the sample array file
    const arraySample = await fs.readFile(
      path.join(process.cwd(), 'decks/FEN_MF1/audio/FEN_MF1-array.json'),
      'utf-8'
    );
    
    // Read the script file
    const scriptContent = await fs.readFile(
      path.join(process.cwd(), `decks/${deckKey}/audio/script.txt`),
      'utf-8'
    );

    // Call OpenAI to segment the text
    const response = await fetch(baseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'gpt-4-turbo-preview',
        messages: [
          {
            role: 'system',
            content: `You are a script segmentation assistant. Your task is to take a script and break it into logical segments that can be read naturally. You must return a JSON object with a "results" key containing an array of strings, where each string is a complete thought or sentence. 
            
            Here is an example of the output format: ${arraySample}

    Please segment the following script in a similar way, grouping the segments into logical sections, like in the example. In general, each segment should contain a few sentences around a particular topic. Your response must be a JSON object with a "results" key containing the array.`
          },
          {
            role: 'user',
            content: `Please segment this script into natural speaking parts: ${scriptContent}`
          }
        ],
        response_format: { type: "json_object" }
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API request failed: ${response.statusText}\n${JSON.stringify(errorData)}`);
    }

    const data = await response.json();
    const segments = data.choices[0].message.content;
    
    // Parse the response to get the results array
    const parsedSegments = JSON.parse(segments);
    if (!parsedSegments.results || !Array.isArray(parsedSegments.results)) {
      throw new Error('Invalid response format: missing results array');
    }

    // Save just the array portion to the JSON file
    await fs.writeFile(
      path.join(process.cwd(), `decks/${deckKey}/audio/${deckKey}-array.json`),
      JSON.stringify(parsedSegments.results, null, 4)
    );

    console.log(`Generated array file: ${deckKey}-array.json`);
    console.log('Array generation completed successfully!');
  } catch (error) {
    console.error('Error generating array:', error);
  }
}

// Check if a deck key was provided as a command line argument
const deckKey = process.argv[2];
if (!deckKey) {
  console.error('Please provide a deck key as a command line argument.');
  process.exit(1);
}

generateArray(deckKey); 