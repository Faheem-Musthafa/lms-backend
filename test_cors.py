import asyncio
from app.main import app

async def test():
    scope = {
        "type": "http",
        "method": "OPTIONS",
        "path": "/api/v1/login", # or whatever the path is
        "headers": [
            (b"host", b"testserver"),
            (b"origin", b"https://lms-mf-es-shell.vercel.app"),
            (b"access-control-request-method", b"POST"),
            (b"access-control-request-headers", b"content-type"),
        ]
    }
    
    async def receive():
        return {"type": "http.request"}

    async def send(message):
        print(message)

    await app(scope, receive, send)

asyncio.run(test())
