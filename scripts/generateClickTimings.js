import fs from 'fs';
import path from 'path';
import OpenAI from 'openai';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const WORDS_PER_MINUTE = 150; // Average speaking rate
const WORDS_PER_SECOND = WORDS_PER_MINUTE / 60;

export async function generateClickTimings(deckKey) {
    // Read the markdown file
    const mdPath = path.join('decks', deckKey, 'audio', `${deckKey}.md`);
    const mdContent = fs.readFileSync(mdPath, 'utf-8');

    // Read the config file
    const configPath = path.join('decks', deckKey, 'audio', 'config.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));

    // Split MD into sections using the delimiter
    const sections = mdContent.split('----').filter(section => section.trim());
    const sectionTitles = sections.map(section => {
        const lines = section.trim().split('\n');
        return lines[0].trim();
    });

    // Calculate speaking duration for each section
    const sectionDurations = sections.map(section => {
        const wordCount = section.trim().split(/\s+/).length;
        return Math.ceil(wordCount / WORDS_PER_SECOND);
    });

    // Initialize OpenAI
    const openai = new OpenAI({
        apiKey: process.env.OPENAI_API_KEY,
    });

    // Process each slide
    for (let i = 0; i < config.slides.length; i++) {
        const slide = config.slides[i];
        const sectionContent = sections[i]?.trim();
        const duration = sectionDurations[i];
        const numClicks = slide.clicks.length;

        if (!sectionContent) continue;

        // Skip if no clicks needed
        if (numClicks === 0) continue;

        const prompt = `
        I have a presentation slide with the following content:
        "${sectionContent}"
        
        This content takes approximately ${duration} seconds to speak at a normal pace.
        The slide needs ${numClicks} click points to reveal content progressively.
        
        Please provide an array of ${numClicks} numbers representing the most logical timestamps (in seconds) 
        to trigger each progressive reveal, considering the natural flow of the content.
        The numbers should be between 0 and ${duration} and in ascending order.
        
        Return only the array of numbers, nothing else.`;

        try {
            const completion = await openai.chat.completions.create({
                model: "gpt-3.5-turbo",
                messages: [{ role: "user", content: prompt }],
                temperature: 0.3,
                max_tokens: 100
            });

            const response = completion.choices[0].message.content;
            const clickTimings = JSON.parse(response);

            // Update the config with new timings
            config.slides[i].clicks = clickTimings;

            console.log(`Slide ${i + 1} timings generated: ${clickTimings}`);
        } catch (error) {
            console.error(`Error processing slide ${i + 1}:`, error);
        }
    }

    // Save updated config
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    console.log('Click timings have been generated and saved to config.json');
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
    const deckKey = process.argv[2] || 'FEN_MF';
    console.log(`Generating click timings for deck: ${deckKey}`);
    
    generateClickTimings(deckKey)
        .then(() => {
            console.log('Click timing generation complete!');
            process.exit(0);
        })
        .catch(error => {
            console.error('Error generating click timings:', error);
            process.exit(1);
        });
}