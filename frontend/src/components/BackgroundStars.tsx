import React from 'react';
import { useParallax } from '../hooks/useParallax';

interface BackgroundStarsProps {
  children: React.ReactNode;
  starCount?: number;
  shootingStarCount?: number;
}

const BackgroundStars: React.FC<BackgroundStarsProps> = ({ 
  children, 
  starCount = 30,
  shootingStarCount = 3
}) => {
  const scrollY = useParallax();

  return (
    <div className="page-container login-page">
      {/* Stars */}
      <div 
        className="stars"
        style={{ transform: `translateY(${scrollY * 0.2}px)` }}
      >
        {[...Array(starCount)].map((_, i) => (
          <div key={i} className="star" style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 60}%`,
            animationDelay: `${Math.random() * 3}s`,
            animationDuration: `${2 + Math.random() * 3}s`
          }}></div>
        ))}
      </div>

      {/* Shooting Stars */}
      <div className="shooting-stars">
        {[...Array(10)].map((_, i) => {
          const duration = 2 + Math.random() * 2;
          return (
            <div 
              key={`shooting-${i}`} 
              className="shooting-star" 
              style={{
                top: `${Math.random() * 60}%`,
                animationDelay: `${Math.random() * 30 + 10}s`,
                '--animation-duration': `${duration}s`
              } as React.CSSProperties}
            ></div>
          );
        })}
      </div>
      
      {children}
    </div>
  );
};

export default BackgroundStars; 