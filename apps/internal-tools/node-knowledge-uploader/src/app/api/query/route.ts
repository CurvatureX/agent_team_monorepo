import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import { supabase } from '@/lib/supabase';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Error types for better error handling
enum ErrorType {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  OPENAI_ERROR = 'OPENAI_ERROR',
  DATABASE_ERROR = 'DATABASE_ERROR',
  NETWORK_ERROR = 'NETWORK_ERROR',
  RATE_LIMIT_ERROR = 'RATE_LIMIT_ERROR',
  INTERNAL_ERROR = 'INTERNAL_ERROR'
}

interface ErrorDetails {
  type: ErrorType;
  message: string;
  userMessage: string;
  retryable: boolean;
  retryAfter?: number;
}

// Request interface
interface QueryRequest {
  query: string;
  limit?: number;
  threshold?: number;
  nodeTypeFilter?: string;
}

// Search result interface
interface SearchResult {
  id: string;
  node_type: string;
  node_subtype: string | null;
  title: string;
  description: string;
  content: string;
  similarity: number;
  metadata: Record<string, any>;
}

// Response interface
interface QueryResponse {
  success: boolean;
  results: SearchResult[];
  query: string;
  processingTime: number;
  totalCount: number;
  error?: string;
}

// Enhanced error classification function
function classifyError(error: any): ErrorDetails {
  // OpenAI API errors
  if (error?.error?.type === 'insufficient_quota') {
    return {
      type: ErrorType.OPENAI_ERROR,
      message: 'OpenAI quota exceeded',
      userMessage: 'Search service is temporarily unavailable due to quota limits. Please try again later.',
      retryable: true,
      retryAfter: 3600 // 1 hour
    };
  }

  if (error?.error?.type === 'rate_limit_exceeded') {
    return {
      type: ErrorType.RATE_LIMIT_ERROR,
      message: 'OpenAI rate limit exceeded',
      userMessage: 'Too many requests. Please wait a moment and try again.',
      retryable: true,
      retryAfter: 60 // 1 minute
    };
  }

  if (error?.status === 401 || error?.error?.type === 'invalid_api_key') {
    return {
      type: ErrorType.OPENAI_ERROR,
      message: 'OpenAI API authentication failed',
      userMessage: 'Search service configuration error. Please contact support.',
      retryable: false
    };
  }

  if (error?.status >= 500 && error?.status < 600) {
    return {
      type: ErrorType.OPENAI_ERROR,
      message: 'OpenAI API server error',
      userMessage: 'Search service is temporarily unavailable. Please try again in a few minutes.',
      retryable: true,
      retryAfter: 300 // 5 minutes
    };
  }

  // Database/Supabase errors
  if (error?.code === 'PGRST116' || error?.message?.includes('connection')) {
    return {
      type: ErrorType.DATABASE_ERROR,
      message: 'Database connection failed',
      userMessage: 'Database is temporarily unavailable. Please try again in a moment.',
      retryable: true,
      retryAfter: 30
    };
  }

  if (error?.code?.startsWith('PGRST') || error?.message?.includes('database')) {
    return {
      type: ErrorType.DATABASE_ERROR,
      message: 'Database query failed',
      userMessage: 'Search failed due to a database error. Please try again.',
      retryable: true,
      retryAfter: 10
    };
  }

  // Network errors
  if (error?.code === 'ENOTFOUND' || error?.code === 'ECONNREFUSED' || error?.code === 'ETIMEDOUT') {
    return {
      type: ErrorType.NETWORK_ERROR,
      message: 'Network connection failed',
      userMessage: 'Network error occurred. Please check your connection and try again.',
      retryable: true,
      retryAfter: 30
    };
  }

  // Default to internal error
  return {
    type: ErrorType.INTERNAL_ERROR,
    message: error?.message || 'Unknown error occurred',
    userMessage: 'An unexpected error occurred. Please try again.',
    retryable: true,
    retryAfter: 60
  };
}

