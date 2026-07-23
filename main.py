import uvicorn
from gateway import app

if __name__ == "__main__":
    print("AUTOBOT Gateway starting on http://0.0.0.0:8002")
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
