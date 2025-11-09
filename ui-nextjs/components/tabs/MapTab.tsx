'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import type { PredictionResponse, AllPredictionsResponse, Horizon } from '@/types/api';
import dynamic from 'next/dynamic';

const HazeMap = dynamic(() => import('@/components/HazeMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[600px] bg-gray-200 animate-pulse rounded-lg" />
  ),
});

interface MapTabProps {
  showLoading: (text?: string) => void;
  hideLoading: () => void;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

export default function MapTab({ showLoading, hideLoading, showToast }: MapTabProps) {
  return (
    <div>
      <h2 className="text-black font-bold mb-4 ">Haze Detection Map</h2>
      <HazeMap />
    </div>
  );
}


