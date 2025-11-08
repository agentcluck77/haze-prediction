export interface PSICategory {
  label: string;
  color: string;
  bgColor: string;
}

export function getPSICategory(psi: number): PSICategory {
  if (psi < 50) {
    return {
      label: 'Good',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    };
  }
  if (psi < 100) {
    return {
      label: 'Moderate',
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
    };
  }
  if (psi < 200) {
    return {
      label: 'Unhealthy',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    };
  }
  if (psi < 300) {
    return {
      label: 'Very Unhealthy',
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    };
  }
  return {
    label: 'Hazardous',
    color: 'text-red-800',
    bgColor: 'bg-red-100',
  };
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('en-SG', {
    timeZone: 'Asia/Singapore',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

