'use client';

import { Button } from "./button";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, useState } from "react";

interface CardCarouselProps {
  children: React.ReactNode[];
  itemsPerView?: number;
}

export function CardCarousel({ children, itemsPerView = 5 }: CardCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const nextSlide = () => {
    if (currentIndex < children.length - itemsPerView) {
      setCurrentIndex(prev => prev + 1);
      scrollContainerRef.current?.scrollBy({ left: 280, behavior: 'smooth' });
    }
  };

  const prevSlide = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
      scrollContainerRef.current?.scrollBy({ left: -280, behavior: 'smooth' });
    }
  };

  return (
    <div className="relative group">
      <div
        ref={scrollContainerRef}
        className="flex overflow-hidden gap-4 scroll-smooth"
      >
        {children}
      </div>
      
      {currentIndex > 0 && (
        <Button
          variant="outline"
          size="icon"
          className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={prevSlide}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      )}
      
      {currentIndex < children.length - itemsPerView && (
        <Button
          variant="outline"
          size="icon"
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={nextSlide}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
