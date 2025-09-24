# AI Worker Dashboard

A comprehensive dashboard for monitoring and managing AI-powered workflows in real-time.

## Features

### 🏠 Homepage Dashboard
- **Card-based Layout**: AI Workers displayed in a responsive grid (4 per row on desktop)
- **Real-time Status**: Live status indicators (Active, Idle, Running, Error, Paused) with animated indicators
- **Quick Stats**: Last run time, next scheduled run, execution count for each worker
- **Status Overview**: Summary counts for each status type
- **Auto-refresh**: Real-time updates every 5 seconds

### 📊 Workflow Detail View
- **Top Navigation**: Horizontal scrollable workflow selector with status indicators
- **Tabbed Interface**:
  - **Overview**: Current execution status, trigger configuration, recent activity
  - **Graph**: Interactive workflow visualization using ReactFlow
  - **History**: Detailed execution history with filtering and search
  - **Logs**: Real-time execution logs with level filtering and auto-scroll

### 🔄 Real-time Features
- **Live Status Updates**: Workflow statuses update automatically
- **Running Execution Monitoring**: Real-time progress tracking for active executions
- **Live Log Streaming**: Continuous log updates during workflow execution
- **Auto-scroll Logs**: Optional auto-scroll to follow live log output

### 🎨 UI/UX Features
- **Responsive Design**: Mobile-friendly responsive layout
- **Loading States**: Smooth loading indicators throughout the app
- **Error Handling**: Graceful error states and user feedback
- **Accessibility**: Keyboard navigation and screen reader support
- **Modern UI**: Clean, professional design with Tailwind CSS

## Architecture

### Frontend Structure
```
src/
├── components/           # React components
│   ├── WorkerDashboard.tsx      # Main dashboard homepage
│   ├── WorkflowDetailView.tsx   # Detailed workflow view
│   ├── WorkflowGraph.tsx        # Interactive workflow visualization
│   ├── ExecutionHistory.tsx     # Execution history with search/filter
│   └── ExecutionLogs.tsx        # Real-time log viewer
├── data/                # Mock data and API responses
│   └── mockData.ts      # Sample AI workers and execution data
├── hooks/               # Custom React hooks
│   └── useApi.ts        # API integration hooks
├── services/            # API and external service integrations
│   └── api.ts           # Backend API client
├── types/               # TypeScript type definitions
│   └── index.ts         # Workflow, execution, and log types
└── utils/               # Utility functions
```

### Data Model
- **AIWorker**: Core workflow definition with metadata, graph, and execution history
- **ExecutionRecord**: Individual workflow run with timing, status, and results
- **NodeExecution**: Individual node execution within a workflow run
- **LogEntry**: Structured log entries with timestamps, levels, and node associations

### Integration Ready
The dashboard is designed to integrate with the existing monorepo backend:
- **API Service**: Pre-built HTTP client for all workflow operations
- **React Hooks**: Custom hooks for data fetching and real-time updates
- **SSE Support**: Server-Sent Events for real-time updates
- **Authentication**: JWT token support for secured API calls

## Usage

### Development
```bash
# Install dependencies
npm install

# Start development server (port 5554)
npm run dev

# Build for production
npm run build

# Run linting
npm run lint
```

### Backend Integration
To connect with the actual backend APIs:

1. **Environment Configuration**:
   ```env
   REACT_APP_API_URL=http://localhost:8000/api
   ```

2. **Replace Mock Data**:
   ```typescript
   // In components, replace mockData imports with API hooks
   import { useWorkflows } from '../hooks/useApi';

   // Instead of: const [workers] = useState(mockAIWorkers);
   const { workflows: workers, loading, error } = useWorkflows();
   ```

3. **Authentication**:
   ```typescript
   // Store JWT token in localStorage
   localStorage.setItem('auth_token', 'your-jwt-token');
   ```

### Key Endpoints Expected
- `GET /api/app/workflows` - List all workflows
- `GET /api/app/workflows/{id}` - Get workflow details
- `POST /api/app/workflows/{id}/execute` - Execute workflow
- `GET /api/app/executions/{id}` - Get execution status
- `GET /api/app/workflows/{id}/stream` - SSE for real-time updates

## Demo Data

The dashboard includes comprehensive mock data featuring 6 different AI workers:

1. **Customer Support Agent** - Event-triggered ticket processing
2. **Social Media Monitor** - Scheduled social media scanning
3. **Lead Qualification Bot** - Webhook-based lead scoring (currently running)
4. **Content Generator** - Scheduled content creation (error state)
5. **Invoice Processor** - File-upload triggered document processing (paused)
6. **DevOps Alert Manager** - Webhook-based incident management

Each worker includes:
- Realistic workflow graphs with multiple node types
- Execution history with various outcomes
- Detailed logs with different log levels
- Real-time execution simulation for active workflows

## Technology Stack

- **React 18** with TypeScript
- **React Router** for navigation
- **ReactFlow** for workflow visualization
- **Tailwind CSS** for styling
- **Lucide React** for icons
- **date-fns** for date formatting
- **clsx** for conditional classes
- **Vite** for build tooling

## Deployment

The dashboard is containerized and ready for deployment:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 5554
CMD ["npm", "run", "preview"]
```

The application runs on port 5554 and is fully self-contained with mock data for demonstration purposes.
