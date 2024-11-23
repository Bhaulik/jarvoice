from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Jarvoice API",
    description="Personal AI Assistant API that can manage tasks through phone calls & texts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Jarvoice API",
        "status": "active"
    }

# Health check endpoint
@app.get("/events")
async def health_check():
    return {
        "event": "jarvoice-api",
        "service": "jarvoice-api"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)