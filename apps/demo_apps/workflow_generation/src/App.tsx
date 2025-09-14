import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { CanvasPage } from './components/CanvasPage';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background text-foreground">
        <Routes>
          {/* Redirect root to canvas */}
          <Route path="/" element={<Navigate to="/canvas" replace />} />
          {/* Main canvas page - matches http://localhost:3000/canvas pattern */}
          <Route path="/canvas" element={<CanvasPage />} />
          {/* Keep workflow detail as a query parameter or state within canvas */}
          <Route path="/canvas/:workflowId" element={<CanvasPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
