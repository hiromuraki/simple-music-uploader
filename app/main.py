import os
import json
import time
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# 1. 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FOLDER = os.path.join(BASE_DIR, 'music')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
TEMPLATES_FOLDER = os.path.join(BASE_DIR, 'templates')

if not os.path.exists(MUSIC_FOLDER):
    os.makedirs(MUSIC_FOLDER)

# 2. 挂载静态文件和模板
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")
templates = Jinja2Templates(directory=TEMPLATES_FOLDER)

# 3. 中间件：强制添加 COOP/COEP 响应头 (FFmpeg.wasm 必需)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response

# --- 路由 ---


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 资源访问: /resources/music/{filename}


@app.get("/resources/music/{filename}")
async def serve_music(filename: str):
    file_path = os.path.join(MUSIC_FOLDER, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# API: 获取列表


@app.get("/api/list")
async def get_music_list():
    music_list = []
    # 遍历 JSON 文件
    for filename in os.listdir(MUSIC_FOLDER):
        if filename.endswith('.json'):
            try:
                filepath = os.path.join(MUSIC_FOLDER, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    music_list.append(data)
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue

    # 按时间倒序
    music_list.sort(key=lambda x: x.get('upload_time', 0), reverse=True)
    return music_list

# API: 上传 (核心)


@app.post("/upload")
async def upload_file(
    audio: UploadFile = File(...),
    metadata: str = Form(...)
):
    try:
        # FastAPI 会自动处理大文件流式上传，无需手动配置 MAX_CONTENT_LENGTH
        # 但我们仍然可以检查一下

        # 1. 解析元数据
        meta_obj = json.loads(metadata)

        # 2. 确定文件名 (前端算好的 md5:16.mp3)
        if audio.filename is None:
            raise HTTPException(status_code=500, detail="Invalid md5:16")
        mp3_filename = os.path.basename(audio.filename)
        file_id = os.path.splitext(mp3_filename)[0]  # 应该是 16位 hash

        # 3. 保存音频
        mp3_path = os.path.join(MUSIC_FOLDER, mp3_filename)

        # 使用 shutil 高效写入
        with open(mp3_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        # 4. 补充并保存元数据
        meta_obj['upload_time'] = int(time.time())
        meta_obj['id'] = file_id
        meta_obj['filename'] = mp3_filename

        json_filename = f"{file_id}.json"
        json_path = os.path.join(MUSIC_FOLDER, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(meta_obj, f, ensure_ascii=False)

        return {"message": "Upload success", "id": file_id}

    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    print("启动 FastAPI (Uvicorn)... 访问 http://127.0.0.1:8000")
    # 绑定到 0.0.0.0 以便 WSL 外部访问
    uvicorn.run(app, host="0.0.0.0", port=8000)
