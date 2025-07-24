# Input Examples for RAG Comparison Demo

## ✅ Simple Input (Recommended)

In LangGraph Studio, paste this JSON as input:

```json
{
  "query": "What is an AI agent node and how does it work?",
  "node_type": "",
  "response_with_rag": "",
  "response_without_rag": "",
  "context": ""
}
```

## 🎯 Sample Queries to Try

### AI Agent Questions

```json
{
  "query": "How do I use an AI agent node to analyze data?",
  "node_type": "",
  "response_with_rag": "",
  "response_without_rag": "",
  "context": ""
}
```

### Trigger Node Questions

```json
{
  "query": "How do I set up a webhook trigger?",
  "node_type": "",
  "response_with_rag": "",
  "response_without_rag": "",
  "context": ""
}
```

### Memory Node Questions

```json
{
  "query": "What types of memory nodes are available?",
  "node_type": "",
  "response_with_rag": "",
  "response_without_rag": "",
  "context": ""
}
```

### Flow Control Questions

```json
{
  "query": "How do I create conditional branching in my workflow?",
  "node_type": "",
  "response_with_rag": "",
  "response_without_rag": "",
  "context": ""
}
```

## 📝 Notes

- **Only the `query` field matters** - put your question there
- Leave all other fields as empty strings (`""`)
- The system will automatically search across all node types for relevant information
- You'll get three outputs:
  1. **Response with RAG** - Answer using retrieved context
  2. **Response without RAG** - Answer using only AI training data
  3. **Comparison** - Analysis of the differences between both responses

## 🚀 Expected Output

The workflow will return:

- `response_with_rag`: Detailed, context-aware answer
- `response_without_rag`: General answer based on training data
- `context`: The retrieved information used for RAG
- `comparison`: Analysis of which response is better and why
