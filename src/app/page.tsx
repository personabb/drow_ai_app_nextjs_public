'use client';
import React, { useState, useRef, useEffect } from 'react';
import SketchMode from '../components/SketchMode';
import InpaintMode from '../components/InpaintMode';

enum Mode {
  Sketch, // ラクガキモード
  Inpaint // インペイントモード
}

const HomePage = () => {
  const [mode, setMode] = useState<Mode>(Mode.Sketch);
    // スクロールを無効にする関数
    const disableScroll = () => {
      document.body.classList.add('no-scroll');
    };
  
    // スクロールを有効にする関数
    const enableScroll = () => {
      document.body.classList.remove('no-scroll');
    };
  useEffect(() => {
    if (mode === Mode.Sketch || mode === Mode.Inpaint) {
      disableScroll();
    } else {
      enableScroll();
    }
    
    return () => enableScroll(); // コンポーネントがアンマウントされるときにスクロールを有効化
  }, [mode]);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [maskImage, setMaskImage] = useState<string | null>(null); // マスク画像の状態
  const sketchCanvasRef = useRef<HTMLCanvasElement>(null);
  const inpaintCanvasRef = useRef<HTMLCanvasElement>(null);
  const [prompt, setPrompt] = useState('');
  const [users, setUsers] = useState('user01');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [isButtonPressed, setIsButtonPressed] = useState(false);

  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  

  const switchToInpaint = async() => {
    const endpoint = '/api/change_mode';
    const url = `${baseUrl}${endpoint}`;
    setMode(Mode.Inpaint);
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'inpaint'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 成功時の処理（例えば、成功メッセージを表示するなど）
    } catch (error) {
      console.error("Error applying prompts:", error);
    }

  };
  const switchToSketch = async() => {
    const endpoint = '/api/change_mode';
    const url = `${baseUrl}${endpoint}`;
    setMode(Mode.Sketch);
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'sketch'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 成功時の処理（例えば、成功メッセージを表示するなど）
    } catch (error) {
      console.error("Error applying prompts:", error);
    }
  };

  const saveImages = () => {
    const saveCanvas = (canvas: HTMLCanvasElement | null, filename: string) => {
      if (!canvas) return;
      const link = document.createElement('a');
      link.href = canvas.toDataURL('image/png');
      link.download = filename;
      link.click();
    };

    if (mode === Mode.Sketch) {
      saveCanvas(sketchCanvasRef.current, 'sketch.png');
      if (processedImage) {
        const link = document.createElement('a');
        link.href = processedImage;
        link.download = 'processed.png';
        link.click();
      }
    } else if (mode === Mode.Inpaint) {
      saveCanvas(inpaintCanvasRef.current, 'inpaint.png');
      if (maskImage) {
        const link = document.createElement('a');
        link.href = maskImage;
        link.download = 'mask.png';
        link.click();
      }
    }
  };

  const clearCanvases = () => {
    const clearCanvas = (canvas: HTMLCanvasElement | null) => {
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'black';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    };

    clearCanvas(sketchCanvasRef.current);
    clearCanvas(inpaintCanvasRef.current);
    setProcessedImage(null);
    setMaskImage(null); // マスク画像もリセット
  };

  // プロンプト適用ボタン処理
  const applyPrompts = async () => {
    const endpoint = '/api/apply-prompts';
    const url = `${baseUrl}${endpoint}`;
    console.log("execute applyPrompts");
    if (!prompt && !negativePrompt) return;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          users: users,
          prompt: prompt,
          negative_prompt: negativePrompt
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 成功時の処理（例えば、成功メッセージを表示するなど）
    } catch (error) {
      console.error("Error applying prompts:", error);
    }
  };


  return (
    <div className="flex flex-col h-screen">
      <div className="flex justify-center items-center mb-4">
      User:
      <input
          type="text"
          defaultValue="user01"
          value={users}
          onChange={(e) => setUsers(e.target.value)}
          placeholder="necessary"
          className="border rounded p-2 h-12"
        />
        <button
          onClick={switchToSketch}
          className={`m-2 p-2 border ${mode === Mode.Sketch ? 'bg-blue-500 text-white' : 'bg-white text-black'}`}
        >
          Sketch Mode
        </button>
        <button
          onClick={switchToInpaint}
          className={`m-2 p-2 border ${mode === Mode.Inpaint ? 'bg-blue-500 text-white' : 'bg-white text-black'}`}
        >
          Inpaint Mode
        </button>
        <button
          onClick={saveImages}
          className="m-2 p-2 border bg-green-500 text-white"
        >
          Save
        </button>
        <button
          onClick={clearCanvases}
          className="m-2 p-2 border bg-red-500 text-white"
        >
          Clear
        </button>
      </div>
      <div className="mt-4 flex justify-center items-center">
      Prompt:
      <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Prompt"
          className="w-3/5 border rounded p-2 h-12"
        />
      </div>
      <div className="mt-4 flex justify-center items-center">
        Negative Prompt:
        <textarea
          value={negativePrompt}
          onChange={(e) => setNegativePrompt(e.target.value)}
          placeholder="Negative Prompt"
          className="w-3/5 border rounded p-2 h-12"
        />
        <button
          onMouseDown={() => setIsButtonPressed(true)}
          onMouseUp={() => setIsButtonPressed(false)}
          onMouseLeave={() => setIsButtonPressed(false)}
          onTouchStart={() => setIsButtonPressed(true)}
          onTouchEnd={() => setIsButtonPressed(false)}
          onClick={applyPrompts}
          className={`m-2 p-2 border ${isButtonPressed ? 'bg-green-500' : 'bg-blue-500'} text-white`}
        >
          適用
        </button>
      </div>
      <div className="flex justify-center items-center space-x-4">
        {mode === Mode.Sketch && (
          <>
            <SketchMode users={users} setProcessedImage={setProcessedImage} canvasRef={sketchCanvasRef} />
            <div className="flex flex-col items-center">
              <div>Result Images</div>
              <div className="border border-blue-500 w-[500px] h-[500px] flex justify-center items-center">
                {processedImage ? (
                  <img src={processedImage} alt="Processed" width="500" height="500" />
                ) : (
                  <div className="text-gray-500">Processing result will be displayed here</div>
                )}
              </div>
            </div>
          </>
        )}
        {mode === Mode.Inpaint && (
          <InpaintMode users={users} processedImage={processedImage} setProcessedImage={setProcessedImage} canvasRef={inpaintCanvasRef} setMaskImage={setMaskImage} />
        )}
      </div>
    </div>
  );
};

export default HomePage;
