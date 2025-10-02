"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

interface PageTitleContextType {
  customTitle: ReactNode | null;
  setCustomTitle: (title: ReactNode | null) => void;
}

const PageTitleContext = createContext<PageTitleContextType>({
  customTitle: null,
  setCustomTitle: () => {},
});

export const usePageTitle = () => useContext(PageTitleContext);

export function PageTitleProvider({ children }: { children: React.ReactNode }) {
  const [customTitle, setCustomTitle] = useState<ReactNode | null>(null);

  return (
    <PageTitleContext.Provider value={{ customTitle, setCustomTitle }}>
      {children}
    </PageTitleContext.Provider>
  );
}