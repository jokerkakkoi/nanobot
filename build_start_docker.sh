
docker build -t nanobot:qiming-v11 .

docker run -dt -v /home/aiops/project/.nanobot:/root/.nanobot -p 18790:18790 -p 30001:8000 nanobot:qiming-v11 gateway

OutboundMessage(channel='qiming', chat_id='2027558912690466817', content='你好！我是 nanobot 🐈，一个 AI 助手。\n\n有什么我可以帮你的吗？', reply_to=None, media=[], metadata={})
