# Requirements Document

## Introduction

This feature adds RAG (Retrieval-Augmented Generation) query capabilities to the existing node-knowledge-uploader application. Users will be able to input natural language queries to search and retrieve relevant node knowledge from the vector database, leveraging the existing embeddings infrastructure. This transforms the application from a write-only knowledge uploader into a comprehensive knowledge management system with both upload and retrieval capabilities.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to search for relevant node knowledge using natural language queries, so that I can quickly find specific information about workflow nodes without manually browsing through all stored data.

#### Acceptance Criteria

1. WHEN a user enters a search query THEN the system SHALL generate an embedding for the query using the same OpenAI model (text-embedding-ada-002) used for storage
2. WHEN the query embedding is generated THEN the system SHALL perform a vector similarity search against the node_knowledge_vectors table using pgvector
3. WHEN the similarity search is performed THEN the system SHALL return the top 10 most relevant results ranked by cosine similarity
4. WHEN results are returned THEN the system SHALL display each result with node type, subtype, title, description, and similarity score
5. IF no results meet a minimum similarity threshold THEN the system SHALL display a "No relevant results found" message

### Requirement 2

**User Story:** As a user, I want to see detailed information about search results, so that I can understand the context and capabilities of each node type without having to remember all details.

#### Acceptance Criteria

1. WHEN search results are displayed THEN each result SHALL show the node type, subtype, title, and truncated description by default
2. WHEN a user clicks on a result THEN the system SHALL expand to show the full content including all capabilities and detailed descriptions
3. WHEN results are displayed THEN the system SHALL show the similarity score as a percentage to indicate relevance
4. WHEN multiple results have the same node type THEN the system SHALL group them visually while maintaining individual similarity scores
5. WHEN a result is expanded THEN the system SHALL highlight query-relevant keywords in the content

### Requirement 3

**User Story:** As a user, I want the search interface to be intuitive and responsive, so that I can efficiently explore the knowledge base without technical complexity.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a prominent search input field with placeholder text explaining the functionality
2. WHEN a user types a query THEN the system SHALL provide real-time feedback about query length and processing status
3. WHEN a search is initiated THEN the system SHALL show a loading indicator and disable the search button to prevent duplicate requests
4. WHEN search results are returned THEN the system SHALL display them in a clean, scannable format with clear visual hierarchy
5. WHEN no query is entered THEN the system SHALL show example queries to guide user interaction

### Requirement 4

**User Story:** As a user, I want to see search history and be able to refine my queries, so that I can iteratively explore related concepts and build upon previous searches.

#### Acceptance Criteria

1. WHEN a user performs a search THEN the system SHALL store the query in local browser storage for the current session
2. WHEN the search interface is displayed THEN the system SHALL show the last 5 recent queries as clickable suggestions
3. WHEN a user clicks a recent query THEN the system SHALL automatically populate the search field and execute the search
4. WHEN search results are displayed THEN the system SHALL provide a "Clear results" option to reset the interface
5. WHEN a user performs a new search THEN the system SHALL replace previous results while maintaining the query history

### Requirement 5

**User Story:** As a developer, I want the search functionality to integrate seamlessly with the existing upload interface, so that I can both contribute to and consume the knowledge base in a unified experience.

#### Acceptance Criteria

1. WHEN the application loads THEN the system SHALL display both upload and search functionality in a tabbed or sectioned interface
2. WHEN a user uploads new knowledge THEN the system SHALL provide an option to immediately search the newly added content
3. WHEN search results are displayed THEN the system SHALL show the total count of available nodes in the database for context
4. WHEN the database is empty THEN the system SHALL display a message encouraging users to upload knowledge first
5. WHEN switching between upload and search modes THEN the system SHALL preserve the state of both interfaces without losing user input
