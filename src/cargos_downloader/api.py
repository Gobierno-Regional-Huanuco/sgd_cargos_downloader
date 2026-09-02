from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

import requests


class SgdApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class SgdApiClient:
    def __init__(self, service_url: str, token: str | None = None, timeout: int = 45, max_retries: int = 6):
        self.service_url = service_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def login(self, username: str, password: str) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "api/cargos/login",
            json={"adm_email": username, "password": password},
        )
        token = payload.get("token")
        if not token:
            raise SgdApiError("El servicio no devolvio token de acceso.")
        self.set_token(token)
        return payload

    def logout(self) -> None:
        try:
            self._request("POST", "api/cargos/logout")
        except SgdApiError:
            pass

    def me(self) -> dict[str, Any]:
        return self._request("GET", "api/cargos/me")

    def offices(self) -> list[dict[str, Any]]:
        return self._request("GET", "api/cargos/oficinas").get("data", [])

    def documents(
        self,
        *,
        scope: str,
        depe_id: int,
        page: int,
        per_page: int,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        include_files: bool = True,
        include_personal: bool = False,
        with_total: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "scope": scope,
            "depe_id": depe_id,
            "page": page,
            "per_page": per_page,
            "include_files": int(include_files),
        }
        if fecha_desde:
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            params["fecha_hasta"] = fecha_hasta
        if include_personal:
            params["include_personal"] = 1
        if with_total:
            params["with_total"] = 1
        return self._request("GET", "api/cargos/documentos", params=params)

    def related_documents(
        self,
        document_id: int,
        *,
        scope: str,
        depe_id: int,
        page: int,
        per_page: int,
        include_files: bool = True,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"api/cargos/documentos/{document_id}/relacionados",
            params={
                "scope": scope,
                "depe_id": depe_id,
                "page": page,
                "per_page": per_page,
                "include_files": int(include_files),
            },
        )

    def related_documents_batch(
        self,
        document_ids: list[int],
        *,
        scope: str,
        depe_id: int,
        include_files: bool = True,
        page: int = 1,
        per_page: int = 500,
        with_total: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "api/cargos/documentos/relacionados/batch",
            json={
                "scope": scope,
                "depe_id": depe_id,
                "document_ids": document_ids,
                "include_files": int(include_files),
                "page": page,
                "per_page": per_page,
                "with_total": int(with_total),
            },
        )

    def download_file(
        self,
        file_id: int,
        destination: Path,
        *,
        scope: str,
        depe_id: int,
        master_id: int | None = None,
        progress: Callable[[int], None] | None = None,
    ) -> None:
        params: dict[str, Any] = {"scope": scope, "depe_id": depe_id}
        if master_id:
            params["master_id"] = master_id

        url = self._url(f"api/cargos/archivos/{file_id}/download")
        response = self._send_with_retries("GET", url, params=params, stream=True)
        if response.status_code >= 400:
            raise self._error_from_response(response)

        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".part")
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)
                    if progress:
                        progress(len(chunk))
        partial.replace(destination)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._send_with_retries(method, self._url(path), **kwargs)
        if response.status_code >= 400:
            raise self._error_from_response(response)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise SgdApiError("El servicio devolvio una respuesta no JSON.") from exc

    def _url(self, path: str) -> str:
        return urljoin(self.service_url, path.lstrip("/"))

    def _send_with_retries(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code != 429 or attempt >= self.max_retries:
                return response
            response.close()
            time.sleep(self._retry_delay(attempt, response))
        return response

    @staticmethod
    def _retry_delay(attempt: int, response: requests.Response) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(1.0, min(float(retry_after), 120.0))
            except ValueError:
                pass
        return min(2.0 * (attempt + 1), 30.0)

    @staticmethod
    def _error_from_response(response: requests.Response) -> SgdApiError:
        payload: Any = None
        message = f"Error HTTP {response.status_code}"
        try:
            payload = response.json()
            message = payload.get("message", message)
        except ValueError:
            if response.text:
                message = response.text[:300]
        return SgdApiError(message, response.status_code, payload)
