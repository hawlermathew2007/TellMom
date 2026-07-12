import multiprocessing
import time

import httpx
import uvicorn

from proxy.main import app as proxy_app
from backend.main import app as backend_app


def run_proxy():
    uvicorn.run(proxy_app, host="127.0.0.1", port=8000, log_level="warning")


def run_backend():
    uvicorn.run(backend_app, host="127.0.0.1", port=8001, log_level="warning")


def wait_until_ready(url: str, timeout: float = 10):
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=1)
            if r.status_code < 500:
                return
        except Exception:
            pass

        time.sleep(0.1)

    raise RuntimeError(f"{url} never became ready")


def test():
    backend = multiprocessing.Process(target=run_backend)
    proxy = multiprocessing.Process(target=run_proxy)

    backend.start()
    proxy.start()

    try:
        wait_until_ready("http://127.0.0.1:8001/health")
        wait_until_ready("http://127.0.0.1:8000/health")

        r = httpx.get("http://127.0.0.1:8000/api/fetch")

        assert r.status_code == 200

    finally:
        proxy.terminate()
        backend.terminate()

        proxy.join()
        backend.join()
