#!/usr/bin/env python3
"""
OpenAPI Client - 完整版
用于对接开放 API 平台
"""

import json
import base64
import hashlib
import hmac
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

HMAC_SHA256 = "HmacSHA256"
ENCODING = "utf-8"
CA_HEADER_TO_SIGN_PREFIX_SYSTEM = "X-Ca-"
SPE1 = ","
SPE2 = ":"
SPE3 = "&"

X_CA_SIGNATURE = "X-Ca-Signature"
X_CA_SIGNATURE_HEADERS = "X-Ca-Signature-Headers"
X_CA_TIMESTAMP = "X-Ca-Timestamp"
X_CA_NONCE = "X-Ca-Nonce"
X_CA_KEY = "X-Ca-Key"
X_SERVICE_ID = "X-Service-Id"
X_SERVICE_METHOD = "X-Service-Method"
X_CONTENT_MD5 = "X-Content-MD5"
X_CA_REQUESTID = "X-Ca-RequestId"
X_CA_ERROR_MESSAGE = "X-Ca-Error-Message"

SIGN_HEADER_LIST = ["X-Ca-Key", "X-Ca-Nonce", "X-Ca-Timestamp", "X-Content-MD5", "X-Service-Id", "X-Service-Method"]


@dataclass
class Response:
    status_code: int = 0
    content_type: str = ""
    request_id: str = ""
    ca_error_msg: str = ""
    error_message: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    json_response: Optional[Dict] = None

    def is_success(self) -> bool:
        if self.status_code == 200 and self.json_response:
            code = self.json_response.get("code")
            return code == 200 or code == "200"
        return False

    def get_error_message(self) -> Optional[str]:
        if self.json_response:
            msg = self.json_response.get("msg")
            if msg and self.json_response.get("code") not in [200, "200"]:
                return msg
        return None


@dataclass
class Request:
    api_url: str = ""
    app_key: str = ""
    app_secret: str = ""
    encoding_aes_key: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    bodys: List[Any] = field(default_factory=list)
    string_body: str = ""
    service_id: str = ""
    method: str = ""

    def add_header(self, name: str, value: str):
        self.headers[name] = value


class AESUtils:
    KEY_ALGORITHM = "AES"
    DEFAULT_CIPHER_ALGORITHM = "AES/ECB/PKCS5Padding"

    @staticmethod
    def encrypt(data: str, key: str) -> str:
        key_bytes = key.encode(ENCODING)
        data_bytes = data.encode(ENCODING)
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        padded_data = pad(data_bytes, AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted).decode(ENCODING)

    @staticmethod
    def decrypt(data: str, key: str) -> str:
        key_bytes = key.encode(ENCODING)
        encrypted_bytes = base64.b64decode(data.encode(ENCODING))
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        decrypted = cipher.decrypt(encrypted_bytes)
        unpadded = unpad(decrypted, AES.block_size)
        return unpadded.decode(ENCODING)


class JSONUtils:
    @staticmethod
    def to_string(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False, default=str)

    @staticmethod
    def parse(value: str, cls: type = None) -> Any:
        if not value:
            return None
        try:
            result = json.loads(value)
            if cls and isinstance(result, dict):
                return cls(**result)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")


class MessageDigestUtil:
    @staticmethod
    def base64_and_md5(data: str) -> str:
        if data is None:
            raise ValueError("data can not be null")
        return MessageDigestUtil.base64_and_md5_bytes(data.encode(ENCODING))

    @staticmethod
    def base64_and_md5_bytes(data: bytes) -> str:
        if data is None:
            raise ValueError("data can not be null")
        md5_digest = hashlib.md5(data).digest()
        return base64.b64encode(md5_digest).decode(ENCODING)

    @staticmethod
    def iso88591_to_utf8(s: str) -> str:
        if s is None:
            return s
        return s.encode('ISO-8859-1', errors='ignore').decode('UTF-8', errors='ignore')