// Enhanced embedding generation with retry logic
async function generateEmbedding(text: string, retryCount = 0): Promise<number[]> {
  const maxRetries = 3;
  const baseDelay = 1000; // 1 second

  try {
    const response = await openai.embeddings.create({
      model: 'text-embedding-ada-002',
      input: text,
    });
    return response.data[0].embedding;
  } catch (error) {
    console.error(`Error generating embedding (attempt ${retryCount + 1}):`, error);

    const errorDetails = classifyError(error);

    // If retryable and we haven't exceeded max retries
    if (errorDetails.retryable && retryCount < maxRetries) {
      const delay = Math.min(baseDelay * Math.pow(2, retryCount), 10000); // Exponential backoff, max 10s
      console.log(`Retrying embedding generation in ${delay}ms...`);

      await new Promise(resolve => setTimeout(resolve, delay));
      return generateEmbedding(text, retryCount + 1);
    }

    // Attach error details for better handling upstream
    (error as any).errorDetails = errorDetails;
    throw error;
  }
}

function validateQueryRequest(body: any): { isValid: boolean; error?: string; data?: QueryRequest } {
  // Check if query is provided and is a string
  if (!body.query || typeof body.query !== 'string') {
    return { isValid: false, error: 'Query is required and must be a string' };
  }

  // Check query length (reasonable limits)
  if (body.query.trim().length === 0) {
    return { isValid: false, error: 'Query cannot be empty' };
  }

  if (body.query.length > 1000) {
    return { isValid: false, error: 'Query is too long (maximum 1000 characters)' };
  }

  // Validate optional parameters
  const limit = body.limit ? parseInt(body.limit) : 10;
  if (isNaN(limit) || limit < 1 || limit > 50) {
    return { isValid: false, error: 'Limit must be a number between 1 and 50' };
  }

  const threshold = body.threshold ? parseFloat(body.threshold) : 0.3;
  if (isNaN(threshold) || threshold < 0 || threshold > 1) {
    return { isValid: false, error: 'Threshold must be a number between 0 and 1' };
  }

  const nodeTypeFilter = body.nodeTypeFilter && typeof body.nodeTypeFilter === 'string'
    ? body.nodeTypeFilter.trim()
    : undefined;

  return {
    isValid: true,
    data: {
      query: body.query.trim(),
      limit,
      threshold,
      nodeTypeFilter: nodeTypeFilter || undefined
    }
  };
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    // Parse request body
    let body;
    try {
      body = await request.json();
    } catch (error) {
      return NextResponse.json({
        success: false,
        error: 'Invalid JSON in request body',
        results: [],
        query: '',
        processingTime: Date.now() - startTime,
        totalCount: 0
      } as QueryResponse, { status: 400 });
    }

    // Validate request
    const validation = validateQueryRequest(body);
    if (!validation.isValid) {
      return NextResponse.json({
        success: false,
        error: validation.error,
        results: [],
        query: body.query || '',
        processingTime: Date.now() - startTime,
        totalCount: 0
      } as QueryResponse, { status: 400 });
    }

    const { query, limit, threshold, nodeTypeFilter } = validation.data!;

    console.log(`Processing query: "${query}" with limit: ${limit}, threshold: ${threshold}, filter: ${nodeTypeFilter || 'none'}`);

    // Generate embedding for the query with enhanced error handling
    let queryEmbedding: number[];
    try {
      queryEmbedding = await generateEmbedding(query);
    } catch (error) {
      console.error('OpenAI embedding generation failed:', error);

      const errorDetails = (error as any).errorDetails || classifyError(error);
      const statusCode = errorDetails.type === ErrorType.RATE_LIMIT_ERROR ? 429 : 503;

      const response: QueryResponse = {
        success: false,
        error: errorDetails.userMessage,
        results: [],
        query,
        processingTime: Date.now() - startTime,
        totalCount: 0
      };

      // Add retry-after header for rate limiting
      const headers: Record<string, string> = {};
      if (errorDetails.retryAfter) {
        headers['Retry-After'] = errorDetails.retryAfter.toString();
      }

      return NextResponse.json(response, {
        status: statusCode,
        headers
      });
    }

    // Perform vector similarity search with enhanced error handling and retry logic
    let searchResults;
    const maxDbRetries = 2;
    let dbRetryCount = 0;

    while (dbRetryCount <= maxDbRetries) {
      try {
        const { data, error } = await supabase.rpc('match_node_knowledge', {
          query_embedding: queryEmbedding,
          match_threshold: threshold,
          match_count: limit,
          node_type_filter: nodeTypeFilter || null
        });

        if (error) {
          console.error('Database search error:', error);
          throw error;
        }

        searchResults = data || [];
        break; // Success, exit retry loop

      } catch (error) {
        console.error(`Vector search failed (attempt ${dbRetryCount + 1}):`, error);

        const errorDetails = classifyError(error);

        // If retryable and we haven't exceeded max retries
        if (errorDetails.retryable && dbRetryCount < maxDbRetries) {
          dbRetryCount++;
          const delay = 1000 * dbRetryCount; // Linear backoff for DB
          console.log(`Retrying database search in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        // Final failure
        const statusCode = errorDetails.type === ErrorType.DATABASE_ERROR ? 503 : 500;
        const response: QueryResponse = {
          success: false,
          error: errorDetails.userMessage,
          results: [],
          query,
          processingTime: Date.now() - startTime,
          totalCount: 0
        };

        const headers: Record<string, string> = {};
        if (errorDetails.retryAfter) {
          headers['Retry-After'] = errorDetails.retryAfter.toString();
        }

        return NextResponse.json(response, {
          status: statusCode,
          headers
        });
      }
    }

    // Format results according to the SearchResult interface
    const formattedResults: SearchResult[] = searchResults.map((result: any) => ({
      id: result.id,
      node_type: result.node_type,
      node_subtype: result.node_subtype,
      title: result.title,
      description: result.description,
      content: result.content,
      similarity: Math.round(result.similarity * 100) / 100, // Round to 2 decimal places
      metadata: result.metadata || {}
    }));

    const processingTime = Date.now() - startTime;

    console.log(`Query completed: ${formattedResults.length} results found in ${processingTime}ms`);

    // Return successful response
    return NextResponse.json({
      success: true,
      results: formattedResults,
      query,
      processingTime,
      totalCount: formattedResults.length
    } as QueryResponse);

  } catch (error) {
    console.error('Unexpected error in query API:', error);

    const errorDetails = classifyError(error);
    const response: QueryResponse = {
      success: false,
      error: errorDetails.userMessage,
      results: [],
      query: '',
      processingTime: Date.now() - startTime,
      totalCount: 0
    };

    const headers: Record<string, string> = {};
    if (errorDetails.retryAfter) {
      headers['Retry-After'] = errorDetails.retryAfter.toString();
    }

    return NextResponse.json(response, {
      status: 500,
      headers
    });
  }
}

// GET method to check API status and get database info with enhanced error handling
export async function GET() {
  try {
    // Check OpenAI API availability first
    let openaiAvailable = true;
    try {
      // Simple test to check if OpenAI API is accessible
      if (!process.env.OPENAI_API_KEY) {
        throw new Error('OpenAI API key not configured');
      }
    } catch (error) {
      console.error('OpenAI API check failed:', error);
      openaiAvailable = false;
    }

    // Get current count of records in the database with retry
    let count = 0;
    let databaseAvailable = true;
    const maxRetries = 2;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const { count: dbCount, error } = await supabase
          .from('node_knowledge_vectors')
          .select('*', { count: 'exact', head: true });

        if (error) {
          throw error;
        }

        count = dbCount || 0;
        break;
      } catch (error) {
        console.error(`Database status check failed (attempt ${attempt + 1}):`, error);

        if (attempt === maxRetries) {
          databaseAvailable = false;
          const errorDetails = classifyError(error);

          return NextResponse.json({
            error: errorDetails.userMessage,
            available: false,
            openaiAvailable,
            databaseAvailable: false,
            totalNodes: 0
          }, { status: 503 });
        }

        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
      }
    }

    const overallAvailable = openaiAvailable && databaseAvailable;

    return NextResponse.json({
      available: overallAvailable,
      openaiAvailable,
      databaseAvailable,
      totalNodes: count,
      message: overallAvailable
        ? 'Query API is ready'
        : 'Query API has limited functionality'
    });
  } catch (error) {
    console.error('Unexpected error in status check:', error);
    const errorDetails = classifyError(error);

    return NextResponse.json({
      error: errorDetails.userMessage,
      available: false,
      openaiAvailable: false,
      databaseAvailable: false,
      totalNodes: 0
    }, { status: 500 });
  }
}
