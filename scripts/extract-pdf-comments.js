/**
 * PDF Comment/Annotation Extractor
 * 
 * Extracts annotations (comments, highlights, sticky notes) from PDF files
 * using Mozilla's pdfjs-dist library.
 * 
 * Usage:
 *   node scripts/extract-pdf-comments.js <pdf-path>
 * 
 * Example:
 *   node scripts/extract-pdf-comments.js "public/MLIC_Heirloom_Video_LT EDITS_01162026(LT).pdf"
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Dynamic import for pdfjs-dist (ES module compatibility)
async function loadPdfJs() {
  const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf.mjs');
  return pdfjsLib;
}

/**
 * Check if a point is inside a quadrilateral defined by quadPoints
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 * @param {Array} quadPoints - Array of 8 numbers defining the quad [x1,y1,x2,y2,x3,y3,x4,y4]
 * @returns {boolean}
 */
function isPointInQuad(x, y, quadPoints) {
  if (!quadPoints || quadPoints.length < 8) return false;
  
  // QuadPoints are: [x1,y1, x2,y2, x3,y3, x4,y4] - corners of highlight region
  // Usually: top-left, top-right, bottom-left, bottom-right (but order varies)
  const minX = Math.min(quadPoints[0], quadPoints[2], quadPoints[4], quadPoints[6]);
  const maxX = Math.max(quadPoints[0], quadPoints[2], quadPoints[4], quadPoints[6]);
  const minY = Math.min(quadPoints[1], quadPoints[3], quadPoints[5], quadPoints[7]);
  const maxY = Math.max(quadPoints[1], quadPoints[3], quadPoints[5], quadPoints[7]);
  
  // Add some tolerance for text slightly outside highlight bounds
  const tolerance = 2;
  return x >= (minX - tolerance) && x <= (maxX + tolerance) && 
         y >= (minY - tolerance) && y <= (maxY + tolerance);
}

/**
 * Check if a text item overlaps with a rectangle
 * @param {Object} textItem - Text item with transform info
 * @param {Array} rect - [x1, y1, x2, y2] rectangle
 * @returns {boolean}
 */
function textOverlapsRect(textItem, rect) {
  if (!rect || rect.length < 4) return false;
  
  const [tx, ty] = [textItem.transform[4], textItem.transform[5]];
  const textWidth = textItem.width || 0;
  const textHeight = textItem.height || 10;
  
  const textX1 = tx;
  const textY1 = ty;
  const textX2 = tx + textWidth;
  const textY2 = ty + textHeight;
  
  const [rectX1, rectY1, rectX2, rectY2] = rect;
  
  // Check overlap with tolerance
  const tolerance = 5;
  return !(textX2 < rectX1 - tolerance || textX1 > rectX2 + tolerance ||
           textY2 < rectY1 - tolerance || textY1 > rectY2 + tolerance);
}

/**
 * Extract text under highlight annotations
 * @param {Object} page - PDF page object
 * @param {Array} annotations - Annotations for this page
 * @returns {Promise<Array>} Annotations with highlightedText populated
 */
async function extractHighlightedText(page, annotations) {
  const textContent = await page.getTextContent();
  const textItems = textContent.items;
  
  for (const annot of annotations) {
    if (annot.type === 'Highlight' || annot.type === 'Underline' || annot.type === 'StrikeOut') {
      const matchingText = [];
      
      // Try quadPoints first (more accurate for highlights)
      if (annot.quadPoints && annot.quadPoints.length >= 8) {
        // QuadPoints may contain multiple quads (8 numbers each)
        const numQuads = Math.floor(annot.quadPoints.length / 8);
        
        for (const textItem of textItems) {
          const [tx, ty] = [textItem.transform[4], textItem.transform[5]];
          
          // Check against each quad
          for (let i = 0; i < numQuads; i++) {
            const quad = annot.quadPoints.slice(i * 8, (i + 1) * 8);
            if (isPointInQuad(tx, ty, quad)) {
              if (textItem.str && textItem.str.trim()) {
                matchingText.push(textItem.str);
              }
              break;
            }
          }
        }
      }
      
      // Fallback to rect if no quadPoints match
      if (matchingText.length === 0 && annot.rect) {
        for (const textItem of textItems) {
          if (textOverlapsRect(textItem, annot.rect)) {
            if (textItem.str && textItem.str.trim()) {
              matchingText.push(textItem.str);
            }
          }
        }
      }
      
      annot.highlightedText = matchingText.length > 0 ? matchingText.join(' ').trim() : null;
    }
  }
  
  return annotations;
}