class SignUtil:
    @staticmethod
    def sign(secret: str, headers: Dict[str, str]) -> str:
        try:
            sign_data = SignUtil.build_headers(headers, SIGN_HEADER_LIST)
            key_bytes = secret.encode(ENCODING)
            message = sign_data.encode(ENCODING)
            signature = hmac.new(key_bytes, message, hashlib.sha256).digest()
            return base64.b64encode(signature).decode(ENCODING)
        except Exception as e:
            raise RuntimeError(f"Sign error: {e}")

    @staticmethod
    def build_headers(headers: Dict[str, str], sign_header_list: List[str]) -> str:
        sb_list = []
        if headers:
            sort_map = dict(sorted(headers.items()))
            sign_headers = []
            for header_name, header_value in sort_map.items():
                if SignUtil.is_header_to_sign(header_name, sign_header_list):
                    sb = f"{header_name.lower()}{SPE2}{header_value or ''}"
                    sb_list.append(sb)
                    sign_headers.append(header_name.lower())
            headers[X_CA_SIGNATURE_HEADERS] = SPE1.join(sign_headers)
        return SPE3.join(sb_list)

    @staticmethod
    def is_header_to_sign(header_name: str, sign_header_list: List[str]) -> bool:
        if not header_name:
            return False
        if header_name.startswith(CA_HEADER_TO_SIGN_PREFIX_SYSTEM):
            return True
        if sign_header_list:
            for sign_header in sign_header_list:
                if header_name.lower() == sign_header.lower():
                    return True
        return False


class OpenApiUtils:
    @staticmethod
    def post(request: Request) -> Response:
        try:
            headers = request.headers.copy()
            body = request.string_body if request.string_body else JSONUtils.to_string(request.bodys)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            resp = requests.post(
                request.api_url,
                headers=headers,
                data=body if body != "[]" else None,
                verify=False,
                timeout=30
            )
            return OpenApiUtils._convert_response(resp)
        except Exception as e:
            response = Response()
            response.status_code = 500
            response.error_message = str(e)
            return response

    @staticmethod
    def _convert_response(resp: requests.Response) -> Response:
        response = Response()
        response.status_code = resp.status_code
        response.headers = dict(resp.headers)
        response.content_type = resp.headers.get("Content-Type", "")
        response.request_id = resp.headers.get("X-Ca-Request-Id", "")
        response.ca_error_msg = resp.headers.get("X-Ca-Error-Message", "")
        response.body = resp.text
        try:
            response.json_response = resp.json()
        except json.JSONDecodeError:
            response.json_response = None
        return response


class Client:
    def __init__(self, api_url: str, app_key: str, app_secret: str, encoding_aes_key: str = ""):
        self.api_url = api_url
        self.app_key = app_key
        self.app_secret = app_secret
        self.encoding_aes_key = encoding_aes_key

    def execute(self, request: Request) -> Response:
        request.api_url = self.api_url
        request.app_key = self.app_key
        request.app_secret = self.app_secret
        request.encoding_aes_key = self.encoding_aes_key
        request.add_header(X_CA_KEY, request.app_key)
        request.add_header(X_CA_NONCE, str(uuid.uuid4()))
        request.add_header(X_CA_TIMESTAMP, str(int(time.time() * 1000)))
        json_str = JSONUtils.to_string(request.bodys)
        if self.encoding_aes_key:
            encrypt_str = AESUtils.encrypt(json_str, self.encoding_aes_key)
        else:
            encrypt_str = json_str
        content_md5 = MessageDigestUtil.base64_and_md5(encrypt_str)
        request.add_header(X_CONTENT_MD5, content_md5)
        signature = SignUtil.sign(request.app_secret, request.headers)
        request.add_header(X_CA_SIGNATURE, signature)
        request.string_body = encrypt_str
        return OpenApiUtils.post(request)


def create_client(api_url: str, app_key: str, app_secret: str, encoding_aes_key: str = "") -> Client:
    return Client(api_url, app_key, app_secret, encoding_aes_key)
