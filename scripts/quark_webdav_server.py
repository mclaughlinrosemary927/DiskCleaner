"""Expose the authorized Quark drive as a local, read-only WebDAV endpoint."""

from __future__ import annotations

import argparse
import json
import logging
import threading
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx
from quark_client import QuarkClient


DAV_NS = "DAV:"
ROOT_ID = "0"


class QuarkDrive:
    def __init__(self, cookies_file: Path) -> None:
        raw = json.loads(cookies_file.read_text(encoding="utf-8"))
        cookies = "; ".join(
            f"{item['name']}={item['value']}" for item in raw["cookies"]
        )
        self.client = QuarkClient(cookies=cookies, auto_login=False)
        self.lock = threading.Lock()
        self.children: dict[str, list[dict[str, Any]]] = {}
        self._capacity: tuple[int, int] | None = None
        self._capacity_updated_at = 0.0

    def list_folder(self, folder_id: str) -> list[dict[str, Any]]:
        with self.lock:
            response = self.client.list_files(folder_id, size=100)
        if response.get("status") != 200:
            raise RuntimeError(response.get("message", "Quark request failed"))
        entries = response.get("data", {}).get("list", [])
        self.children[folder_id] = entries
        return entries

    def resolve(self, path: str) -> tuple[str, dict[str, Any] | None]:
        parts = [part for part in path.strip("/").split("/") if part]
        folder_id = ROOT_ID
        item: dict[str, Any] | None = None
        for part in parts:
            item = next(
                (entry for entry in self.list_folder(folder_id)
                 if entry.get("file_name") == part),
                None,
            )
            if item is None:
                raise FileNotFoundError(path)
            folder_id = item["fid"]
        return folder_id, item

    def download_url(self, file_id: str) -> str:
        with self.lock:
            return self.client.get_download_url(file_id)

    def capacity(self) -> tuple[int, int]:
        """Return Quark's real (free_bytes, used_bytes) account quota."""
        if self._capacity and time.monotonic() - self._capacity_updated_at < 60:
            return self._capacity
        with self.lock:
            response = self.client.api_client.get("member")
        data = response.get("data", {})
        total = int(data.get("total_capacity", 0))
        used = int(data.get("use_capacity", 0))
        if total <= 0 or used < 0 or used > total:
            raise RuntimeError("Quark did not return a valid capacity")
        self._capacity = (total - used, used)
        self._capacity_updated_at = time.monotonic()
        return self._capacity


class Handler(BaseHTTPRequestHandler):
    drive: QuarkDrive

    server_version = "DiskCleaner-QuarkDAV/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        logging.info("%s - %s", self.address_string(), fmt % args)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("DAV", "1")
        self.send_header("Allow", "OPTIONS, PROPFIND, GET, HEAD")
        self.end_headers()

    def do_PROPFIND(self) -> None:
        try:
            path = unquote(urlparse(self.path).path)
            folder_id, item = self.drive.resolve(path)
            is_directory = item is None or bool(item.get("dir"))
            entries = self.drive.list_folder(folder_id) if is_directory else []
            root = Element(f"{{{DAV_NS}}}multistatus")
            self._append_prop(root, path, item, is_directory)
            if self.headers.get("Depth", "0") != "0" and is_directory:
                for entry in entries:
                    child_path = path.rstrip("/") + "/" + quote(entry["file_name"])
                    self._append_prop(root, child_path, entry, bool(entry.get("dir")))
            body = tostring(root, encoding="utf-8", xml_declaration=True)
            self.send_response(HTTPStatus.MULTI_STATUS)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as error:
            logging.exception("PROPFIND failed")
            self.send_error(HTTPStatus.BAD_GATEWAY, str(error))

    def _append_prop(
        self, root: Element, path: str, item: dict[str, Any] | None, is_directory: bool
    ) -> None:
        response = SubElement(root, f"{{{DAV_NS}}}response")
        href = quote(path if path.startswith("/") else "/" + path, safe="/%")
        SubElement(response, f"{{{DAV_NS}}}href").text = href + ("/" if is_directory and not href.endswith("/") else "")
        propstat = SubElement(response, f"{{{DAV_NS}}}propstat")
        prop = SubElement(propstat, f"{{{DAV_NS}}}prop")
        SubElement(prop, f"{{{DAV_NS}}}displayname").text = (
            item.get("file_name") if item else "夸克网盘"
        )
        resource_type = SubElement(prop, f"{{{DAV_NS}}}resourcetype")
        if is_directory:
            SubElement(resource_type, f"{{{DAV_NS}}}collection")
        if not is_directory:
            SubElement(prop, f"{{{DAV_NS}}}getcontentlength").text = str(item.get("size", 0))
        if item is None:
            free_bytes, used_bytes = self.drive.capacity()
            SubElement(prop, f"{{{DAV_NS}}}quota-available-bytes").text = str(free_bytes)
            SubElement(prop, f"{{{DAV_NS}}}quota-used-bytes").text = str(used_bytes)
        timestamp = (item or {}).get("updated_at")
        if timestamp:
            try:
                dt = datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)
                SubElement(prop, f"{{{DAV_NS}}}getlastmodified").text = format_datetime(dt, usegmt=True)
            except (TypeError, ValueError, OSError):
                pass
        SubElement(propstat, f"{{{DAV_NS}}}status").text = "HTTP/1.1 200 OK"

    def do_HEAD(self) -> None:
        self._send_file(head_only=True)

    def do_GET(self) -> None:
        self._send_file(head_only=False)

    def _send_file(self, head_only: bool) -> None:
        try:
            path = unquote(urlparse(self.path).path)
            _, item = self.drive.resolve(path)
            if item is None or item.get("dir"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            url = self.drive.download_url(item["fid"])
            if not url:
                raise RuntimeError("Quark did not return a download URL")
            headers = {"Range": self.headers.get("Range", "")} if self.headers.get("Range") else {}
            with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=60) as response:
                self.send_response(response.status_code)
                for key in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                    if response.headers.get(key):
                        self.send_header(key, response.headers[key])
                self.end_headers()
                if not head_only:
                    for chunk in response.iter_bytes():
                        self.wfile.write(chunk)
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as error:
            logging.exception("GET failed")
            self.send_error(HTTPStatus.BAD_GATEWAY, str(error))

    def do_PUT(self) -> None:
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "The mounted Quark drive is read-only")

    do_DELETE = do_PUT
    do_MKCOL = do_PUT
    do_MOVE = do_PUT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cookies", required=True, type=Path)
    parser.add_argument("--port", default=5245, type=int)
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    if args.log:
        logging.basicConfig(filename=args.log, level=logging.INFO, encoding="utf-8")
    else:
        logging.basicConfig(level=logging.INFO)
    Handler.drive = QuarkDrive(args.cookies)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
