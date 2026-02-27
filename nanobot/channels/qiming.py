"""Qiming channel implementation using FastAPI to receive webhook requests."""

from locale import str
import asyncio

from loguru import logger
from pydantic import BaseModel, Field

from nanobot.config.schema import QimingConfig

try:
    # Import packages required for receive qiming webhook requests
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import uvicorn
    import json
    QIMING_AVAILABLE = True
except ImportError:
    QIMING_AVAILABLE = False
    pass

class QimingMessage(BaseModel):
    """Qiming message model."""
    class TextMsg(BaseModel):
        content: str

    type: str
    callback_url: str = Field(alias="callBackUrl")
    callback_method: str = Field(alias="callBackMethod")
    phone: str
    group_id: str = Field(alias="groupId")
    tenant_id: int = Field(alias="tenantId", default=1)
    robot_id: str = Field(alias="robotId")
    text_msg: TextMsg = Field(alias="textMsg")

class QimingChannel(Channel):
    """Qiming channel implementation."""

    name = "qiming"

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.config: QimingConfig = config
        self._app: FastAPI = FastAPI()
        self._server: uvicorn.Server = None
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes for qimign webhook."""

        @self._app.post("/webhook")
        async def webhook(request: Request) -> JSONResponse:
            """Handle incoming qiming webhook requests"""
            try:
                data = await request.json()
                message = QimingMessage(**data)
            except json.JSONDecodeError:
                logger.error("Invalid JSON payload in qiming webhook request")
                raise HTTPException(status_code=400, detail="Invalid JSON payload")

            self._handle_message(
                sender_id=message.phone,
                chat_id=message.group_id,
                content=message.text_msg.content,
                media=None,
                metadata=None,
                session_key=None,
            )

    async def start(self) -> None:
        """Start the Qiming FastAPI server."""
        if not QIMING_AVAILABLE:
            logger.error("Qiming FastAPI not installed. Run: pip install -r requirements.txt")
            return
        
        # @TODO: link port with config
        self._server = uvicorn.Server(
            config=uvicorn.Config(
                app=self._app,
                host=self.config.host,
                port=self.config.port,
                log_level="info",
            )
        )
         # Run the server
        try:
            await self._server.serve()
            self._running = True
        except asyncio.CancelledError:
            logger.info("Qiming channel server cancelled")
        finally:
            self._running = False

