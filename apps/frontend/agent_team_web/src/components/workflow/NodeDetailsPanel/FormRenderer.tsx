"use client";

import React, { useMemo } from 'react';
import type { ParameterSchema, SchemaProperty } from '@/types/node-template';
import {
  TextField,
  SelectField,
  BooleanField,
  NumberField,
  ArrayField,
} from './fields';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface FormRendererProps {
  schema: ParameterSchema;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  errors?: Record<string, string>;
}

export const FormRenderer: React.FC<FormRendererProps> = ({
  schema,
  values,
  onChange,
  errors = {},
}) => {
  const handleFieldChange = (fieldName: string, fieldValue: unknown) => {
    onChange({
      ...values,
      [fieldName]: fieldValue,
    });
  };

  const renderField = (name: string, property: SchemaProperty, value: unknown) => {
    const commonProps = {
      name,
      value,
      onChange: (val: unknown) => handleFieldChange(name, val),
      required: schema.required?.includes(name),
      error: errors[name],
    };

    switch (property.type) {
      case 'string':
        if (property.enum) {
          return (
            <SelectField
              {...commonProps}
              value={typeof value === 'string' ? value : ''}
              options={property.enum}
            />
          );
        }
        return <TextField {...commonProps} value={typeof value === 'string' ? value : ''} />;

      case 'boolean':
        return <BooleanField {...commonProps} value={typeof value === 'boolean' ? value : false} />;

      case 'integer':
      case 'number':
        return (
          <NumberField
            {...commonProps}
            value={typeof value === 'number' ? value : 0}
            step={property.type === 'integer' ? 1 : 0.01}
          />
        );

      case 'array':
        // For now, assume string array. Could be enhanced for other types
        return <ArrayField {...commonProps} value={Array.isArray(value) ? value : []} />;

      case 'object':
        // For complex objects, we could recursively render
        // For now, just show a JSON editor
        return (
          <div className="space-y-2">
            <Label>{name}</Label>
            <Textarea
              value={JSON.stringify(value || {}, null, 2)}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  handleFieldChange(name, parsed);
                } catch {
                  // Invalid JSON, don't update
                }
              }}
              className="h-32 font-mono"
            />
          </div>
        );

      default:
        return null;
    }
  };

  const fields = useMemo(() => {
    if (!schema.properties) return [];
    
    return Object.entries(schema.properties).map(([name, property]) => ({
      name,
      property,
      value: values[name],
    }));
  }, [schema.properties, values]);

  return (
    <div className="space-y-4">
      {fields.map(({ name, property, value }) => (
        <div key={name}>
          {renderField(name, property, value)}
        </div>
      ))}
    </div>
  );
};