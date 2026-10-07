import io
import requests
from bs4 import BeautifulSoup


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
        return code_tag.get_text(strip=True) if code_tag else ""

    @staticmethod
    def extract_hyperlink(html_fragment: str) -> str:
        doc = BeautifulSoup(html_fragment, "html.parser")
        anchor_tag = doc.find("a")
        return anchor_tag.get("href", "") if anchor_tag else ""


class NetworkAutomaton:
    def __init__(self, target_host: str, auth_token: str):
        self._host = target_host
        self._token = auth_token
        self._hop_counter = 0

    def launch(self):
        current_response = requests.get(self._host, cookies={"user": self._token})
        page_markup = current_response.content.decode("utf-8", errors="ignore")
        while True:
            self._hop_counter += 1

            query_parameters = (
                PageAnalyzer.parse_table_elements(
                    page_markup[
                        page_markup.find(
                            "При переходе выставьте следующие параметры запроса, указанные в таблице:"
                        ) :
                    ]
                )
                if "При переходе выставьте следующие параметры запроса, указанные в таблице:"
                in page_markup
                else {}
            )
            http_headers = (
                PageAnalyzer.parse_table_elements(
                    page_markup[
                        page_markup.find("Запрос должен иметь следующие заголовки:") :
                    ]
                )
                if "Запрос должен иметь следующие заголовки:" in page_markup
                else {}
            )
            form_fields = (
                PageAnalyzer.parse_table_elements(
                    page_markup[
                        page_markup.find(
                            "Запрос должен иметь следующие данные формы:"
                        ) :
                    ]
                )
                if "Запрос должен иметь следующие данные формы:" in page_markup
                else {}
            )
            step_cookies = (
                PageAnalyzer.parse_table_elements(
                    page_markup[
                        page_markup.find("В запросе должны быть выставлены cookie:") :
                    ]
                )
                if "В запросе должны быть выставлены cookie:" in page_markup
                else {}
            )
            step_cookies["user"] = self._token

            if "Отправьте GET-запрос" in page_markup:
                endpoint_route = PageAnalyzer.extract_single_code_value(
                    page_markup[page_markup.find("Отправьте GET-запрос") :]
                )
                current_response = requests.get(
                    self._host + endpoint_route,
                    cookies=step_cookies,
                    params=query_parameters,
                    headers=http_headers,
                )
            elif "Отправьте POST-запрос" in page_markup:
                endpoint_route = PageAnalyzer.extract_single_code_value(
                    page_markup[page_markup.find("Отправьте POST-запрос") :]
                )
                current_response = requests.post(
                    self._host + endpoint_route,
                    cookies=step_cookies,
                    params=query_parameters,
                    headers=http_headers,
                    data=form_fields,
                )
            elif "Загрузите файлы по адресу" in page_markup:
                endpoint_route = PageAnalyzer.extract_single_code_value(
                    page_markup[page_markup.find("Загрузите файлы по адресу") :]
                )
                files_dict = PageAnalyzer.parse_table_elements(page_markup)
                payload_files = [
                    ("file", (f_name, io.BytesIO(f_text.encode("utf-8")), "text/plain"))
                    for f_name, f_text in files_dict.items()
                ]
                current_response = requests.post(
                    self._host + endpoint_route,
                    cookies=step_cookies,
                    files=payload_files,
                )
            elif "Перейдите по" in page_markup:
                endpoint_route = PageAnalyzer.extract_hyperlink(
                    page_markup[page_markup.find("Перейдите по") :]
                )
                current_response = requests.get(
                    self._host + endpoint_route,
                    cookies=step_cookies,
                    params=query_parameters,
                    headers=http_headers,
                )
            else:
                print(page_markup)
                break

            page_markup = current_response.content.decode("utf-8", errors="ignore")

        print(f"Шагов пройдено: {self._hop_counter}")


automaton = NetworkAutomaton(
    "http://hw1.alexbers.com", "109ad7ae2416c4c4c49d5410ec547263"
)
automaton.launch()
