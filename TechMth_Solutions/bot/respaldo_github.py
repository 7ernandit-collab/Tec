"""Respaldo del Excel en un repositorio PRIVADO de GitHub.

Los servidores gratuitos (como Render) borran su disco cada vez que se reinician o se
duermen. Para no perder los registros:
  • al arrancar, se descarga el Excel guardado en el repositorio privado;
  • cada vez que el Excel cambia, se sube de nuevo (agrupando cambios cada 20 s).

Se activa con las variables de entorno:
  GITHUB_TOKEN        token con permiso "Contents: Read and write" sobre el repositorio
  GITHUB_REPO_DATOS   repositorio privado, por ejemplo  usuario/techmth-datos
  GITHUB_RAMA_DATOS   (opcional) rama, por omisión  main
"""
from __future__ import annotations

import base64
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://api.github.com"


class RespaldoGitHub:
    def __init__(self, token: str, repo: str, ruta_local: Path, ruta_remota: str = "Titulacion_Bot.xlsx",
                 rama: str = "main", espera: float = 20.0):
        self.token = token
        self.repo = repo
        self.ruta_local = Path(ruta_local)
        self.ruta_remota = ruta_remota
        self.rama = rama
        self.espera = espera
        self._temporizador: threading.Timer | None = None
        self._candado = threading.Lock()
        self.ultimo: str = "sin respaldos todavía"

    @classmethod
    def desde_entorno(cls, ruta_local: Path) -> "RespaldoGitHub | None":
        token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPO_DATOS")
        if not token or not repo:
            return None
        return cls(token, repo, ruta_local, rama=os.environ.get("GITHUB_RAMA_DATOS", "main"))

    # ------------------------------------------------------------ HTTP
    def _pedir(self, metodo: str, url: str, cuerpo: dict | None = None, crudo: bool = False):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(url, data=datos, method=metodo, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.raw" if crudo else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TechMth-Solutions",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            contenido = r.read()
        return contenido if crudo else json.loads(contenido or b"{}")

    def _url(self) -> str:
        return f"{API}/repos/{self.repo}/contents/{self.ruta_remota}"

    def _sha(self) -> str | None:
        try:
            return self._pedir("GET", f"{self._url()}?ref={self.rama}").get("sha")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    # ------------------------------------------------------------ uso
    def descargar(self) -> bool:
        """Trae el Excel del repositorio (si existe). Devuelve True si lo descargó."""
        try:
            datos = self._pedir("GET", f"{self._url()}?ref={self.rama}", crudo=True)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.ultimo = "el repositorio aún no tiene Excel; se subirá con el primer registro"
                return False
            self._error(f"no se pudo descargar ({e.code})")
            return False
        except Exception as e:  # noqa: BLE001
            self._error(f"no se pudo descargar ({e})")
            return False
        self.ruta_local.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_local.write_bytes(datos)
        self.ultimo = f"descargado al arrancar · {datetime.now():%d/%m/%Y %H:%M}"
        return True

    def subir(self) -> bool:
        with self._candado:
            try:
                contenido = base64.b64encode(self.ruta_local.read_bytes()).decode()
                cuerpo = {"message": f"Respaldo automático {datetime.now():%Y-%m-%d %H:%M:%S}",
                          "content": contenido, "branch": self.rama}
                sha = self._sha()
                if sha:
                    cuerpo["sha"] = sha
                self._pedir("PUT", self._url(), cuerpo)
            except Exception as e:  # noqa: BLE001
                self._error(f"no se pudo subir ({e})")
                return False
            self.ultimo = f"último respaldo · {datetime.now():%d/%m/%Y %H:%M}"
            return True

    def programar(self):
        """Agrupa varios cambios seguidos en una sola subida."""
        if self._temporizador and self._temporizador.is_alive():
            return
        self._temporizador = threading.Timer(self.espera, self.subir)
        self._temporizador.daemon = True
        self._temporizador.start()

    def _error(self, texto: str):
        self.ultimo = f"⚠ {texto}"
        print(f"[respaldo GitHub] {texto}", file=sys.stderr)
