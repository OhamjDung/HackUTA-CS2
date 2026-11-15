"""Event loop for uvicorn on Windows: `uvicorn ... --loop match_service.loop:selector_loop`.

uvicorn's default on Windows is asyncio's ProactorEventLoop. When a client resets its connection at the
wrong moment, the proactor's accept loop logs "[WinError 64] The specified network name is no longer
available / Accept failed on a socket" and CLOSES THE LISTENING SOCKET. The process stays alive but
nothing answers any more, and the demo pages show "Failed to fetch". Seen on Tom's PC (2026-11-15).
The selector loop keeps listening after a failed accept. The service only uses TCP sockets and httpx,
which the selector loop supports.
"""

import asyncio

selector_loop = asyncio.SelectorEventLoop
