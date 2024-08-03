import React, { useRef, useState, useEffect, RefObject } from 'react';

interface InpaintModeProps {
  processedImage: string | null;
  setProcessedImage: (image: string | null) => void;
  canvasRef: RefObject<HTMLCanvasElement>;
  setMaskImage: (image: string | null) => void;
}

const InpaintMode: React.FC<InpaintModeProps> = ({ processedImage, setProcessedImage, canvasRef, setMaskImage }) => {
  const [isDrawing, setIsDrawing] = useState(false);
  const [points, setPoints] = useState<{ x: number; y: number }[]>([]);
  const [currentMaskImage, setCurrentMaskImage] = useState<string | null>(null);
  const [inpaintedImage, setInpaintedImage] = useState<string | null>(null);
  const [isProcessed, setIsProcessed] = useState(false);
  const [isButtonPressed1, setIsButtonPressed1] = useState(false);
  const [isButtonPressed2, setIsButtonPressed2] = useState(false);
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  const startDrawing = (event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    const { offsetX, offsetY } = getCanvasPosition(event);
    setPoints([{ x: offsetX, y: offsetY }]);
  };

  const drawMask = (event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !canvasRef.current || !processedImage) return;

    const { offsetX, offsetY } = getCanvasPosition(event);
    const point = { x: offsetX, y: offsetY };
    setPoints(prevPoints => [...prevPoints, point]);

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const image = new Image();
    image.src = processedImage;
    image.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height); // キャンバスをクリア
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height); // 赤色画像を再描画

      // フリーハンドで選択したポイントを描画（灰色の点線）
      ctx.strokeStyle = 'gray';
      ctx.setLineDash([5, 3]); // 点線の設定
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      points.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.lineTo(point.x, point.y);
      ctx.stroke();
      //ctx.setLineDash([]); // 点線をリセット
    };
  };

  const finishDrawing = () => {
    setIsDrawing(false);
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // マスクの範囲をポリゴンで描画するための準備
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = canvas.width;
    maskCanvas.height = canvas.height;
    const maskCtx = maskCanvas.getContext('2d');
    if (!maskCtx) return;

    // 背景を黒に設定
    maskCtx.fillStyle = 'black';
    maskCtx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);

    // マスクの範囲を白で描画
    maskCtx.fillStyle = 'white';
    maskCtx.beginPath();
    maskCtx.moveTo(points[0].x, points[0].y);
    points.forEach(p => maskCtx.lineTo(p.x, p.y));
    maskCtx.closePath();
    maskCtx.fill();

    // マスク画像をデータURLとして保存
    const maskDataURL = maskCanvas.toDataURL();
    setMaskImage(maskDataURL); // 親コンポーネントにマスク画像を設定
    setCurrentMaskImage(maskDataURL); // ローカル状態にも保存

    // キャンバスを再描画して範囲選択の線を消去
    //ctx.clearRect(0, 0, canvas.width, canvas.height); // キャンバスをクリア
    const image = new Image();
    image.src = processedImage || '';
    //image.onload = () => ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  };

  const getCanvasPosition = (event: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    let offsetX, offsetY;

    if (event.type.startsWith('mouse')) {
      const mouseEvent = event as React.MouseEvent<HTMLCanvasElement>;
      offsetX = mouseEvent.nativeEvent.offsetX;
      offsetY = mouseEvent.nativeEvent.offsetY;
    } else {
      const touchEvent = event as React.TouchEvent<HTMLCanvasElement>;
      const rect = canvasRef.current?.getBoundingClientRect();
      offsetX = touchEvent.touches[0].clientX - rect!.left;
      offsetY = touchEvent.touches[0].clientY - rect!.top;
    }

    return { offsetX, offsetY };
  };

  const executeInpainting = async () => {
    if (!processedImage || !currentMaskImage) return;

    const endpoint = '/api/inpaint';
    const url = `${baseUrl}${endpoint}`;

    console.log("execute inpainting");

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          original_image: processedImage,
          mask_image: currentMaskImage,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      //console.log(data);
      setInpaintedImage(data.inpainted_image); // 処理後の画像を設定
      setIsProcessed(true); // 処理完了状態に設定
    } catch (error) {
      console.error("Error executing inpainting:", error);
    }
  };

  const acceptResult = () => {
    if (inpaintedImage) {
      setIsProcessed(false);
      setCurrentMaskImage(null);
      setMaskImage(null);
      setPoints([]);
      // 処理済みの画像を元画像として設定
      setProcessedImage(inpaintedImage);
      setInpaintedImage(null);
    }
  };

  const rejectResult = () => {
    setIsProcessed(false);
    setInpaintedImage(null);
  };

  useEffect(() => {
    if (processedImage && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        const image = new Image();
        image.src = processedImage;
        image.onload = () => ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      }
    }
  }, [processedImage]);

  return (
    <>
      <div className="flex flex-col items-center">
        <div>Original Images</div>
        <div className="border border-black">
          <canvas
            ref={canvasRef}
            width="500"
            height="500"
            className="border border-black"
            onMouseDown={startDrawing}
            onMouseUp={finishDrawing}
            onMouseMove={drawMask}
            onTouchStart={startDrawing}
            onTouchEnd={finishDrawing}
            onTouchMove={drawMask}
          />
        </div>
        <div>
        {currentMaskImage && !isProcessed && (
        <button
          onMouseDown={() => setIsButtonPressed1(true)}
          onMouseUp={() => setIsButtonPressed1(false)}
          onMouseLeave={() => setIsButtonPressed1(false)}
          onTouchStart={() => setIsButtonPressed1(true)}
          onTouchEnd={() => setIsButtonPressed1(false)}
          onClick={executeInpainting}
          className={`m-2 p-2 border ${isButtonPressed1 ? 'bg-blue-500' : 'bg-red-500'} text-white`}
        >
          実行
        </button>
      )}
        </div>
      
      {isProcessed && (
        <div>
          <button
            onMouseDown={() => setIsButtonPressed1(true)}
            onMouseUp={() => setIsButtonPressed1(false)}
            onMouseLeave={() => setIsButtonPressed1(false)}
            onTouchStart={() => setIsButtonPressed1(true)}
            onTouchEnd={() => setIsButtonPressed1(false)}
            onClick={acceptResult}
            className={`m-2 p-2 border ${isButtonPressed1 ? 'bg-blue-500' : 'bg-green-500'} text-white`}
          >
            OK
          </button>
          <button
            onMouseDown={() => setIsButtonPressed2(true)}
            onMouseUp={() => setIsButtonPressed2(false)}
            onMouseLeave={() => setIsButtonPressed2(false)}
            onTouchStart={() => setIsButtonPressed2(true)}
            onTouchEnd={() => setIsButtonPressed2(false)}
            onClick={rejectResult}
            className={`m-2 p-2 border ${isButtonPressed2 ? 'bg-blue-500' : 'bg-red-500'} text-white`}
          >
            NG
          </button>
        </div>
      )}
      </div>
      <div className="flex flex-col items-center">
        <div>Result Images</div>
        <div className="border border-blue-500 w-[500px] h-[500px] flex justify-center items-center" style={{ backgroundColor: 'black' }}>
          {inpaintedImage ? (
            <img src={inpaintedImage} alt="Inpainted Result" width="500" height="500" />
          ) : currentMaskImage ? (
            <img src={currentMaskImage} alt="Mask" width="500" height="500" />
          ) : (
            <div className="text-gray-500">Processing result will be displayed here</div>
          )}
        </div>
        
      </div>

      
    </>
  );
};

export default InpaintMode;
