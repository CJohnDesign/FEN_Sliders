import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { BUILDER_CONFIG } from '../config/builder.config';

// Simple in-memory store for rate limiting
const rateLimitStore = new Map<string, { count: number; resetTime: number }>();

export function rateLimit(request: NextRequest) {
  const ip = request.ip ?? 'unknown';
  const now = Date.now();
  
  // Clean up expired entries
  for (const [key, value] of rateLimitStore.entries()) {
    if (value.resetTime < now) {
      rateLimitStore.delete(key);
    }
  }
  
  // Get or create rate limit info for this IP
  let rateLimit = rateLimitStore.get(ip);
  if (!rateLimit || rateLimit.resetTime < now) {
    rateLimit = {
      count: 0,
      resetTime: now + BUILDER_CONFIG.rateLimit.windowMs
    };
  }
  
  // Increment count
  rateLimit.count++;
  rateLimitStore.set(ip, rateLimit);
  
  // Check if rate limit exceeded
  if (rateLimit.count > BUILDER_CONFIG.rateLimit.max) {
    return NextResponse.json({
      error: 'Too many requests',
      retryAfter: Math.ceil((rateLimit.resetTime - now) / 1000)
    }, { 
      status: 429,
      headers: {
        'Retry-After': Math.ceil((rateLimit.resetTime - now) / 1000).toString()
      }
    });
  }
  
  return null;
} 