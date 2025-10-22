#!/bin/bash

# Automated Deck Export Script
# Usage: ./auto-export.sh FEN_STG

set -e

DECK_ID=$1

if [ -z "$DECK_ID" ]; then
    echo "❌ Please provide a deck ID"
    echo "Usage: ./auto-export.sh FEN_STG"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🚀 AUTOMATED EXPORT FOR $DECK_ID"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Export PDF
echo "📄 Step 1: Exporting PDF..."
npm run deck export "$DECK_ID"

# Find the latest PDF file
LATEST_PDF=$(ls -t exports/${DECK_ID}_*.pdf 2>/dev/null | head -1)

if [ -z "$LATEST_PDF" ]; then
    echo "❌ No PDF found after export"
    exit 1
fi

FILENAME=$(basename "$LATEST_PDF")
BASE_FILENAME="${FILENAME%.pdf}"
SUPABASE_URL="https://wzldwfbsadmnhqofifco.supabase.co/storage/v1/object/public/pdfs/$FILENAME"

echo ""
echo "✅ Export complete!"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  📤 UPLOAD INFORMATION"
echo "═══════════════════════════════════════════════════════════"
echo "  Deck ID: $DECK_ID"
echo "  Filename: $FILENAME"
echo "  Base Name: $BASE_FILENAME"
echo "  Supabase URL: $SUPABASE_URL"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Output JSON for AI processing
echo "--- JSON_OUTPUT_START ---"
cat << EOF
{
  "deckId": "$DECK_ID",
  "filename": "$FILENAME",
  "baseFilename": "$BASE_FILENAME",
  "supabaseUrl": "$SUPABASE_URL",
  "success": true
}
EOF
echo ""
echo "--- JSON_OUTPUT_END ---"
echo ""
echo "✅ Ready for Google Drive upload and cleanup!"

