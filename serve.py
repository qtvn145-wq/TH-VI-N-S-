from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.main import app
FRONTEND = Path(__file__).resolve().parent / 'frontend'
app.mount('/ui', StaticFiles(directory=FRONTEND), name='frontend')
@app.get('/', include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND / 'index.html')
