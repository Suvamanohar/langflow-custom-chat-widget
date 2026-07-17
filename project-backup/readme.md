# Langflow Custom Chat Widget

## Project architecture

Widget HTML
→ POST /api/v1/chat/widget
→ Langflow Flow
→ Groq Model
→ AI Response

## Backend startup

```powershell
cd C:\Users\suva\Documents\langflow
uv run langflow run --backend-only