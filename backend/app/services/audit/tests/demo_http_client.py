"""Small in-process HTTP/ASGI test driver using only Python's standard library.

Runs the real middleware, routing, body parsing, dependencies and response stack.
No HTTP test dependency is installed in the existing backend image.
"""
import asyncio
import json
from http.cookies import SimpleCookie
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit
from uuid import uuid4


class Cookies(dict):
    def set(self, name, value):
        self[name] = value


class ASGIClient:
    def __init__(self, app):
        self.app, self.cookies, self.headers = app, Cookies(), {}

    def get(self, path, **kwargs): return self.request('GET', path, **kwargs)
    def post(self, path, **kwargs): return self.request('POST', path, **kwargs)
    def delete(self, path, **kwargs): return self.request('DELETE', path, **kwargs)

    def request(self, method, path, data=None, files=None, headers=None, follow_redirects=True):
        outgoing = {k.lower():v for k,v in {**self.headers, **(headers or {})}.items()}
        body = b''
        if files:
            boundary = 'diptest' + uuid4().hex
            for key, value in (data or {}).items():
                body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            for key, (filename, payload) in files.items():
                body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + payload + b'\r\n'
            body += f'--{boundary}--\r\n'.encode()
            outgoing['content-type'] = 'multipart/form-data; boundary=' + boundary
        elif data is not None:
            body = urlencode(data).encode()
            outgoing['content-type'] = 'application/x-www-form-urlencoded'
        outgoing['host'] = 'testserver'
        outgoing['content-length'] = str(len(body))
        outgoing['cookie'] = '; '.join(f'{k}={v}' for k,v in self.cookies.items())
        parts = urlsplit(path)
        scope = {'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1',
                 'method':method,'scheme':'http','path':parts.path,'raw_path':parts.path.encode(),
                 'query_string':parts.query.encode(),'root_path':'','server':('testserver',80),
                 'client':('testclient',12345),'headers':[(k.encode(),v.encode()) for k,v in outgoing.items()]}
        messages = []
        async def run():
            delivered = False
            async def receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type':'http.request','body':body,'more_body':False}
                return {'type':'http.disconnect'}
            async def send(message): messages.append(message)
            await self.app(scope, receive, send)
        asyncio.run(run())
        start = next(m for m in messages if m['type'] == 'http.response.start')
        response_headers = {k.decode():v.decode() for k,v in start['headers']}
        for key, value in start['headers']:
            if key == b'set-cookie':
                parsed = SimpleCookie(); parsed.load(value.decode())
                for k, v in parsed.items(): self.cookies[k] = v.value
        payload = b''.join(m.get('body', b'') for m in messages if m['type'] == 'http.response.body')
        result = SimpleNamespace(status_code=start['status'], headers=response_headers, content=payload,
                                 text=payload.decode('utf-8',errors='replace'), json=lambda: json.loads(payload))
        if follow_redirects and result.status_code in {301,302,303,307,308}:
            return self.get(result.headers['location'], follow_redirects=False)
        return result
