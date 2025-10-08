"use client";

import React, { useMemo } from 'react';
import type { ParameterSchema, SchemaProperty } from '@/types/node-template';
import {
  TextField,
  SelectField,
  BooleanField,
  NumberField,
  ArrayField,
  PasswordField,
  TextareaField,
  MultiSelectField,
  DynamicSelectField,
  DynamicMultiSelectField,
  JsonEditorField,
} from './fields';

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
      required: property.required || schema.required?.includes(name),
      readonly: property.readonly || false,
      placeholder: property.placeholder,
      error: errors[name],
    };

    // Password fields (sensitive strings)
    if (property.type === 'string' && property.sensitive) {
      return (
        <PasswordField
          {...commonProps}
          value={value ? String(value) : ''}
        />
      );
    }

    // Multiline text fields (textarea)
    if (property.type === 'string' && property.multiline) {
      return (
        <TextareaField
          {...commonProps}
          value={value ? String(value) : ''}
          min={property.min}
          max={property.max}
        />
      );
    }

    // Dynamic select fields (API-driven dropdowns)
    if (property.api_endpoint) {
      return (
        <DynamicSelectField
          {...commonProps}
          value={value ? String(value) : ''}
          apiEndpoint={property.api_endpoint}
        />
      );
    }

    // String fields
    if (property.type === 'string') {
      if (property.enum) {
        return (
          <SelectField
            {...commonProps}
            value={value ? String(value) : ''}
            options={property.enum}
          />
        );
      }
      return <TextField {...commonProps} value={value ? String(value) : ''} />;
    }

    // Boolean fields
    if (property.type === 'boolean') {
      return <BooleanField {...commonProps} value={typeof value === 'boolean' ? value : false} />;
    }

    // Number fields
    if (property.type === 'integer' || property.type === 'number') {
      return (
        <NumberField
          {...commonProps}
          value={typeof value === 'number' ? value : 0}
          step={property.type === 'integer' ? 1 : 0.01}
          min={property.min}
          max={property.max}
        />
      );
    }

    // Array fields
    if (property.type === 'array') {
      // Dynamic multi-select (API-driven)
      if (property.api_endpoint) {
        return (
          <DynamicMultiSelectField
            {...commonProps}
            value={Array.isArray(value) ? value : []}
            apiEndpoint={property.api_endpoint}
          />
        );
      }

      // Static multi-select with enum options
      if (property.enum && property.multiple) {
        return (
          <MultiSelectField
            {...commonProps}
            value={Array.isArray(value) ? value : []}
            options={property.enum}
          />
        );
      }

      // Regular array field for other cases
      return <ArrayField {...commonProps} value={Array.isArray(value) ? value : []} />;
    }

    // Object fields (JSON editor)
    if (property.type === 'object') {
      console.log(`[FormRenderer] Rendering object field "${name}":`, {
        propertyType: property.type,
        valueType: typeof value,
        value: value,
        isString: typeof value === 'string',
      });

      // If the value is a string like "[object Object]", try to parse it
      let objectValue: Record<string, any> = {};
      if (typeof value === 'string') {
        try {
          objectValue = JSON.parse(value);
        } catch {
          console.warn(`[FormRenderer] Could not parse string value for ${name}:`, value);
          objectValue = {};
        }
      } else if (typeof value === 'object' && value !== null) {
        objectValue = value as Record<string, any>;
      }

      return (
        <JsonEditorField
          {...commonProps}
          value={objectValue}
        />
      );
    }

    return null;
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
