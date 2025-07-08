import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
  id?: string;
}

const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart, id = 'mermaid-diagram' }) => {
  const mermaidRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }
    });
  }, []);

  useEffect(() => {
    if (mermaidRef.current && chart) {
      mermaidRef.current.innerHTML = '';
      const uniqueId = `${id}-${Date.now()}`;
      
      mermaid.render(uniqueId, chart).then(({ svg }) => {
        if (mermaidRef.current) {
          mermaidRef.current.innerHTML = svg;
        }
      }).catch((error) => {
        console.error('Error rendering Mermaid diagram:', error);
        if (mermaidRef.current) {
          mermaidRef.current.innerHTML = '<div class="text-red-500">Error rendering diagram</div>';
        }
      });
    }
  }, [chart, id]);

  return (
    <div 
      ref={mermaidRef} 
      className="w-full h-full flex items-center justify-center bg-white rounded-lg border border-gray-200 shadow-sm"
    />
  );
};

export default MermaidDiagram;