/**
 * Extract annotations from a PDF file
 * @param {string} pdfPath - Path to the PDF file
 * @returns {Promise<Array>} Array of annotation objects
 */
async function extractAnnotations(pdfPath) {
  const pdfjsLib = await loadPdfJs();
  
  // Read PDF file
  const absolutePath = path.isAbsolute(pdfPath) 
    ? pdfPath 
    : path.resolve(process.cwd(), pdfPath);
  
  if (!fs.existsSync(absolutePath)) {
    throw new Error(`PDF file not found: ${absolutePath}`);
  }
  
  const data = new Uint8Array(fs.readFileSync(absolutePath));
  
  // Load PDF document
  const loadingTask = pdfjsLib.getDocument({ data });
  const pdf = await loadingTask.promise;
  const numPages = pdf.numPages;
  
  console.log(`\n📄 PDF loaded: ${path.basename(pdfPath)}`);
  console.log(`   Pages: ${numPages}\n`);
  
  const annotations = [];
  
  // Process each page
  for (let pageNum = 1; pageNum <= numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const annots = await page.getAnnotations({ intent: 'display' });
    
    // Log all annotation types found for debugging
    const allTypes = [...new Set(annots.map(a => a.subtype))];
    if (allTypes.length > 0) {
      console.log(`   Page ${pageNum} annotation types: ${allTypes.join(', ')}`);
    }
    
    // Get ALL annotations to look for comments
    let pageAnnotations = annots.map(a => {
      // Extract richText properly - it might be an object with str property or nested structure
      let richTextContent = null;
      if (a.richText) {
        if (typeof a.richText === 'string') {
          richTextContent = a.richText;
        } else if (a.richText.str) {
          richTextContent = a.richText.str;
        } else if (typeof a.richText === 'object') {
          // Try to extract text from the object
          richTextContent = JSON.stringify(a.richText, null, 2);
        }
      }
      
      // Extract contentsObj if it exists
      let contentsText = a.contents || null;
      if (!contentsText && a.contentsObj) {
        if (typeof a.contentsObj === 'string') {
          contentsText = a.contentsObj;
        } else if (a.contentsObj.str) {
          contentsText = a.contentsObj.str;
        }
      }
      
      // Extract titleObj for author
      let authorText = a.title || a.author || null;
      if (!authorText && a.titleObj) {
        if (typeof a.titleObj === 'string') {
          authorText = a.titleObj;
        } else if (a.titleObj.str) {
          authorText = a.titleObj.str;
        }
      }
      
      return {
        page: pageNum,
        type: a.subtype,
        contents: contentsText,
        author: authorText,
        creationDate: a.creationDate || null,
        modificationDate: a.modificationDate || null,
        rect: a.rect,
        quadPoints: a.quadPoints || null,
        color: a.color || null,
        highlightedText: null,
        // Additional fields that might contain comments
        name: a.name || null,
        richText: richTextContent,
        parentId: a.parentId || null,
        inReplyTo: a.inReplyTo || null,
        subject: a.subject || null,
        rc: a.rc || null,
        popupRef: a.popupRef || null,
        id: a.id || null,
        raw: Object.keys(a).filter(k => !['rect', 'quadPoints', 'color', 'transform'].includes(k))
      };
    });
    
    // Extract text under highlights
    if (pageAnnotations.length > 0) {
      pageAnnotations = await extractHighlightedText(page, pageAnnotations);
    }
    
    annotations.push(...pageAnnotations);
  }
  
  // Debug: show raw annotation keys
  if (annotations.length > 0) {
    console.log(`\n   Debug - First annotation keys: ${annotations[0].raw.join(', ')}`);
  }
  
  return annotations;
}

