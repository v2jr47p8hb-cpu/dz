"""Общие утилиты парсера ОГЭ: HTTP с повторами, пути, CA-бандл для oge.fipi.ru."""
import os, time, pathlib, subprocess, requests

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUT = ROOT / "out"
SITE = ROOT.parent.parent / "oge"
FIPI_PROJ = "DE0E276E497AB3784C3FC4CC20248DC0"
FIPI = "https://oge.fipi.ru/bank/"
CACHE.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

GS_URL = "https://secure.globalsign.com/cacert/gsgccr3dvtlsca2020.crt"


def ca_bundle():
    """oge.fipi.ru не отдаёт промежуточный сертификат GlobalSign — докладываем его сами (проверку TLS не отключаем)."""
    pem = CACHE / "ca.pem"
    if not pem.exists():
        der = CACHE / "gs.crt"
        der.write_bytes(requests.get(GS_URL, timeout=30).content)
        gs = subprocess.run(["openssl", "x509", "-inform", "DER", "-in", str(der)],
                            capture_output=True, check=True).stdout
        base = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
        if not os.path.exists(base):
            import certifi
            base = certifi.where()
        pem.write_bytes(pathlib.Path(base).read_bytes() + b"\n" + gs)
    return str(pem)


class Http:
    def __init__(self, delay=2.0, verify=True, headers=None):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "Mozilla/5.0 (startum-oge-bank; educational)"
        if headers:
            self.s.headers.update(headers)
        self.delay = delay
        self.verify = verify
        self.last = 0.0

    def req(self, method, url, tries=6, **kw):
        for i in range(tries):
            wait = self.delay - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                r = self.s.request(method, url, verify=self.verify, timeout=60, **kw)
                if r.status_code >= 500:
                    raise requests.HTTPError(f"{r.status_code}")
                return r
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                if i == tries - 1:
                    raise
                print(f"  повтор {i + 1} ({e.__class__.__name__}: {str(e)[:80]})", flush=True)
                time.sleep(2 * (i + 1))

    def get(self, url, **kw):
        return self.req("GET", url, **kw)

    def post(self, url, **kw):
        return self.req("POST", url, **kw)
