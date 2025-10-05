from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psutil
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = time.time()

@app.get("/health")
async def health():
    uptime = int(time.time() - start_time)

    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage('/')

    return {
        "status": "ok",
        "uptime_seconds": uptime,
        "cpu_percent": cpu_percent,
        "memory": {
            "total_mb": round(memory.total / 1024 / 1024, 2),
            "used_mb": round(memory.used / 1024 / 1024, 2),
            "percent": memory.percent
        },
        "swap": {
            "total_mb": round(swap.total / 1024 / 1024, 2),
            "used_mb": round(swap.used / 1024 / 1024, 2),
            "percent": swap.percent
        },
        "disk": {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "percent": disk.percent
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
