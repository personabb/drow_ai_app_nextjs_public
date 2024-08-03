from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageOps
import io
import base64
import nest_asyncio
from pyngrok import ngrok
from module.module_sdc import SDXLC as SDXL
import asyncio
import torch
import numpy as np

app = FastAPI()
sdxl = SDXL()
print("Stable Diffusion XL model loaded successfully")

# CORSの設定
origins = [
    "*" # フロントエンドのURLを指定
    # 必要に応じて他のオリジンを追加
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # すべてのHTTPメソッドを許可
    allow_headers=["*"],  # すべてのヘッダーを許可
)

class ImageData(BaseModel):
    image: str

class InpaintData(BaseModel):
    original_image: str
    mask_image: str

# プロンプトの情報を保持するクラス変数
class PromptData:
    prompt = ""
    negative_prompt = ""

class ApplyPromptsData(BaseModel):
    prompt: str
    negative_prompt: str

class ApplyModeData(BaseModel):
  mode: str

@app.post("/api/process-image")
async def process_image(data: ImageData):
    try:
        # Base64エンコードされた画像データをデコード
        image_data = base64.b64decode(data.image.split(",")[1])
        image = Image.open(io.BytesIO(image_data))

        # 画像の線を赤に変更する処理
        red_image = process_scribble(image)
        print("red_image")

        # 画像をBase64にエンコードして返却
        buffered = io.BytesIO()
        red_image.save(buffered, format="PNG")
        processed_image_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {"processed_image": f"data:image/png;base64,{processed_image_str}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def process_scribble(image: Image.Image) -> Image.Image:

    # ピクセルデータを取得
    datas = image.getdata()

    # 新しいピクセルデータを格納するリスト
    new_data = []

    # ピクセルをループして透明度をチェック
    for item in datas:
        # 完全に透明なピクセル（アルファが0）の場合
        if item[3] == 0:
            # kuro色で置き換え
            new_data.append((0, 0, 0, 255))
        else:
            # そのまま
            new_data.append(item)

    # 新しいピクセルデータで画像を更新
    image.putdata(new_data)

    # 画像をPNG形式で保存
    image.save('inputs/refer.png', 'PNG')
    image = sdxl.generate_image(PromptData.prompt, PromptData.negative_prompt,'inputs/refer.png',controlnet_conditioning_scale = 0.3, mode = "scribble")
    print("image")
    image = image.convert("RGBA")
    return image

@app.post("/api/inpaint")
async def inpaint(data: InpaintData):
    try:
        # Base64エンコードされた元画像とマスク画像をデコード
        original_image_data = base64.b64decode(data.original_image.split(",")[1])
        mask_image_data = base64.b64decode(data.mask_image.split(",")[1])

        original_image = Image.open(io.BytesIO(original_image_data)).convert("RGBA")
        mask_image = Image.open(io.BytesIO(mask_image_data)).convert("L")

        original_image.save('inputs/original_image.png', 'PNG')
        mask_image.save('inputs/mask_image.png', 'PNG')

        # マスクに従って元画像の範囲を消去
        result_image_tensor, mask_tensor = apply_mask(original_image, mask_image)
        #result_image.save('inputs/refer.png', 'PNG')
        image = sdxl.generate_image(PromptData.prompt, PromptData.negative_prompt,result_image_tensor,controlnet_conditioning_scale = 0.9, mode = "inpaint", mask_image = mask_tensor)
        image = image.convert("RGBA")

        # 画像をBase64にエンコードして返却
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        result_image_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {"inpainted_image": f"data:image/png;base64,{result_image_str}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def apply_mask(original_image: Image.Image, mask_image: Image.Image) -> Image.Image:
    # PIL画像をNumPy配列に変換
    original_image = original_image.convert("RGB")
    mask_image = mask_image.convert("L")
    mask_image = mask_image.resize((original_image.size[0],original_image.size[1]), Image.NEAREST)
    original_np = np.array(original_image)
    mask_np = np.array(mask_image)

    #print(original_np.shape)
    
    # NumPy配列をTorchテンソルに変換
    original_tensor = torch.tensor(original_np)
    mask_tensor = torch.tensor(mask_np)
    mask_tensor = mask_tensor.unsqueeze(2)

    masked_tensor = original_tensor.clone()  # 元のテンソルをコピー

    return masked_tensor, mask_tensor


@app.post("/api/apply-prompts")
async def apply_prompts(data: ApplyPromptsData):
    # プロンプトとネガティブプロンプトのデータを保存
    PromptData.prompt = data.prompt
    PromptData.negative_prompt = data.negative_prompt
    print(f"Prompt: {PromptData.prompt}", f"Negative Prompt: {PromptData.negative_prompt}")

    return {"message": "Prompts applied successfully"}


@app.post("/api/change_mode")
async def change_mode(data: ApplyModeData):
  mode = data.mode
  #ハイスペックなpc、サーバを利用する場合は、モデルをリセットする必要はないためコメントアウト。
  #互換性を維持するために、このapiは呼ばれるが、なにもしない。
  """if mode == "inpaint":
    print("loading inpaint mode")
    sdxl.memory_reset_model(controlnet_path = "destitech/controlnet-inpaint-dreamer-sdxl")
    print("loaded inpaint mode")
  elif mode == "sketch":
    print("loading sketch mode")
    sdxl.memory_reset_model(controlnet_path = "xinsir/controlnet-scribble-sdxl-1.0")
    print("loaded sketch mode")"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
