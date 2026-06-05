# OpenRouter Video MCP Sunucusu

OpenRouter'ın video oluşturma API'sini kullanan **Streamable HTTP MCP sunucusu**.  
Render.com'a deploy edilmek üzere tasarlanmıştır.

## MCP Endpoint

```
https://<your-app>.onrender.com/mcp
```

## Araçlar (Tools)

| Araç | Açıklama |
|------|----------|
| `list_video_models` | Kullanılabilir video modellerini listeler |
| `generate_video` | Video oluşturma işi başlatır |
| `check_video_status` | İş durumunu kontrol eder |
| `wait_for_video` | Video hazır olana kadar bekler |
| `list_my_generations` | Geçmiş üretim listesi |

## Hızlı Başlangıç (Yerel Geliştirme)

```bash
# 1. Depoyu klonla
git clone <repo-url>
cd openrouter_video_mcp

# 2. Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Ortam değişkenlerini ayarla
copy .env.example .env
# .env dosyasını düzenle ve OPENROUTER_API_KEY'i gir

# 5. Sunucuyu başlat
python server.py
```

Sunucu `http://localhost:8000/mcp` adresinde hazır!

## Render.com'a Deploy

### 1. GitHub'a push et
```bash
git init
git add .
git commit -m "feat: OpenRouter Video MCP sunucusu"
git remote add origin <github-repo-url>
git push -u origin main
```

### 2. Render.com'da servis oluştur
- [render.com](https://render.com) → **New** → **Web Service**
- GitHub reposunu bağla
- **Environment Variables** bölümüne ekle:
  - `OPENROUTER_API_KEY` = `sk-or-v1-...`
  - `SITE_URL` = `https://<app-name>.onrender.com`

### 3. MCP istemcisine ekle (Claude Desktop vb.)

```json
{
  "mcpServers": {
    "openrouter-video": {
      "url": "https://<app-name>.onrender.com/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Desteklenen Modeller

- `google/veo-3.1-fast` *(hız öncelikli)*
- `google/veo-3.1-lite`
- `kwaivgi/kling-v3.0-pro`
- `kwaivgi/kling-v3.0-std`
- `kwaivgi/kling-video-o1`
- Ve daha fazlası → `list_video_models` ile güncel listeyi alın

## Örnek Kullanım (MCP üzerinden)

```
Araç: generate_video
  prompt: "A serene mountain lake at sunrise, cinematic slow motion"
  model: "google/veo-3.1-fast"
  aspect_ratio: "16:9"
  duration: 8
  generate_audio: true

→ Döner: { "job_id": "job_abc123", "status": "pending" }

Araç: wait_for_video
  job_id: "job_abc123"

→ Döner: { "video_urls": ["https://..."] }
```

## Endpoints

| Endpoint | Açıklama |
|----------|----------|
| `GET /health` | Sağlık kontrolü (Render için) |
| `GET /` | Sağlık kontrolü |
| `POST /mcp` | MCP Streamable HTTP |
| `GET /mcp` | MCP SSE stream |
