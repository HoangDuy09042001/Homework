from fastapi import FastAPI
from router.api import router  # Replace with the actual filename where the above router is defined

app = FastAPI()
app.include_router(router, prefix="/image-text")