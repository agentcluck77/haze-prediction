'use client';

interface LoadingOverlayProps {
  loading: boolean;
  text?: string;
}

export default function LoadingOverlay({ loading, text = 'Loading...' }: LoadingOverlayProps) {
  if (!loading) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        <p className="text-gray-700 font-medium">{text}</p>
      </div>
    </div>
  );
}

