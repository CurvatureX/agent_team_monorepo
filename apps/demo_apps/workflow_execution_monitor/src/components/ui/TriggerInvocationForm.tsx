import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Play,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
  Copy,
  ExternalLink
} from 'lucide-react';
import { apiClient } from '@/services/api';

interface TriggerInvocationFormProps {
  workflowId: string;
  triggerNodeId: string;
  triggerName: string;
  triggerType: string;
  onSuccess?: (result: any) => void;
  onError?: (error: string) => void;
}

interface TriggerSchema {
  trigger_type: string;
  schema: {
    type: string;
    properties: any;
    required: string[];
  };
  examples: any[];
  description: string;
  success: boolean;
}

interface ExecutionResult {
  success: boolean;
  workflow_id: string;
  trigger_node_id: string;
  execution_id: string;
  message: string;
  trigger_data: any;
  execution_url: string;
}

export const TriggerInvocationForm: React.FC<TriggerInvocationFormProps> = ({
  workflowId,
  triggerNodeId,
  triggerName,
  triggerType,
  onSuccess,
  onError
}) => {
  const [schema, setSchema] = useState<TriggerSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parameters, setParameters] = useState<any>({});
  const [description, setDescription] = useState('Manual trigger execution');
  const [result, setResult] = useState<ExecutionResult | null>(null);

  useEffect(() => {
    loadSchema();
  }, [workflowId, triggerNodeId]);

  const loadSchema = async () => {
    try {
      setLoading(true);
      setError(null);

      const schemaData = await apiClient.getTriggerSchema(triggerType);
      setSchema(schemaData);

      // Initialize parameters with examples if available
      if (schemaData.examples && schemaData.examples.length > 0) {
        setParameters(schemaData.examples[0]);
      }

    } catch (err) {
      console.error('Error loading trigger schema:', err);
      setError(err instanceof Error ? err.message : 'Failed to load trigger schema');
      onError?.(err instanceof Error ? err.message : 'Failed to load trigger schema');
    } finally {
      setLoading(false);
    }
  };

  const handleParameterChange = (key: string, value: any) => {
    setParameters((prev: any) => ({
      ...prev,
      [key]: value
    }));
  };

  const handleExampleLoad = (example: any) => {
    if (example.parameters) {
      setParameters(example.parameters);
    }
    if (example.description) {
      setDescription(example.description);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setSubmitting(true);
      setError(null);
      setResult(null);

      const result = await apiClient.manualInvokeTrigger(workflowId, triggerNodeId, {
        parameters,
        description
      });

      setResult(result);
      onSuccess?.(result);

    } catch (err) {
      console.error('Error invoking trigger:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to invoke trigger';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const copyExecutionId = () => {
    if (result?.execution_id) {
      navigator.clipboard.writeText(result.execution_id);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading trigger schema...</span>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="py-8 text-center">
        <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-2" />
        <p className="text-muted-foreground">Failed to load trigger schema</p>
        <button
          onClick={loadSchema}
          className="mt-2 px-3 py-1 bg-primary text-primary-foreground rounded text-sm hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    );
  }

  // With the new public API, all triggers support manual invocation
  // Remove the manual_invocation.supported check

  if (result) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="py-6 text-center space-y-4"
      >
        <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
        <div>
          <h3 className="text-lg font-semibold text-foreground">Execution Started!</h3>
          <p className="text-muted-foreground">{result.message}</p>
        </div>

        <div className="bg-muted p-4 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-foreground">Execution ID:</span>
            <div className="flex items-center gap-2">
              <code className="bg-background px-2 py-1 rounded text-xs">
                {result.execution_id}
              </code>
              <button
                onClick={copyExecutionId}
                className="p-1 hover:bg-accent rounded"
                title="Copy execution ID"
              >
                <Copy className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        <button
          onClick={() => setResult(null)}
          className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
        >
          Invoke Again
        </button>
      </motion.div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Trigger Information */}
      <div className="bg-muted p-4 rounded-lg">
        <h3 className="font-semibold text-foreground mb-2">Manual Trigger Invocation</h3>
        <p className="text-sm text-muted-foreground mb-2">
          {schema.manual_invocation.description}
        </p>
        <div className="text-xs text-muted-foreground">
          <span className="font-medium">Trigger Type:</span> {schema.trigger_type}
        </div>
      </div>

      {/* Example Parameters */}
      {schema.manual_invocation.parameter_examples.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-foreground text-sm">Quick Examples:</h4>
          <div className="grid gap-2">
            {schema.manual_invocation.parameter_examples.map((example, index) => (
              <button
                key={index}
                onClick={() => handleExampleLoad(example)}
                className="text-left p-2 bg-card border border-border rounded hover:bg-accent/50 transition-colors"
              >
                <div className="text-sm font-medium text-foreground">{example.name}</div>
                <div className="text-xs text-muted-foreground">{example.description}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Parameter Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Description
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground"
            placeholder="Describe this manual execution"
          />
        </div>

        {/* Dynamic Parameters */}
        {schema.schema?.properties && (
          <div className="space-y-3">
            <h4 className="font-medium text-foreground text-sm">Parameters:</h4>
            {Object.entries(schema.schema.properties).map(([key, prop]: [string, any]) => (
              <div key={key}>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {key}
                  {schema.schema.required?.includes(key) && (
                    <span className="text-destructive ml-1">*</span>
                  )}
                </label>
                {prop.description && (
                  <p className="text-xs text-muted-foreground mb-1">{prop.description}</p>
                )}

                {prop.type === 'object' ? (
                  <textarea
                    value={typeof parameters[key] === 'object' ? JSON.stringify(parameters[key], null, 2) : '{}'}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value);
                        handleParameterChange(key, parsed);
                      } catch {
                        // Keep invalid JSON as string for now
                        handleParameterChange(key, e.target.value);
                      }
                    }}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground font-mono text-sm"
                    rows={3}
                    placeholder="{}"
                  />
                ) : prop.enum ? (
                  <select
                    value={parameters[key] || ''}
                    onChange={(e) => handleParameterChange(key, e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground"
                  >
                    <option value="">Select {key}</option>
                    {prop.enum.map((option: string) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={prop.type === 'integer' || prop.type === 'number' ? 'number' : 'text'}
                    value={parameters[key] || ''}
                    onChange={(e) => handleParameterChange(key, e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground"
                    placeholder={prop.example || prop.default || `Enter ${key}`}
                  />
                )}
              </div>
            ))}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <AlertCircle className="w-4 h-4 text-destructive" />
            <span className="text-sm text-destructive">{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Invoking Trigger...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              <span>Invoke Trigger</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
