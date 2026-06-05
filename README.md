# OpenRouter Video MCP Server

A Model Context Protocol (MCP) server using **Streamable HTTP transport** to generate high-quality videos using OpenRouter's Video APIs.

Designed for easy deployment on **Render.com** (or similar container/web app hosting platforms).

## MCP Endpoint

```
https://<your-app>.onrender.com/mcp
```

## Tools

| Tool | Description |
|------|-------------|
| `list_video_models` | Lists all available video models on OpenRouter |
| `generate_video` | Starts an asynchronous video generation job |
| `check_video_status` | Checks the status of a specific job ID |
| `wait_for_video` | Polls/blocks until the video is completed |
| `list_my_generations` | Lists recent video generation jobs history |

## Quick Start (Local Development)

```bash
# 1. Clone the repository
git clone <repo-url>
cd openrouter_video_mcp

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
copy .env.example .env
# Edit .env and supply your OPENROUTER_API_KEY

# 5. Start the server
python server.py
```

The server will run on `http://localhost:8000/mcp`.

## Deploying to Render.com

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "feat: OpenRouter Video MCP server"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Set Up Web Service on Render.com
- Visit [render.com](https://render.com) → **New** → **Web Service**
- Connect your GitHub repository.
- Render will automatically detect the configuration using `render.yaml`.
- In the Render Dashboard, add the following **Environment Variables**:
  - `OPENROUTER_API_KEY`: Your OpenRouter API key (format `sk-or-...`)
  - `SITE_URL`: The URL of your Render app (e.g., `https://<app-name>.onrender.com`)

### 3. Add to your MCP client (e.g. Claude Desktop)

Add this configuration block to your client config (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "openrouter-video": {
      "url": "https://<your-app-name>.onrender.com/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Supported Models

- `google/veo-3.1-fast` *(Default - fast and balanced)*
- `google/veo-3.1-lite`
- `kwaivgi/kling-v3.0-pro`
- `kwaivgi/kling-v3.0-std`
- `kwaivgi/kling-video-o1`
- And more! Check dynamically using the `list_video_models` tool.

## Example Workflow (via MCP Client)

```
User: Let's create a video.
Client Tool Call: generate_video(
  prompt="A serene mountain lake at sunrise, cinematic slow motion",
  model="google/veo-3.1-fast",
  aspect_ratio="16:9",
  duration=8,
  generate_audio=true
)
Server Returns: { "job_id": "job_abc123", "status": "pending" }

Client Tool Call: wait_for_video(job_id="job_abc123")
Server Blocks (polling)...
Server Returns: { "status": "completed", "video_urls": ["https://cdn.openrouter.ai/...mp4"] }
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check (for Render.com uptime monitoring) |
| `GET /` | Root health check |
| `POST /mcp` | MCP Streamable HTTP endpoint |
| `GET /mcp` | MCP SSE stream endpoint |
