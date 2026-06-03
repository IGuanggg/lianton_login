import os
import socket
import threading
import time

import webview

from app import app


def port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def choose_port(start=5123):
    for port in range(start, start + 40):
        if port_is_free(port):
            return port
    raise RuntimeError("No available local port found")


def wait_until_ready(port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.15)
    return False


def run_server(port):
    os.environ["OPEN_BROWSER"] = "0"
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def main():
    port = choose_port(int(os.environ.get("PORT", "5123")))
    thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    thread.start()
    wait_until_ready(port)
    webview.create_window(
        "登录态获取",
        f"http://127.0.0.1:{port}",
        width=520,
        height=760,
        min_size=(420, 620),
    )
    webview.start()


if __name__ == "__main__":
    main()
