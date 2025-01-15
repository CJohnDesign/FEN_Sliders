import { generateClickTimings } from './generateClickTimings.js';

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