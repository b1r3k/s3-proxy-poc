import httpx


class AsyncHttpClient:
    def __init__(self, max_keepalive_connections=100, max_connections=1000):
        self._limits = httpx.Limits(
            max_keepalive_connections=max_keepalive_connections, max_connections=max_connections
        )
        self._session = None

    async def _get_session(self):
        if self._session is None:
            self._session = await httpx.AsyncClient(limits=self._limits).__aenter__()
        return self._session

    async def close_session(self):
        if self._session is not None:
            try:
                await self._session.__aexit__(None, None, None)
                self._session = None
            except Exception:
                pass

    async def request(self, *args, **kwargs):
        session = await self._get_session()
        try:
            return await session.request(*args, **kwargs)
        except RuntimeError:
            await self.close_session()
            self._session = None
            return await self.request(*args, **kwargs)
