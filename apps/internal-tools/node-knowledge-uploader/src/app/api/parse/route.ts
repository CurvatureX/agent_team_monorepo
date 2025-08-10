import { NextRequest, NextResponse } from 'next/server';
import { parseNodeKnowledge, NodeKnowledge } from '@/lib/nodeKnowledgeParser';

export async function POST(request: NextRequest) {
  try {
    console.log('📥 Parse API: Request received');

    const { content } = await request.json();
    console.log('📄 Parse API: Content length:', content?.length || 0);

    if (!content) {
      return NextResponse.json({ error: 'Content is required' }, { status: 400 });
    }

    // Check environment variables
    console.log('🔐 Parse API: Checking environment variables...');
    console.log('🔐 OPENAI_API_KEY exists:', !!process.env.OPENAI_API_KEY);
    console.log('🔐 OPENAI_API_KEY length:', process.env.OPENAI_API_KEY?.length || 0);

    console.log('🚀 Parse API: Starting OpenAI-powered parsing...');

    // Add timeout wrapper
    const parseWithTimeout = Promise.race([
      parseNodeKnowledge(content),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('OpenAI parsing timeout after 30 seconds')), 30000)
      )
    ]);

    const parsedNodes = await parseWithTimeout as NodeKnowledge[];

    console.log(`🎯 Parse API: OpenAI parsing complete - ${parsedNodes.length} nodes extracted`);

    return NextResponse.json({
      success: true,
      message: `Successfully parsed ${parsedNodes.length} nodes with OpenAI`,
      nodes: parsedNodes,
      count: parsedNodes.length
    });

  } catch (error) {
    console.error('❌ Parse API error:', error);
    console.error('❌ Error details:', {
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
      name: error instanceof Error ? error.name : undefined
    });

    return NextResponse.json(
      {
        error: 'Failed to parse content',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