/**
 * Format annotations for display
 * @param {Array} annotations - Array of annotation objects
 * @returns {string} Formatted string output
 */
function formatAnnotations(annotations) {
  if (annotations.length === 0) {
    return '\n⚠️  No annotations/comments found in this PDF.\n\nPossible reasons:\n- The PDF has no comments or annotations\n- Comments were flattened into the document\n- Annotations don\'t have text content (highlight-only)\n\nTry exporting comments from Adobe: Comment > Export All Comments to Data File\n';
  }
  
  let output = `\n📝 Found ${annotations.length} annotation(s):\n`;
  output += '─'.repeat(60) + '\n';
  
  // Group by page
  const byPage = {};
  annotations.forEach(a => {
    if (!byPage[a.page]) byPage[a.page] = [];
    byPage[a.page].push(a);
  });
  
  for (const [pageNum, pageAnnots] of Object.entries(byPage)) {
    output += `\n📄 Page ${pageNum}:\n`;
    
    pageAnnots.forEach((a, idx) => {
      output += `\n  [${a.type}]`;
      if (a.author) output += ` by ${a.author}`;
      if (a.subject) output += ` - Subject: ${a.subject}`;
      output += '\n';
      
      if (a.contents) {
        output += `  💬 Comment: "${a.contents}"\n`;
      }
      
      if (a.richText && a.richText !== 'null') {
        // If it's JSON, try to extract readable text
        if (a.richText.startsWith('{') || a.richText.startsWith('[')) {
          try {
            const parsed = JSON.parse(a.richText);
            output += `  📝 Rich Text Data:\n${JSON.stringify(parsed, null, 4).split('\n').map(l => '     ' + l).join('\n')}\n`;
          } catch {
            output += `  📝 Rich Text: ${a.richText}\n`;
          }
        } else {
          output += `  📝 Rich Text: "${a.richText}"\n`;
        }
      }
      
      if (a.name) {
        output += `  Name: ${a.name}\n`;
      }
      
      if (a.rc) {
        output += `  RC: ${a.rc}\n`;
      }
      
      if (a.highlightedText) {
        output += `  📌 Highlighted: "${a.highlightedText}"\n`;
      }
      
      if (!a.contents && !a.highlightedText && !a.richText) {
        output += `  (No extractable text)\n`;
      }
    });
  }
  
  output += '\n' + '─'.repeat(60) + '\n';
  
  return output;
}

/**
 * Export annotations as JSON
 * @param {Array} annotations - Array of annotation objects
 * @param {string} outputPath - Path to write JSON file
 */
function exportToJson(annotations, outputPath) {
  fs.writeFileSync(outputPath, JSON.stringify(annotations, null, 2));
  console.log(`\n💾 JSON exported to: ${outputPath}`);
}

// Main execution
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log(`
PDF Comment Extractor
─────────────────────────────────────────
Usage:
  node scripts/extract-pdf-comments.js <pdf-path> [--json]

Options:
  --json    Also export as JSON file

Examples:
  node scripts/extract-pdf-comments.js "public/MyDocument.pdf"
  node scripts/extract-pdf-comments.js "public/MyDocument.pdf" --json
`);
    process.exit(1);
  }
  
  const pdfPath = args[0];
  const exportJson = args.includes('--json');
  
  try {
    const annotations = await extractAnnotations(pdfPath);
    
    // Display formatted output
    console.log(formatAnnotations(annotations));
    
    // Export JSON if requested
    if (exportJson && annotations.length > 0) {
      const baseName = path.basename(pdfPath, '.pdf');
      const jsonPath = path.join(path.dirname(pdfPath), `${baseName}-annotations.json`);
      exportToJson(annotations, jsonPath);
    }
    
    // Summary
    if (annotations.length > 0) {
      const withComments = annotations.filter(a => a.contents).length;
      const withHighlightedText = annotations.filter(a => a.highlightedText).length;
      console.log(`Summary:`);
      console.log(`  - ${withComments} annotation(s) with comment text`);
      console.log(`  - ${withHighlightedText} highlight(s) with extracted text`);
    }
    
  } catch (error) {
    console.error(`\n❌ Error: ${error.message}`);
    process.exit(1);
  }
}

main();
