# お絵描きサポートWebアプリ

## 始め方

### バックエンド
#### バックエンドサーバの準備
バックエンドの準備では、`./drow_ai_backend`をカレントディレクトリとして、それ以降のコマンドを実行してください。

#### LoRAファイルの取得
バックエンドサーバ側で利用するLoRAモデルを予め取得してください。
https://civitai.com/models/255143/dreamyvibes-artsyle-sdxl-lora
https://huggingface.co/furusu/SD-LoRA/blob/main/lcm-animagine-3.safetensors

上記2つのLoRAを取得して、`DreamyvibesartstyleSDXL.safetensors`と`lcm-animaginexl-3_1.safetensors`にリネームして`drow_ai_backend/inputs`フォルダに格納してください。

#### バックエンドサーバの起動
下記コマンドを実行してサーバを起動してください
```
python app.py
```

### フロントエンド
リポジトリ直下（`./`）をカレントディレクトリとして、以降のコマンドを実行してください
#### バックエンドURLの設定
`.env.local`をリポジトリ直下（`./`）に作成して、下記の通り設定してください。
URLはバックエンドサーバのURLです。(以下は例です)

```
NEXT_PUBLIC_API_BASE_URL=https://192.168.0.xxx:3000
```

（バックエンドサーバのプライベートIPアドレスを予め確認しておいてください。ポートは3000です）

#### フロントエンドサーバを起動

下記のコマンドを一行ずつ実行してください

```bash
pnpm i
pnpm build
pnpm dev
```

### 端末で接続
（バックエンドの準備も完了後）
ターミナルに表示されているURLに対して、フロントエンドサーバと同じネットワークにつながっている端末から接続してください。
