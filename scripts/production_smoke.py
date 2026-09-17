#!/usr/bin/env python3
"""End-to-end smoke test for an already running production Compose stack.

The test creates a disposable user and one report in PostgreSQL. It never prints
the JWT or password. Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost/api/v1")
    parser.add_argument(
        "--sample",
        type=Path,
        default=Path("example_files/30.03-07.04.2026 Вопросы функционирования контрактной системы_40_ДОТ.xlsx"),
    )
    parser.add_argument("--require-local-ai", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def api_request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
    body: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, object | None]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type

    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            if not raw:
                response_body = None
            try:
                response_body = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                response_body = raw.decode(errors="replace")
            return response.status, response_body
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            response_body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            response_body = raw.decode(errors="replace")
        return error.code, response_body


def multipart_body(
    fields: dict[str, str], files: list[tuple[str, str, bytes]]
) -> tuple[bytes, str]:
    boundary = "----AiReviewSmoke" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )
    for field_name, file_name, content in files:
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{field_name}"; filename="{file_name}"\r\n'.encode(),
                f"Content-Type: {mime_type}\r\n\r\n".encode(),
                content,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    args = parse_args()
    require(args.sample.is_file(), f"Sample file not found: {args.sample}")

    status, _ = api_request(args.base_url, "/analysis/history")
    require(status == 401, f"Unauthenticated API must return 401, got {status}")
    print("auth guard: ok")

    suffix = uuid.uuid4().hex[:12]
    email = f"production-smoke-{suffix}@example.invalid"
    password = "Smoke-Test-Password-2026!"

    status, _ = api_request(
        args.base_url,
        "/auth/register",
        method="POST",
        payload={"username": "Smoke", "email": email, "password": "short"},
    )
    require(status == 400, f"Short password must return 400, got {status}")
    print("registration validation: ok")

    status, auth = api_request(
        args.base_url,
        "/auth/register",
        method="POST",
        payload={"username": "Production Smoke", "email": email, "password": password},
    )
    require(status == 200 and isinstance(auth, dict) and bool(auth.get("token")), "Registration failed")
    token = auth["token"]

    status, login = api_request(
        args.base_url,
        "/auth/login",
        method="POST",
        payload={"email": email.upper(), "password": password},
    )
    require(status == 200 and isinstance(login, dict) and bool(login.get("token")), "Login failed")
    token = login["token"]
    print("register and normalized login: ok")

    status, _ = api_request(
        args.base_url,
        "/auth/register",
        method="POST",
        payload={"username": "Duplicate", "email": email, "password": password},
    )
    require(status == 400, f"Duplicate email must return 400, got {status}")
    status, _ = api_request(
        args.base_url,
        "/auth/login",
        method="POST",
        payload={"email": email, "password": password + "-wrong"},
    )
    require(status == 401, f"Wrong password must return 401, got {status}")
    print("duplicate registration and wrong password: ok")

    status, availability = api_request(args.base_url, "/analysis/availability", token=token)
    require(status == 200 and isinstance(availability, dict), "Availability check failed")
    local_available = bool(availability.get("providers", {}).get("qwen_local", {}).get("available"))
    if args.require_local_ai:
        require(local_available, "Local AI was required but is not ready")
    print(f"availability: ok (local_ai={local_available})")

    tiny_csv = "Должность;Полезность;Практико;Доступность;Отстраненность;Формат;Взаимодействие\nМетодист;9;8;9;нет;очно;9\n".encode()

    invalid_upload_cases = [
        ("unsupported extension", "invalid.txt", tiny_csv, "qwen_local"),
        ("empty file", "empty.csv", b"", "qwen_local"),
        ("long filename", f"{'x' * 197}.csv", tiny_csv, "qwen_local"),
        ("unsupported model", "valid.csv", tiny_csv, "unknown-model"),
    ]
    for label, file_name, content, model_type in invalid_upload_cases:
        invalid_body, invalid_type = multipart_body(
            {"modelType": model_type},
            [("userResponseFiles", file_name, content)],
        )
        status, _ = api_request(
            args.base_url,
            "/analysis/upload",
            method="POST",
            token=token,
            body=invalid_body,
            content_type=invalid_type,
        )
        require(status == 400, f"{label} must return 400, got {status}")
    print("upload validation cases: ok")

    limit_body, limit_type = multipart_body(
        {"modelType": "qwen_local"},
        [("userResponseFiles", f"limit-{index}.csv", tiny_csv) for index in range(21)],
    )
    status, _ = api_request(
        args.base_url,
        "/analysis/upload",
        method="POST",
        token=token,
        body=limit_body,
        content_type=limit_type,
    )
    require(status == 400, f"21-file upload must return 400, got {status}")
    print("upload count limit: ok")

    upload_body, upload_type = multipart_body(
        {"modelType": "qwen_local"},
        [("userResponseFiles", args.sample.name, args.sample.read_bytes())],
    )
    status, accepted = api_request(
        args.base_url,
        "/analysis/upload",
        method="POST",
        token=token,
        body=upload_body,
        content_type=upload_type,
    )
    require(status == 202 and isinstance(accepted, dict) and bool(accepted.get("task_id")), "Upload failed")
    task_id = accepted["task_id"]
    print("upload: accepted")

    deadline = time.monotonic() + args.timeout
    result = None
    while time.monotonic() < deadline:
        _, result = api_request(args.base_url, f"/analysis/status/{task_id}", token=token)
        if isinstance(result, dict) and result.get("status") in {"Completed", "Failed"}:
            break
        time.sleep(1)
    require(isinstance(result, dict) and result.get("status") == "Completed", f"Analysis failed: {result}")
    courses = result.get("result", {}).get("courses_analysis", [])
    require(courses and courses[0].get("students_count", 0) > 0, "Completed report has no responses")
    print(f"analysis: completed ({courses[0]['students_count']} responses)")

    _, history = api_request(args.base_url, "/analysis/history", token=token)
    require(isinstance(history, list), "History response must be a list")
    require(any(item.get("id") == task_id for item in history), "Report missing from history")

    status, _ = api_request(
        args.base_url,
        f"/analysis/rename/{task_id}",
        method="PUT",
        token=token,
        payload={"name": " "},
    )
    require(status == 400, f"Blank report name must return 400, got {status}")
    status, _ = api_request(
        args.base_url,
        f"/analysis/rename/{task_id}",
        method="PUT",
        token=token,
        payload={"name": "x" * 256},
    )
    require(status == 400, f"Long report name must return 400, got {status}")

    new_name = "Production smoke report"
    status, renamed = api_request(
        args.base_url,
        f"/analysis/rename/{task_id}",
        method="PUT",
        token=token,
        payload={"name": new_name},
    )
    require(status == 200 and renamed.get("courseName") == new_name, "Rename failed")

    status, _ = api_request(args.base_url, f"/analysis/archive/{task_id}", method="PUT", token=token, payload={})
    require(status == 200, f"Archive must return 200, got {status}")
    _, archived = api_request(args.base_url, "/analysis/history?onlyArchived=true", token=token)
    require(isinstance(archived, list), "Archived history response must be a list")
    require(any(item.get("id") == task_id for item in archived), "Archive failed")

    status, _ = api_request(args.base_url, f"/analysis/unarchive/{task_id}", method="PUT", token=token, payload={})
    require(status == 200, f"Unarchive must return 200, got {status}")
    _, active = api_request(args.base_url, "/analysis/history", token=token)
    require(isinstance(active, list), "Active history response must be a list")
    require(any(item.get("id") == task_id for item in active), "Unarchive failed")
    print("history, rename, archive and unarchive: ok")

    second_email = f"production-smoke-isolation-{suffix}@example.invalid"
    status, second_auth = api_request(
        args.base_url,
        "/auth/register",
        method="POST",
        payload={"username": "Isolation Smoke", "email": second_email, "password": password},
    )
    require(
        status == 200 and isinstance(second_auth, dict) and bool(second_auth.get("token")),
        "Second user registration failed",
    )
    second_token = second_auth["token"]
    status, _ = api_request(args.base_url, f"/analysis/status/{task_id}", token=second_token)
    require(status == 404, f"Another user must not see the report, got {status}")
    status, _ = api_request(
        args.base_url,
        f"/analysis/rename/{task_id}",
        method="PUT",
        token=second_token,
        payload={"name": "Forbidden rename"},
    )
    require(status == 404, f"Another user must not rename the report, got {status}")
    print("cross-user report isolation: ok")
    print("production smoke: PASS")


if __name__ == "__main__":
    main()
