import zipfile
from pathlib import Path

target = Path("c:/SNEHARSHA/INFRALYTIX/sample-repo.zip")
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(
        "app.py",
        "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'status': 'active'}\n",
    )
    z.writestr(
        "package.json",
        '{"name": "cloud-ui", "dependencies": {"react": "^19.0.0", "tailwindcss": "^3.4.0"}}',
    )
    z.writestr(
        "Dockerfile",
        "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"app.py\"]\n",
    )
print(f"Created {target} successfully")
