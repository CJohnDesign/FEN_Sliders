import { createClient } from '@supabase/supabase-js';
import config from './scripts/youtube.config.js';

const supabase = createClient(config.supabase.url, config.supabase.anonKey);
const { error } = await supabase.storage
  .from('pdfs')
  .remove(['FEN_STG_006.pdf']);

if (error) {
  console.error('Delete failed:', error.message);
  process.exit(1);
} else {
  console.log('✅ Cleaned up FEN_STG_006.pdf from Supabase');
}

