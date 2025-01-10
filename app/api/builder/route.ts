import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { BuilderService, BuilderInput } from '@/app/services/builder.service';
import { rateLimit } from '@/app/middleware/rateLimit';

export async function POST(req: NextRequest) {
  // Check rate limit
  const rateLimitResult = rateLimit(req);
  if (rateLimitResult) return rateLimitResult;
  
  try {
    // Parse and validate input
    const body = await req.json();
    const input = BuilderInput.parse(body);
    
    // Call builder service
    const result = await BuilderService.createDeck(input);
    
    return NextResponse.json({ result });
    
  } catch (error) {
    console.error('Builder API error:', error);
    
    if (error.name === 'ZodError') {
      return NextResponse.json({ 
        error: 'Invalid input format',
        details: error.errors 
      }, { status: 400 });
    }
    
    return NextResponse.json({ 
      error: 'Builder process failed',
      message: error.message
    }, { status: 500 });
  }
} 