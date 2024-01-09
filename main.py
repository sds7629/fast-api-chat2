import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

# from urllib3 import

templates = Jinja2Templates(directory="templates")

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logging.error(f"{request}: {exc_str}")
    content = {"status_code": 10422, "message": exc_str, "data": None}
    return JSONResponse(
        content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


class SocketManager:
    def __init__(self):
        self.active_connections: List[(WebSocket, str)] = []

    async def connect(self, websocket: WebSocket, user: str):
        await websocket.accept()
        self.active_connections.append((websocket, user))

    def disconnet(self, websocket: WebSocket, user: str):
        self.active_connections.remove((websocket, user))

    async def broadcast(self, data):
        for connection in self.active_connections:
            await connection[0].send_json(data)


manager = SocketManager()


@app.get("/api/current_user")
def get_user(request: Request):
    return request.cookies.get("X-Authorization")


class RegisterValidator(BaseModel):
    username: str


@app.post("/api/register")
def register_user(user: RegisterValidator, response: Response):
    response.set_cookie(key="X-Authorization", value=user.username, httponly=True)


@app.get("/")
def get_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/chat")
def get_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.websocket("/api/chat")
async def chat(websocket: WebSocket):
    sender = websocket.cookies.get("X-Authorization")
    if sender:
        await manager.connect(websocket, sender)
        response = {
            "sender": sender,
            "message": "got connected",
        }
        await manager.broadcast(response)
        try:
            while True:
                data = await websocket.receive_json()
                await manager.broadcast(data)
        except WebSocketDisconnect:
            manager.disconnet(websocket, sender)
            response["message"] = "left"
            await manager.broadcast(response)


# @app.get("/client")
# async def client(request: Request):
#     return templates.TemplateResponse("client.html", {"request": request})


# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     print(f"client conneted: {websocket.client}")
#     await websocket.accept()
#     await websocket.send_text(f"Welcome client: {websocket.client}")
#     while True:
#         data = await websocket.receive_text()
#         print(f"message received: {data} from: {websocket.client}")
#         await websocket.send_text(f"Message text was: {data}")


# def run():
#     import uvicorn

#     uvicorn.run(app)


# if __name__ == "__main__":
#     run()
