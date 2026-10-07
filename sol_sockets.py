import socket
from bs4 import BeautifulSoup
from urllib.parse import urlencode


class HttpQuestRunner:
    def __init__(self, host_address):
        self._host = host_address

    def _receive_all(self, sock_instance):
        buffer = bytearray()
        while True:
            chunk = sock_instance.recv(4096)
            if not chunk:
                break
            buffer.extend(chunk)

        full_response = buffer.decode("utf-8", errors="ignore")

        separator_idx = full_response.find("\r\n\r\n")
        if separator_idx != -1:
            return full_response[separator_idx + 4 :]
        return full_response

    def _execute_tcp_request(
        self,
        method,
        route,
        cookies=None,
        query_params=None,
        headers=None,
        body_bytes=None,
        content_type=None,
    ):
        if cookies is None:
            cookies = {}
        if query_params is None:
            query_params = {}
        if headers is None:
            headers = {}
        if body_bytes is None:
            body_bytes = b""

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self._host, 80))

        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        custom_headers = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
        query_suffix = "?" + urlencode(query_params) if query_params else ""

        lines = [
            f"{method} {route + query_suffix} HTTP/1.1",
            f"Host: {self._host}",
            f"Cookie: {cookie_header}",
        ]

        if content_type:
            lines.append(f"Content-Type: {content_type}")

        if custom_headers:
            lines.append(custom_headers.rstrip("\r\n"))

        if body_bytes:
            lines.append(f"Content-Length: {len(body_bytes)}")

        lines.extend(["Connection: close", "", ""])

        head_payload = "\r\n".join(lines).encode("utf-8")
        sock.sendall(head_payload + body_bytes)

        response_text = self._receive_all(sock)
        sock.close()
        return response_text

    def get(self, route="/", cookies=None, params=None, headers=None):
        return self._execute_tcp_request(
            "GET", route, cookies=cookies, query_params=params, headers=headers
        )

    def post(self, route="/", cookies=None, params=None, headers=None, data=None):
        if data is None:
            data = {}
        encoded_data = urlencode(data).encode("utf-8")
        return self._execute_tcp_request(
            "POST",
            route,
            cookies=cookies,
            query_params=params,
            headers=headers,
            body_bytes=encoded_data,
            content_type="application/x-www-form-urlencoded",
        )

    def post_multipart(self, route="/", cookies=None, files=None):
        if files is None:
            files = {}

        boundary_id = "BoundaryDataNode777"
        chunks = []
        for name, text_content in files.items():
            chunks.append(f"--{boundary_id}\r\n".encode("utf-8"))
            chunks.append(
                f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode(
                    "utf-8"
                )
            )
            chunks.append(b"Content-Type: text/plain\r\n\r\n")
            chunks.append(text_content.encode("utf-8") + b"\r\n")

        chunks.append(f"--{boundary_id}--\r\n".encode("utf-8"))
        payload_body = b"".join(chunks)

        return self._execute_tcp_request(
            "POST",
            route,
            cookies=cookies,
            body_bytes=payload_body,
            content_type=f"multipart/form-data; boundary={boundary_id}",
        )


class PageAnalyzer:
    @staticmethod
    def parse_table_elements(html_fragment: str) -> dict:
        doc = BeautifulSoup(html_fragment, "html.parser")
        table = doc.find("table")
        if not table:
            return {}

        result = {}
        for row in table.find_all("tr"):
            codes = row.find_all("code")
            if len(codes) >= 2:
                key = codes[0].get_text(strip=True)
                val = codes[1].get_text(strip=True)
                result[key] = val
        return result

    @staticmethod
    def extract_single_code_value(html_fragment: str) -> str:
        doc = BeautifulSoup(html_fragment, "html.parser")
        code_tag = doc.find("code")
        return code_tag.text.strip() if code_tag else ""

    @staticmethod
    def extract_hyperlink(html_fragment: str) -> str:
        doc = BeautifulSoup(html_fragment, "html.parser")
        anchor_tag = doc.find("a")
        return anchor_tag.get("href") if anchor_tag and anchor_tag.has_attr("href") else ""


class SocketNetworkAutomation:
    def __init__(self, target_host: str, auth_token: str):
        self._client = HttpQuestRunner(target_host)
        self._token = auth_token
        self._hop_counter = 0

    def launch(self):
        current_response = self._client.get(cookies={"user": self._token})
        while True:
            self._hop_counter += 1

            query_parameters = (
                PageAnalyzer.parse_table_elements(
                    current_response[
                        current_response.find(
                            "При переходе выставьте следующие параметры запроса, указанные в таблице:"
                        ) :
                    ]
                )
                if "При переходе выставьте следующие параметры запроса, указанные в таблице:"
                in current_response
                else {}
            )
            http_headers = (
                PageAnalyzer.parse_table_elements(
                    current_response[
                        current_response.find(
                            "Запрос должен иметь следующие заголовки:"
                        ) :
                    ]
                )
                if "Запрос должен иметь следующие заголовки:" in current_response
                else {}
            )
            form_fields = (
                PageAnalyzer.parse_table_elements(
                    current_response[
                        current_response.find(
                            "Запрос должен иметь следующие данные формы:"
                        ) :
                    ]
                )
                if "Запрос должен иметь следующие данные формы:" in current_response
                else {}
            )
            step_cookies = (
                PageAnalyzer.parse_table_elements(
                    current_response[
                        current_response.find(
                            "В запросе должны быть выставлены cookie:"
                        ) :
                    ]
                )
                if "В запросе должны быть выставлены cookie:" in current_response
                else {}
            )

            step_cookies["user"] = self._token

            if "Отправьте GET-запрос" in current_response:
                dest = PageAnalyzer.extract_single_code_value(
                    current_response[current_response.find("Отправьте GET-запрос") :]
                )
                current_response = self._client.get(
                    route=dest,
                    cookies=step_cookies,
                    params=query_parameters,
                    headers=http_headers,
                )
            elif "Отправьте POST-запрос" in current_response:
                dest = PageAnalyzer.extract_single_code_value(
                    current_response[current_response.find("Отправьте POST-запрос") :]
                )
                current_response = self._client.post(
                    route=dest,
                    cookies=step_cookies,
                    params=query_parameters,
                    headers=http_headers,
                    data=form_fields,
                )
            elif "Загрузите файлы по адресу" in current_response:
                dest = PageAnalyzer.extract_single_code_value(
                    current_response[
                        current_response.find("Загрузите файлы по адресу") :
                    ]
                )
                file_map = PageAnalyzer.parse_table_elements(current_response)
                current_response = self._client.post_multipart(
                    route=dest,
                    cookies=step_cookies,
                    files=file_map,
                )
            elif "Перейдите по" in current_response:
                dest = PageAnalyzer.extract_hyperlink(
                    current_response[current_response.find("Перейдите по") :]
                )
                current_response = self._client.get(
                    route=dest,
                    cookies=step_cookies,
                    params=query_parameters,
                    headers=http_headers,
                )
            else:
                print(current_response)
                print(f"Шагов пройдено: {self._hop_counter}")
                break


automaton_socket = SocketNetworkAutomation(
    "hw1.alexbers.com", "109ad7ae2416c4c4c49d5410ec547263"
)
automaton_socket.launch()
