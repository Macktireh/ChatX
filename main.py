from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes.chat import router as chat_router
from routes.sse import router as sse_router

app = FastAPI(title="Chat App")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(chat_router)
app.include_router(sse_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=1)
