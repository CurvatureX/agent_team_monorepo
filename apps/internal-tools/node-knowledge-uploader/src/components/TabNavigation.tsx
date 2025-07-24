"use client";

import { useState } from "react";

interface TabNavigationProps {
  activeTab: "upload" | "search";
  onTabChange: (tab: "upload" | "search") => void;
  searchResultsCount?: number;
  databaseCount?: number | null;
}

export default function TabNavigation({
  activeTab,
  onTabChange,
  searchResultsCount,
  databaseCount,
}: TabNavigationProps) {
  const [isLoading, setIsLoading] = useState(false);

  // Handle tab switching with loading state
  const handleTabChange = (tab: "upload" | "search") => {
    if (tab !== activeTab) {
      setIsLoading(true);
      onTabChange(tab);
      // Reset loading state after a brief delay to allow for smooth transition
      setTimeout(() => setIsLoading(false), 100);
    }
  };

  return (
    <div className="border-b border-gray-200 mb-6">
      {/* Tab Navigation */}
      <nav className="flex space-x-8" aria-label="Tabs">
        <button
          onClick={() => handleTabChange("upload")}
          className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
            activeTab === "upload"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
          aria-current={activeTab === "upload" ? "page" : undefined}
        >
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            Upload Knowledge
          </div>
        </button>

        <button
          onClick={() => handleTabChange("search")}
          className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
            activeTab === "search"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
          aria-current={activeTab === "search" ? "page" : undefined}
        >
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            Search Knowledge
            {searchResultsCount !== undefined && searchResultsCount > 0 && (
              <span className="ml-1 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                {searchResultsCount}
              </span>
            )}
          </div>
        </button>
      </nav>

      {/* Database Status Display */}
      <div className="mt-4 mb-2">
        <div className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <svg
                className="w-5 h-5 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
                />
              </svg>
              <span className="text-sm font-medium text-gray-700">
                Database Status:
              </span>
            </div>

            <div className="flex items-center gap-2">
              {databaseCount !== null && databaseCount !== undefined ? (
                <>
                  <span className="text-sm text-gray-900 font-semibold">
                    {databaseCount.toLocaleString()} nodes
                  </span>
                  <div
                    className={`w-2 h-2 rounded-full ${
                      databaseCount > 0 ? "bg-green-500" : "bg-yellow-500"
                    }`}
                    title={
                      databaseCount > 0
                        ? "Database has content"
                        : "Database is empty"
                    }
                  />
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="animate-spin w-4 h-4 border-2 border-gray-300 border-t-blue-600 rounded-full" />
                  <span className="text-sm text-gray-500">Loading...</span>
                </div>
              )}
            </div>
          </div>

          {/* Conditional messaging based on database state */}
          {databaseCount !== null && databaseCount !== undefined && (
            <div className="text-xs text-gray-600">
              {databaseCount === 0 ? (
                <span className="flex items-center gap-1">
                  <svg
                    className="w-4 h-4 text-yellow-500"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Database is empty - upload knowledge to start searching
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <svg
                    className="w-4 h-4 text-green-500"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Ready for search and upload
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Loading overlay during tab transitions */}
      {isLoading && (
        <div className="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center z-10">
          <div className="flex items-center gap-2 text-gray-600">
            <div className="animate-spin w-5 h-5 border-2 border-gray-300 border-t-blue-600 rounded-full" />
            <span className="text-sm">Loading...</span>
          </div>
        </div>
      )}
    </div>
  );
}
