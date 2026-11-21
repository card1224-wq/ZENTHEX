"""Offline regression tests; no production connection and no exchange orders."""
import gzip
import json
import unittest
from unittest.mock import patch

import httpx
from starlette.testclient import TestClient
import zenthex_gateway as gateway


class Bytes(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data
        self.closed = False

    async def __aiter__(self):
        yield self.data

    async def aclose(self):
        self.closed = True


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.streams = []
        self.mode = "ok"

        def handler(request):
            self.requests.append(request)
            if self.mode == "fail":
                raise httpx.ConnectError("sensitive internal diagnostic", request=request)
            path = request.url.path
            headers = [("content-type", "application/json")]
            status = 200
            if path == "/api/health":
                data = {"status": "ok", "service": "zenthex-saas"}
            elif path == "/api/finance/server-ip":
                data = {"server_ip": "13.124.81.242" if self.mode != "wrong-ip" else "74.220.52.254"}
            elif path in ("/api/auth/signup", "/api/auth/dev/outbox"):
                status = 403 if self.mode != "unguarded" else 200
                data = {}
            elif path == "/redirect":
                status = 307
                headers.append(("location", "https://13.124.81.242/finance.html?x=1#trade"))
                data = {}
            elif path == "/api/session":
                # Cookie jar contamination across different visitors is forbidden.
                headers.append(("set-cookie", "session=visitor-one; Path=/; Secure; HttpOnly"))
                data = {}
            elif path == "/gzip":
                stream = Bytes(gzip.compress(b"binary payload"))
                self.streams.append(stream)
                return httpx.Response(200, stream=stream, headers={"content-encoding": "gzip"})
            elif path == "/headers":
                headers.extend([("connection", "x-private"), ("x-private", "remove"),
                                ("set-cookie", "one=1; Secure"), ("set-cookie", "two=2; Secure")])
                data = {}
            else:
                data = {"path": path, "query": request.url.query.decode(),
                        "body": request.content.decode(errors="replace"), "method": request.method}
            stream = Bytes(json.dumps(data).encode())
            self.streams.append(stream)
            return httpx.Response(status, stream=stream, headers=headers)

        self.transport = httpx.MockTransport(handler)
        self.patcher = patch.object(gateway.httpx, "AsyncHTTPTransport", return_value=self.transport)
        self.factory = self.patcher.start()
        self.client = TestClient(gateway.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.patcher.stop()

    def test_https_verification_and_no_retries(self):
        self.assertEqual(self.factory.call_args.kwargs,
                         {"retries": 0, "verify": True, "trust_env": False})

    def test_pages_use_aws_and_public_address_stays(self):
        for path in ["/", "/finance.html", "/studio.html", "/stock.html", "/research.html", "/static/network-status.js"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["x-zenthex-backend"], "aws")
            self.assertEqual(self.requests[-1].url.host, "13.124.81.242")

    def test_login_body_query_auth_cookie_and_response_close(self):
        response = self.client.post("/api/auth/login?tag=%ED%95%9C%EA%B8%80&x=1&x=2",
                                    json={"email": "test@example.invalid", "password": "only-offline"},
                                    headers={"authorization": "Bearer offline", "cookie": "own=one"})
        self.assertEqual(response.status_code, 200)
        upstream = self.requests[-1]
        self.assertEqual(upstream.headers["authorization"], "Bearer offline")
        self.assertEqual(upstream.headers["cookie"], "own=one")
        self.assertEqual(json.loads(upstream.content)["password"], "only-offline")
        self.assertEqual(upstream.url.query, b"tag=%ED%95%9C%EA%B8%80&x=1&x=2")
        self.assertTrue(self.streams[-1].closed)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_no_cookie_leak_between_visitors(self):
        self.client.get("/api/session")
        # New browser, sharing only the backend connection pool.
        self.client.cookies.clear()
        self.client.get("/api/another-user")
        self.assertNotIn("cookie", self.requests[-1].headers)

    def test_client_cannot_override_destination_or_forwarded_ip(self):
        self.client.get("/api/health?url=https://attacker.invalid", headers={
            "host": "attacker.invalid", "x-forwarded-for": "127.0.0.1",
            "x-forwarded-host": "attacker.invalid", "forwarded": "for=127.0.0.1",
            "x-real-ip": "127.0.0.1", "connection": "x-injected", "x-injected": "secret"})
        upstream = self.requests[-1]
        self.assertEqual(str(upstream.url).split("/api")[0], gateway.DEFAULT_ORIGIN)
        self.assertEqual(upstream.headers["host"], "13.124.81.242")
        for key in ["forwarded", "x-forwarded-for", "x-forwarded-host", "x-real-ip", "x-injected"]:
            self.assertNotIn(key, upstream.headers)

    def test_encoded_path_cannot_change_host(self):
        self.client.get("/%2Fattacker.invalid/api/health")
        self.assertEqual(self.requests[-1].url.host, "13.124.81.242")

    def test_unsafe_routes_block_before_proxy(self):
        for path in ["/api/auth/signup", "/api/auth/password/reset", "/api/auth/dev/outbox",
                     "/api/auth/phone/send-code", "/api/auth/password%2Freset",
                     "/api/auth/password%252Freset", "/api//auth/signup", "/api/auth/a/%2e%2e/signup"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path).status_code, 403)
        self.assertEqual(self.requests, [])

    def test_hidden_paths_block(self):
        for path in ["/.env", "/.git/config", "/%2eenv", "/static/.secret"]:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.requests, [])

    def test_large_upload_not_forwarded(self):
        with patch.object(gateway, "MAX_BODY", 10):
            self.assertEqual(self.client.post("/api/studio/upload", content=b"x" * 11).status_code, 413)
        self.assertEqual(self.requests, [])

    def test_binary_upload_preserved(self):
        self.client.post("/api/studio/upload", files={"file": ("test.bin", b"\x00\x01\xff")})
        self.assertIn(b"\x00\x01\xff", self.requests[-1].content)
        self.assertIn("multipart/form-data", self.requests[-1].headers["content-type"])

    def test_aws_redirect_keeps_render_address(self):
        response = self.client.get("/redirect", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/finance.html?x=1#trade")
        self.assertEqual(len(self.requests), 1)

    def test_no_double_decompression(self):
        self.assertEqual(self.client.get("/gzip").content, b"binary payload")

    def test_repeated_response_headers_and_hop_headers(self):
        response = self.client.get("/headers")
        self.assertEqual(len(response.headers.get_list("set-cookie")), 2)
        self.assertNotIn("x-private", response.headers)
        self.assertNotIn("connection", response.headers)

    def test_failure_no_retry_no_local_engine(self):
        self.mode = "fail"
        response = self.client.post("/api/finance/start", json={"offline": True})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("sensitive internal", response.text)
        self.assertEqual(len(self.requests), 1)
        import sys
        self.assertNotIn("trading.engine", sys.modules)
        self.assertNotIn("database.session", sys.modules)

    def test_readiness_checks_backend_and_guards(self):
        self.assertEqual(self.client.get("/_gateway/health").status_code, 200)
        self.assertTrue(all(request.method == "GET" for request in self.requests))
        for mode in ["wrong-ip", "unguarded", "fail"]:
            self.mode = mode
            self.assertEqual(self.client.get("/_gateway/health").status_code, 503)

    def test_trace_not_forwarded(self):
        self.assertEqual(self.client.request("TRACE", "/api/health").status_code, 405)
        self.assertEqual(self.requests, [])


class OriginTests(unittest.TestCase):
    def test_unsafe_origins_refused(self):
        for value in ["http://13.124.81.242", "https://127.0.0.1", "https://10.0.0.1",
                      "https://user:password@13.124.81.242", "https://13.124.81.242:8000",
                      "https://13.124.81.242/path", "https://zenthex-saas.onrender.com",
                      "https://13.124.81.242?next=bad", "https://13.124.81.242#bad"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                gateway.backend_origin(value)
        self.assertEqual(gateway.backend_origin("https://13.124.81.242/"), gateway.DEFAULT_ORIGIN)


class RealTLSVerificationTests(unittest.TestCase):
    def test_real_https_rejects_untrusted_cert_and_passes_with_test_ca(self):
        import http.server
        import ssl
        import subprocess
        import tempfile
        import threading
        from pathlib import Path

        hits = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok","service":"zenthex-saas"}')

            def log_message(self, *args):
                pass

        with tempfile.TemporaryDirectory(prefix="zenthex-gateway-tls-") as directory:
            path = Path(directory)
            cert, key = path / "cert.pem", path / "key.pem"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                            "-days", "1", "-subj", "/CN=Local test only",
                            "-addext", "subjectAltName=IP:127.0.0.1", "-keyout", str(key),
                            "-out", str(cert)], check=True, capture_output=True)
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            local_origin = "https://127.0.0.1:" + str(server.server_port)
            try:
                # Override only the destination validator for a local test server.
                # Production TLS must reject its self-signed certificate, even with env CA set.
                with patch.object(gateway, "backend_origin", return_value=local_origin), \
                        patch.dict("os.environ", {"SSL_CERT_FILE": str(cert)}):
                    with TestClient(gateway.app) as client:
                        self.assertEqual(client.get("/api/health").status_code, 502)
                    self.assertEqual(hits, [])
                    # Explicit temporary CA only in the test transport; verify the real HTTPS proxy.
                    trusted = ssl.create_default_context(cafile=str(cert))
                    transport = httpx.AsyncHTTPTransport(verify=trusted, retries=0, trust_env=False)
                    with patch.object(gateway.httpx, "AsyncHTTPTransport", return_value=transport):
                        with TestClient(gateway.app) as client:
                            response = client.get("/api/health")
                            self.assertEqual(response.status_code, 200)
                            self.assertEqual(response.json()["status"], "ok")
                            self.assertEqual(response.headers["X-Zenthex-Backend"], "aws")
                    self.assertEqual(hits, ["/api/health"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


class PublicCheckTests(unittest.TestCase):
    def test_read_only_checker_requires_gateway_and_three_ip_matches(self):
        import contextlib
        import io
        import zenthex_connection_check as check

        paths = []
        observations = 3

        def get(origin, path):
            paths.append(path)
            headers = {"X-Zenthex-Backend": "aws"}
            if path == "/api/health":
                return 200, {"status": "ok", "service": "zenthex-saas"}, headers
            if path == "/_gateway/health":
                return 200, {"mode": "render-gateway"}, headers
            if path == "/api/finance/server-ip":
                return 200, {"server_ip": "13.124.81.242"}, headers
            if path == "/api/finance/server-ip/verify":
                return 200, {"matches": True, "successful_checks": observations,
                             "outbound_ip": "13.124.81.242"}, headers
            return (403 if path.startswith("/api/auth/") else 200), None, headers

        with patch.object(check, "get", side_effect=get), contextlib.redirect_stdout(io.StringIO()):
            check.check_public(check.PUBLIC, gateway=True, outbound=True)
            observations = 2
            with self.assertRaises(RuntimeError):
                check.check_public(check.PUBLIC, gateway=True, outbound=True)
        self.assertTrue(paths)
        for path in paths:
            self.assertNotIn(path, ["/api/finance/start", "/api/finance/stop", "/api/finance/sell-and-stop"])


if __name__ == "__main__":
    unittest.main()
