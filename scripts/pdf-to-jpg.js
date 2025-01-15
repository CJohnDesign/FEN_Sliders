import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { fromPath } from 'pdf2pic';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

async function convertPDFsToJPGs(deckId) {
  // Set up paths for PDFs and output images
  const pdfPath = path.join(projectRoot, 'decks', deckId, 'img', 'pdfs');
  const pagesPath = path.join(projectRoot, 'decks', deckId, 'img', 'pages');

  try {
    // Find all PDF files in the pdfs directory
    const files = await fs.readdir(pdfPath);
    const pdfFiles = files.filter(file => file.toLowerCase().endsWith('.pdf'));

    if (pdfFiles.length === 0) {
      console.log('No PDF files found in the pdfs directory');
      return;
    }

    console.log('\nStarting PDF conversions...\n');

    // Convert each PDF file
    for (const pdfFile of pdfFiles) {
      console.log(`📄 Processing: ${pdfFile}`);
      
      const pdfFilePath = path.join(pdfPath, pdfFile);
      const baseFileName = path.basename(pdfFile, '.pdf');
      
      // Configure conversion options
      const options = {
        density: 300,           // High quality
        saveFilename: baseFileName,
        savePath: pagesPath,
        format: "jpg",
        quality: 100,
        preserveAspectRatio: true
      };

      // Convert PDF to images
      const convert = fromPath(pdfFilePath, options);
      const results = await convert.bulk(-1);  // -1 means convert all pages
      
      // Report results
      const pageCount = Array.isArray(results) ? results.length : 0;
      console.log(`✅ Created ${pageCount} pages in ${pagesPath}\n`);
    }

    console.log('🎉 All PDF conversions completed successfully!\n');

  } catch (error) {
    console.error('\n❌ Error converting PDFs:', error.message);
    process.exit(1);
  }
}

// Get deck ID from command line argument
const deckId = process.argv[2];

if (!deckId) {
  console.error('\n⚠️  Please provide a deck ID');
  process.exit(1);
}

convertPDFsToJPGs(deckId); 