from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "It works!"}

@app.get("/test")
def read_test():
    return {"message": "Test route works!"}
