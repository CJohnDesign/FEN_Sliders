/**
 * YouTube upload configuration
 * 
 * To get your Supabase anon key:
 * https://supabase.com/dashboard/project/wzldwfbsadmnhqofifco/settings/api
 */

export default {
  supabase: {
    url: 'https://wzldwfbsadmnhqofifco.supabase.co',
    anonKey: process.env.SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind6bGR3ZmJzYWRtbmhxb2ZpZmNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU1NTI5NDcsImV4cCI6MjA2MTEyODk0N30.UzLsJEVEmjuY9kzmkMOY2EC8Wyne1cWSeP3GIVpbH0A',
  },
  youtube: {
    channelName: 'firstenroll',
    privacyStatus: 'unlisted', // 'public', 'private', or 'unlisted'
    madeForKids: false,
    category: '22', // People & Blogs
  }
};

