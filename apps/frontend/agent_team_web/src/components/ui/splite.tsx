'use client'

import { Suspense, lazy, useState } from 'react'
import { Component as LumaSpin } from './luma-spin'
const Spline = lazy(() => import('@splinetool/react-spline'))

interface SplineSceneProps {
  scene: string
  className?: string
}

const LoadingSpinner = () => (
  <div className="w-full h-full flex items-center justify-center">
    <div className="mt-36">
      <LumaSpin />
    </div>
  </div>
)

export function SplineScene({ scene, className }: SplineSceneProps) {
  const [isSceneLoading, setIsSceneLoading] = useState(true);

  const handleLoad = () => {
    setIsSceneLoading(false);
  };

  return (
    <div className="relative w-full h-full">
      <Suspense fallback={<LoadingSpinner />}>
        <div className="relative w-full h-full">
          {isSceneLoading && (
            <div className="absolute inset-0 z-10">
              <LoadingSpinner />
            </div>
          )}
          <Spline
            scene={scene}
            className={className}
            onLoad={handleLoad}
          />
        </div>
      </Suspense>
    </div>
  )
}