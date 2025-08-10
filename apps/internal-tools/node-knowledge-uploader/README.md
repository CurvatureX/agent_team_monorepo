# Node Knowledge Uploader

A Next.js application to upload and process node knowledge data into a Supabase database with vector embeddings.

## Features

- Parse structured node knowledge text into individual entries
- Generate OpenAI embeddings for semantic search
- Upload data to Supabase with vector storage
- Real-time preview of parsed nodes
- Overwrite protection and batch processing
- Error handling and detailed reporting

## Prerequisites

1. **Supabase Database** with the `node_knowledge_vectors` table created
2. **OpenAI API Key** for generating embeddings
3. **Node.js** and **npm** installed

## Setup

### 1. Environment Variables

Create a `.env.local` file in the project root with the following variables:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your_supabase_publishable_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
```

### 2. Database Setup

Ensure your Supabase database has the `node_knowledge_vectors` table created using the migration:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the table (from your migration file)
CREATE TABLE node_knowledge_vectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(50) NOT NULL,
    node_subtype VARCHAR(100) NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Install Dependencies

```bash
npm install
```

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

### 1. Content Format

The application expects node knowledge in this specific format:

```
Node Type: NODE_TYPE_NAME
Description: Brief description of the node type.
Subtypes:
- SUBTYPE_NAME: Description of the subtype.
- ANOTHER_SUBTYPE: Another description.

Node Type: ANOTHER_NODE_TYPE
Description: Another node type description.
Subtypes:
- SUBTYPE_1: Description with capabilities.
- Capabilities:
  * Capability 1
  * Capability 2
```

### 2. Upload Process

1. **Paste Content**: The default node knowledge is pre-loaded, or paste your own content
2. **Preview**: Check the parsed nodes in the preview panel
3. **Configure**: Choose whether to overwrite existing data
4. **Upload**: Click "Upload to Supabase" to process and store the data

### 3. Processing Steps

The application will:

1. Parse the text content into structured node data
2. Generate OpenAI embeddings for each node (using text-embedding-ada-002)
3. Insert the data into the Supabase database
4. Provide detailed results and error reporting

## Data Structure

Each parsed node becomes a database record with:

- `node_type`: Main node category (e.g., "TRIGGER_NODE")
- `node_subtype`: Specific subtype (e.g., "TRIGGER_CHAT")
- `title`: Combined title for display
- `description`: Node description
- `content`: Full content including capabilities
- `embedding`: 1536-dimension vector for semantic search
- `metadata`: Additional JSON metadata

## Error Handling

The application provides comprehensive error handling:

- Validation of required environment variables
- OpenAI API rate limiting with delays
- Supabase connection and query errors
- Detailed error reporting for failed node insertions
- Protection against accidental data overwrites

## API Endpoints

### POST /api/upload

Upload node knowledge data.

**Request Body:**

```json
{
  "content": "Node knowledge text...",
  "overwrite": false
}
```

**Response:**

```json
{
  "success": true,
  "message": "Processed 45 nodes",
  "inserted": 45,
  "errors": 0
}
```

### GET /api/upload

Get current database status.

**Response:**

```json
{
  "currentCount": 45
}
```

## Development

### Project Structure

```
src/
├── app/
│   ├── api/upload/          # API routes
│   └── page.tsx             # Main UI
├── lib/
│   ├── supabase.ts          # Supabase client config
│   └── nodeKnowledgeParser.ts  # Text parsing logic
```

### Key Components

- **Parser**: Extracts structured data from text format
- **Embeddings**: Generates OpenAI vectors for semantic search
- **Database**: Stores data with pgvector support
- **UI**: Real-time preview and upload interface

## Troubleshooting

### Common Issues

1. **Environment Variables**: Ensure all required env vars are set
2. **Database Connection**: Check Supabase URL and publishable key
3. **OpenAI Limits**: API rate limiting may cause delays
4. **pgvector Extension**: Ensure vector extension is enabled in Supabase

### Error Messages

- `"Data already exists"`: Use overwrite option or clear data manually
- `"Content is required"`: Provide valid node knowledge text
- `"Failed to generate embedding"`: Check OpenAI API key and limits
- `"Database connection failed"`: Verify Supabase credentials (URL and publishable key)

## License

This project is part of the internal tools suite.
