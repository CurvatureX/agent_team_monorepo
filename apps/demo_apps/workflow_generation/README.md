# Workflow Visualization App

A modern React application that converts JSON workflow definitions to Mermaid diagrams and visualizes them in the browser.

## Features

- **JSON Input**: Paste your workflow JSON and see it visualized instantly
- **Mermaid Generation**: Automatically converts workflow nodes to Mermaid flowchart syntax
- **Real-time Visualization**: See your workflow diagram update as you modify the JSON
- **Node Type Support**: Supports different node types (trigger, ai_agent, switch, ai_tool, webhook)
- **Modern UI**: Clean, responsive design with Tailwind CSS

## Getting Started

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```

3. **Open your browser** and navigate to `http://localhost:3000`

## Usage

1. **Load Example**: Click "Load Example" to see a sample workflow
2. **Edit JSON**: Modify the JSON in the left panel to customize your workflow
3. **Generate Diagram**: Click "Generate Mermaid Diagram" or it will auto-update
4. **View Results**: See the generated Mermaid diagram and code on the right

## JSON Format

The app expects a JSON object with the following structure:

```json
{
  "id": "workflow-id",
  "name": "Workflow Name",
  "active": true,
  "nodes": [
    {
      "id": "node-id",
      "name": "Node Name",
      "type": "trigger|ai_agent|switch|ai_tool|webhook",
      "position": { "x": 100, "y": 100 },
      "parameters": {}
    }
  ],
  "edges": [
    {
      "id": "edge-id",
      "source": "source-node-id",
      "target": "target-node-id"
    }
  ]
}
```

## Node Types

- **trigger**: Circular nodes `([Label])`
- **ai_agent**: Hexagon nodes `{{Label}}`
- **switch**: Diamond nodes `{Label}`
- **ai_tool**: Rectangle nodes `[Label]`
- **webhook**: Circle nodes `((Label))`

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Technologies Used

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Mermaid.js
