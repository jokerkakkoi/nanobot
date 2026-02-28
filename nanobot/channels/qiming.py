"""Qiming channel implementation using FastAPI to receive webhook requests."""

import asyncio
import json
from loguru import logger
from pydantic import BaseModel, Field

from nanobot.bus.queue import MessageBus
from nanobot.channels import BaseChannel
from nanobot.config.schema import QimingConfig
from nanobot.bus.events import OutboundMessage

try:
    # Import packages required for receive qiming webhook requests
    import httpx
    import uvicorn
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    QIMING_AVAILABLE = True
except ImportError:
    QIMING_AVAILABLE = False
    logger.warning("Qiming channel not available: httpx, uvicorn or fastapi not installed")
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

class QimingResponseMessage(BaseModel):
    """Qiming response message model."""
    class TextMsg(BaseModel):
        content: str
        is_mentioned: bool = Field(alias="isMentioned", default=None)
        mention_type: int = Field(alias="mentionType", default=None)
        mentioned_mobile_list: list[str] = Field(alias="mentionedMobileList", default=None)
        group_id: str = Field(alias="groupId")

    type: str = Field(alias="type", default="text")
    text_msg: TextMsg = Field(alias="textMsg")


class QimingChannel(BaseChannel):
    """Qiming channel implementation."""

    name = "qiming"

    def __init__(self, config: QimingConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: QimingConfig = config
        self._http: httpx.AsyncClient | None = None
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

            await self._handle_message(
                sender_id=message.phone,
                chat_id=message.group_id,
                content=message.text_msg.content,
                media=None,
                metadata=None,
                session_key=None,
            )

    async def _send_message(self, msg: OutboundMessage) -> None:
        """Send a message through the Qiming channel."""

        if not self._running:
            logger.warning("Qiming channel server not running")
            return
        if not msg.content:
            logger.warning("Empty message content to send")
            return

        logger.info(f"Sending message to Qiming: {msg}")
        _body = {
            "textMsg": {
                "content": msg.content,
                "groupId": msg.chat_id,
            }
        }
        if msg.reply_to:
            _body["textMsg"]["mentionedMobileList"] = [msg.reply_to]
            _body["textMsg"]["isMentioned"] = True
            _body["textMsg"]["mentionType"] = 2

        _response_body = QimingResponseMessage(**_body)
        logger.info(f"Response message to Qiming: {_response_body}")
        logger.info(f"Webhook URL: {self.config.webhook_url}")
        resp = await self._http.post(
            self.config.webhook_url,
            json=_response_body.model_dump(exclude_none=True, by_alias=True)
        )
        logger.info(f"Sent message to Qiming: {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            logger.error(f"Failed to send message to Qiming: {resp.status_code} {resp.text}")

    async def start(self) -> None:
        """Start the Qiming FastAPI server."""
        if not QIMING_AVAILABLE:
            logger.error("Qiming FastAPI not installed. Run: pip install -r requirements.txt")
            return
        
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
            self._http = httpx.AsyncClient()
            self._running = True
            await self._server.serve()
        except asyncio.CancelledError:
            logger.info("Qiming channel server cancelled")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the Qiming FastAPI server."""
        
        if not self._server or not self._server.started:
            logger.warning("Qiming channel server not running")
            return
        self._server.should_exit = True
        await self._server.shutdown()
        self._server = None
        # Close the shared HTTP client
        if self._http:
            await self._http.aclose()
            self._http = None
        self._running = False
        logger.info("Qiming channel server stopped")

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through the Qiming channel."""

        if not self._running:
            logger.warning("Qiming channel server not running")
            return
        await self._send_message(msg)
