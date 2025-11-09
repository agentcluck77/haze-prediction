'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';
import { api } from '@/lib/api';

interface ApiContextType {
  baseURL: string;
  setBaseURL: (url: string) => void;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

export function ApiProvider({ children }: { children: ReactNode }) {
  const [baseURL, setBaseURLState] = useState('http://localhost:8000');

  const setBaseURL = (url: string) => {
    api.setBaseURL(url);
    setBaseURLState(url);
  };

  return (
    <ApiContext.Provider value={{ baseURL, setBaseURL }}>
      {children}
    </ApiContext.Provider>
  );
}

export function useApi() {
  const context = useContext(ApiContext);
  if (context === undefined) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
}

