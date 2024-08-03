'use client';
import React, { useRef, useState, useEffect, RefObject } from 'react';

interface SketchModeProps {
  setProcessedImage: (image: string | null) => void;
  canvasRef: RefObject<HTMLCanvasElement>;
}

const SketchMode: React.FC<SketchModeProps> = ({ setProcessedImage, canvasRef }) => {
  const [isDrawing, setIsDrawing] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [isButtonPressed, setIsButtonPressed] = useState(false);

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  useEffect(() => {
    if (canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'black';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    }
  }, [canvasRef]);

  const startDrawing = (x: number, y: number) => {
    setIsDrawing(true);
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx) {
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, y);
    }
  };

  const draw = (x: number, y: number) => {
    if (!isDrawing || !canvasRef.current) return;
    const ctx = canvasRef.current.getContext('2d');
    if (ctx) {
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x, y);
    }
  };

  const finishDrawing = async () => {
    setIsDrawing(false);
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const dataURL = canvas.toDataURL();

    if (abortController) {
      abortController.abort();
    }

    const newAbortController = new AbortController();
    setAbortController(newAbortController);
    const endpoint = '/api/process-image';
    const url = `${baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ image: dataURL }),
        signal: newAbortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setProcessedImage(data.processed_image);
    } catch (unknownError) {
      if (unknownError instanceof Error && unknownError.name !== 'AbortError') {
        console.error("Error processing image:", unknownError);
        setProcessedImage(null);
      }
    }
  };

  const handleMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
    startDrawing(event.nativeEvent.offsetX, event.nativeEvent.offsetY);
  };

  const handleMouseMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    draw(event.nativeEvent.offsetX, event.nativeEvent.offsetY);
  };

  const handleTouchStart = (event: React.TouchEvent<HTMLCanvasElement>) => {
    const touch = event.touches[0];
    const rect = canvasRef.current!.getBoundingClientRect();
    startDrawing(touch.clientX - rect.left, touch.clientY - rect.top);
  };

  const handleTouchMove = (event: React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const touch = event.touches[0];
    const rect = canvasRef.current!.getBoundingClientRect();
    draw(touch.clientX - rect.left, touch.clientY - rect.top);
    event.preventDefault(); // タッチ移動時にスクロールを防ぐ
  };

  //const handleMouseUp = () => finishDrawing();
  //const handleTouchEnd = () => finishDrawing();

  return (
    <div>
      <div className="flex flex-col items-center">
        <div>Sketch Images</div>
        <div className="border border-black">
          <canvas
            ref={canvasRef}
            width="500"
            height="500"
            className="border border-black"
            onMouseDown={handleMouseDown}
            //onMouseUp={handleMouseUp}
            onMouseMove={handleMouseMove}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            //onTouchEnd={handleTouchEnd}
          />
        </div>
        <button
        onMouseDown={() => setIsButtonPressed(true)}
        onMouseUp={() => setIsButtonPressed(false)}
        onMouseLeave={() => setIsButtonPressed(false)}
        onTouchStart={() => setIsButtonPressed(true)}
        onTouchEnd={() => setIsButtonPressed(false)}
        onClick={finishDrawing}
        className={`m-2 p-2 border ${isButtonPressed ? 'bg-blue-500' : 'bg-red-500'} text-white`}
      >
        実行
      </button>
      </div>
      
    </div>
  );
};

export default SketchMode;
