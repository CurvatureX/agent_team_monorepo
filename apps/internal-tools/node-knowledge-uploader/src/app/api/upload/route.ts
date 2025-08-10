import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import { supabase } from '@/lib/supabase';
import { parseNodeKnowledge, NodeKnowledge } from '@/lib/nodeKnowledgeParser';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

async function generateEmbedding(text: string): Promise<number[]> {
  try {
    const response = await openai.embeddings.create({
      model: 'text-embedding-ada-002',
      input: text,
    });
    return response.data[0].embedding;
  } catch (error) {
    console.error('Error generating embedding:', error);
    throw error;
  }
}

export async function POST(request: NextRequest) {
  try {
    const { content, overwrite = false, append = false, useStructuredData = false } = await request.json();

    if (!content) {
      return NextResponse.json({ error: 'Content is required' }, { status: 400 });
    }

    let parsedNodes: NodeKnowledge[];

    // Handle structured data or parse from text
    if (useStructuredData) {
      try {
        parsedNodes = JSON.parse(content);
        console.log(`Using ${parsedNodes.length} pre-structured nodes`);
      } catch (error) {
        return NextResponse.json({ error: 'Invalid structured data format' }, { status: 400 });
      }
    } else {
      // Parse the node knowledge from text using OpenAI
      console.log('🚀 Starting OpenAI-powered parsing...');
      parsedNodes = await parseNodeKnowledge(content);
      console.log(`🎯 OpenAI parsing complete: ${parsedNodes.length} nodes extracted`);
    }

    // Handle different upload modes
    if (!overwrite && !append) {
      // Check mode: only upload if database is empty
      const { count } = await supabase
        .from('node_knowledge_vectors')
        .select('*', { count: 'exact', head: true });

      if (count && count > 0) {
        return NextResponse.json({
          error: 'Data already exists in the database. Use append mode to add new records or overwrite mode to replace existing data.',
          existingCount: count
        }, { status: 400 });
      }
    } else if (overwrite && !append) {
      // Overwrite mode: clear existing data first
      console.log('🗑️ Overwrite mode: Clearing existing data...');
      const { error: deleteError } = await supabase
        .from('node_knowledge_vectors')
        .delete()
        .neq('id', '00000000-0000-0000-0000-000000000000'); // Delete all records

      if (deleteError) {
        console.error('Error clearing existing data:', deleteError);
        return NextResponse.json({ error: 'Failed to clear existing data' }, { status: 500 });
      }
      console.log('✅ Existing data cleared successfully');
    } else if (append) {
      // Append mode: just add new records, no checks or clearing needed
      console.log('➕ Append mode: Adding new records to existing data...');
    }

    const results: any[] = [];
    const errors: any[] = [];

    // Process each node
    for (let i = 0; i < parsedNodes.length; i++) {
      const node = parsedNodes[i];

      try {
        console.log(`Processing node ${i + 1}/${parsedNodes.length}: ${node.nodeType} - ${node.nodeSubtype}`);

        // Generate embedding for the content
        const embeddingText = `${node.title}\n${node.description}\n${node.content}`;
        const embedding = await generateEmbedding(embeddingText);

        // Insert into database
        const { data, error } = await supabase
          .from('node_knowledge_vectors')
          .insert({
            node_type: node.nodeType,
            node_subtype: node.nodeSubtype,
            title: node.title,
            description: node.description,
            content: node.content,
            embedding: embedding,
            metadata: {},
          })
          .select()
          .single();

        if (error) {
          console.error(`Error inserting node ${node.nodeType} - ${node.nodeSubtype}:`, error);
          errors.push({
            node: `${node.nodeType} - ${node.nodeSubtype}`,
            error: error.message
          });
        } else {
          results.push(data);
        }

        // Add a small delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 100));

      } catch (error) {
        console.error(`Error processing node ${node.nodeType} - ${node.nodeSubtype}:`, error);
        errors.push({
          node: `${node.nodeType} - ${node.nodeSubtype}`,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    // Create success message based on upload mode
    let message = `Processed ${parsedNodes.length} nodes`;
    if (overwrite && !append) {
      message = `Overwrite complete: Replaced all data with ${results.length} new nodes`;
    } else if (append) {
      message = `Append complete: Added ${results.length} new nodes to existing data`;
    } else {
      message = `Upload complete: Added ${results.length} nodes to empty database`;
    }

    return NextResponse.json({
      success: true,
      message,
      inserted: results.length,
      errors: errors.length,
      errorDetails: errors.length > 0 ? errors : undefined
    });

  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    // Get current count of records
    const { count, error } = await supabase
      .from('node_knowledge_vectors')
      .select('*', { count: 'exact', head: true });

    if (error) {
      return NextResponse.json({ error: 'Failed to fetch data' }, { status: 500 });
    }

    return NextResponse.json({
      currentCount: count || 0
    });
  } catch (error) {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
