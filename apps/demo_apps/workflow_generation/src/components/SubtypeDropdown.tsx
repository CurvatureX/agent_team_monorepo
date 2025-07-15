import React from "react";

interface Subtype {
  id: string;
  label: string;
  description: string;
}

interface SubtypeDropdownProps {
  nodeType: string;
  subtypes: Subtype[];
  position: { x: number; y: number };
  onSelect: (subtype: string) => void;
  onCancel: () => void;
}

const SubtypeDropdown: React.FC<SubtypeDropdownProps> = ({
  nodeType,
  subtypes,
  position,
  onSelect,
  onCancel,
}) => {
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black bg-opacity-10"
        onClick={onCancel}
      />

      {/* Dropdown */}
      <div
        className="fixed z-50 bg-white rounded-lg shadow-xl border border-gray-200 min-w-[280px] max-w-[320px] max-h-[400px] overflow-y-auto"
        style={{
          left: Math.min(position.x, window.innerWidth - 340),
          top: Math.min(position.y, window.innerHeight - 420),
        }}
      >
        <div className="p-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-800 mb-1">
            Choose {nodeType.replace('_', ' ')} Type
          </h3>
          <p className="text-xs text-gray-500">
            Select a specific subtype for this node
          </p>
        </div>

        <div className="p-2">
          {subtypes.map((subtype) => (
            <button
              key={subtype.id}
              onClick={() => onSelect(subtype.id)}
              className="w-full text-left p-3 rounded-md hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-200 mb-1"
            >
              <div className="font-medium text-sm text-gray-800 mb-1">
                {subtype.label}
              </div>
              <div className="text-xs text-gray-500">
                {subtype.description}
              </div>
            </button>
          ))}
        </div>

        <div className="p-3 border-t border-gray-100">
          <button
            onClick={onCancel}
            className="w-full text-sm text-gray-600 hover:text-gray-800 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </>
  );
};

export default SubtypeDropdown;
