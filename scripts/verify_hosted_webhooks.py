"""Synthetic receipt checks against only the disposable loopback hosting fixture."""
import hashlib
import hmac
import http.client
import json
import os
import sys
from urllib.parse import urlsplit
import uuid


def main():
    target = urlsplit(sys.argv[1])
    if target.scheme != 'http' or target.hostname != '127.0.0.1' or not target.port:
        raise SystemExit('Only the disposable HTTP loopback fixture is supported')
    secret = os.environ['SLICKFLOW_FIXTURE_WEBHOOK_SECRET'].encode()

    def request(expected, body=b'{}', delivery=None, event='ping', signature=True,
                method='POST', path='/webhooks/github', extra=None):
        headers = {'Content-Type': 'application/json', 'X-GitHub-Event': event,
                   'X-GitHub-Delivery': delivery or str(uuid.uuid4())}
        if signature:
            headers['X-Hub-Signature-256'] = 'sha256=' + hmac.new(secret, body, hashlib.sha256).hexdigest()
        if extra:
            headers.update(extra)
        connection = http.client.HTTPConnection(target.hostname, target.port, timeout=10)
        try:
            try:
                connection.request(method, path, body, headers)
            except BrokenPipeError:
                # A server may reject Content-Length before consuming all bytes.
                # Still require its actual HTTP response to be exactly 413.
                if expected != 413:
                    raise
            response = connection.getresponse()
            response.read()
            if response.status != expected:
                raise SystemExit(f'Fixture receipt check expected {expected}, got {response.status}')
        finally:
            connection.close()

    delivery = str(uuid.uuid4())
    request(202, delivery=delivery)
    request(200, delivery=delivery)
    request(409, body=b'{"zen":"synthetic"}', delivery=delivery)
    issue = json.dumps({'action': 'opened', 'repository': {'id': 10},
                        'installation': {'id': 20}, 'issue': {'id': 30, 'number': 8}}).encode()
    request(202, body=issue, event='issues')
    request(401, signature=False)
    request(401, extra={'X-Hub-Signature-256': 'sha256=' + '0' * 64})
    request(415, extra={'Content-Encoding': 'gzip'})
    request(413, body=b' ' * 1048577)
    print('PASS: synthetic signed receipt, retry/conflict, issue, signature and encoding checks')


if __name__ == '__main__':
    main()
