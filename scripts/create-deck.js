import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

async function createDeckStructure(deckPath, deckId) {
  // Create image directories
  const imgDirectories = [
    'img/logos',
    'img/pages',
    'img/pdfs',
  ];

  for (const dir of imgDirectories) {
    await fs.mkdir(path.join(deckPath, dir), { recursive: true });
    await fs.writeFile(
      path.join(deckPath, dir, '.gitkeep'),
      ''
    );
  }

  // Create audio directory and files
  const audioPath = path.join(deckPath, 'audio');
  await fs.mkdir(path.join(audioPath, 'oai'), { recursive: true });
  
  // Create audio_script.md
  await fs.writeFile(
    path.join(audioPath, 'audio_script.md'),
    `# ${deckId} Audio Script\n\n`
  );

  // Create audio_config.json
  const defaultConfig = {
    voice: "alloy",
    model: "tts-1",
    speed: 1.0
  };
  
  await fs.writeFile(
    path.join(audioPath, 'audio_config.json'),
    JSON.stringify(defaultConfig, null, 2)
  );
}

async function main() {
  const deckId = process.argv[2];
  const title = process.argv[3] || `${deckId} Presentation`;

  if (!deckId) {
    console.error('Please provide a deck ID');
    process.exit(1);
  }

  const newDeckPath = path.join(projectRoot, 'decks', deckId);

  try {
    // 1. Create base directory
    await fs.mkdir(newDeckPath, { recursive: true });

    // 2. Create folder structure
    await createDeckStructure(newDeckPath, deckId);

    // 3. Copy and update slides.md
    const templateSlidesPath = path.join(projectRoot, 'decks', 'FEN_TEMPLATE', 'slides.md');
    let slidesContent = await fs.readFile(templateSlidesPath, 'utf8');
    
    slidesContent = slidesContent
      .replace(/{{DECK_ID}}/g, deckId)
      .replace(/{{TITLE}}/g, title);

    await fs.writeFile(
      path.join(newDeckPath, 'slides.md'),
      slidesContent
    );

    // 4. Update package.json
    const pkgPath = path.join(projectRoot, 'package.json');
    const pkg = JSON.parse(await fs.readFile(pkgPath, 'utf8'));

    pkg.scripts = {
      ...pkg.scripts,
      [`build:${deckId}`]: `slidev build decks/${deckId}/slides.md --out dist/${deckId}`,
      [`dev:${deckId}`]: `slidev decks/${deckId}/slides.md`,
      [`export:${deckId}`]: `slidev export decks/${deckId}/slides.md --output exports/${deckId}.pdf`,
      [`preview:${deckId}`]: `slidev decks/${deckId}/slides.md --remote`,
    };

    await fs.writeFile(pkgPath, JSON.stringify(pkg, null, 2));

    console.log(`Successfully created deck ${deckId}`);
    console.log('\nAdded npm scripts:');
    console.log(`- npm run dev:${deckId}`);
    console.log(`- npm run build:${deckId}`);
    console.log(`- npm run export:${deckId}`);
    console.log(`- npm run preview:${deckId}`);

  } catch (error) {
    console.error(`Error creating deck: ${error.message}`);
    process.exit(1);
  }
}

main(); 