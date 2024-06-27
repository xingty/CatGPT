import json
import aiohttp
import os
import markdown

from bs4 import BeautifulSoup

from ..utils.text import messages_to_segments
from ..storage.types import Topic


TELEGRAPH_API_URL = "https://api.telegra.ph/createAccount"


class TelegraphAPI:
    def __init__(
        self,
        access_token=None,
        short_name="mq",
        author_name="mq",
        author_url=None,
        proxy_url=None,
    ):
        self.access_token = access_token
        self.base_url = "https://api.telegra.ph"

        self.short_name = short_name
        self.author_name = author_name
        self.author_url = author_url
        self.proxy = proxy_url

    @staticmethod
    async def create(
        access_token=None,
        short_name="meiqiu",
        author_name="meiqiu",
        author_url=None,
        proxy_url=None,
    ):
        TelegraphAPI.load_token()

        api = TelegraphAPI(
            access_token=access_token,
            short_name=short_name,
            author_name=author_name,
            author_url=author_url,
            proxy_url=proxy_url,
        )

        if not api.access_token:
            token_info = api.load_token()
            if token_info is not None:
                api.access_token = token_info["access_token"]
                api.short_name = token_info["short_name"]
                api.author_name = token_info["author_name"]
            else:
                access_token = await api._create_ph_account(
                    short_name, author_name, author_url
                )
                api.access_token = access_token
                api.save_token(
                    {
                        "short_name": api.short_name,
                        "author_name": api.author_name,
                        "access_token": api.access_token,
                    }
                )

        return api

    @staticmethod
    def save_token(token):
        with open("telegraph.json", "w") as f:
            json.dump(token, f, indent=4)

    @staticmethod
    def load_token():
        if os.path.exists("telegraph.json"):
            with open("telegraph.json", "r") as f:
                return json.load(f)

        return None

    async def _create_ph_account(self, short_name, author_name, author_url):
        # If no existing valid token in TOKEN_FILE, create a new account
        data = {
            "short_name": short_name,
            "author_name": author_name,
            "author_url": author_url,
        }

        # Make API request
        account = await self.post(TELEGRAPH_API_URL, data=data)
        if "result" in account and "access_token" in account["result"]:
            return account["result"]["access_token"]

        raise Exception("Failed to create telegra.ph account")

    async def create_page(
        self, title, content, author_name=None, author_url=None, return_content=False
    ):
        url = f"{self.base_url}/createPage"
        data = {
            "access_token": self.access_token,
            "title": title,
            "content": json.dumps(content, ensure_ascii=False),
            "return_content": return_content,
            "author_name": author_name if author_name else self.author_name,
            "author_url": author_url if author_url else self.author_url,
        }

        response = await self.post(url, data=data)
        if "result" not in response:
            raise Exception("Failed to create page, " + str(response))

        return response["result"]

    async def get_account_info(self):
        url = f'{self.base_url}/getAccountInfo?access_token={self.access_token}&fields=["short_name","author_name","author_url","auth_url"]'
        try:
            response = await self.get(url)
            return response.get("result", None)
        except Exception as e:
            print(f"Fail getting telegra.ph token info {e}")

    async def edit_page(
        self,
        path,
        title,
        content,
        author_name=None,
        author_url=None,
        return_content=False,
    ):
        url = f"{self.base_url}/editPage"
        data = {
            "access_token": self.access_token,
            "path": path,
            "title": title,
            "content": json.dumps(content, ensure_ascii=False),
            "return_content": return_content,
            "author_name": author_name if author_name else self.author_name,
            "author_url": author_url if author_url else self.author_url,
        }

        response = await self.post(url, data=data)
        if "result" not in response or "url" not in response["result"]:
            raise Exception("Failed to edit page, " + str(response))

        return response["result"]["url"]

    async def get_page(self, path):
        url = f"{self.base_url}/getPage/{path}?return_content=true"
        response = await self.get(url)
        return response.get("result")

    async def create_page_md(
        self,
        title,
        markdown_text,
        author_name=None,
        author_url=None,
        return_content=False,
    ):
        content = self._md_to_dom(markdown_text)
        return await self.create_page(
            title, content, author_name, author_url, return_content
        )

    async def edit_page_md(
        self,
        path,
        title,
        markdown_text,
        author_name=None,
        author_url=None,
        return_content=False,
    ):
        content = self._md_to_dom(markdown_text)
        return await self.edit_page(
            path, title, content, author_name, author_url, return_content
        )

    async def authorize_browser(self):
        url = f'{self.base_url}/getAccountInfo?access_token={self.access_token}&fields=["auth_url"]'
        response = await self.get(url)
        return response["result"]["auth_url"]

    def _md_to_dom(self, markdown_text):
        html = markdown.markdown(
            markdown_text,
            extensions=["markdown.extensions.extra", "markdown.extensions.sane_lists"],
        )

        soup = BeautifulSoup(html, "html.parser")

        def parse_element(element):
            tag_dict = {"tag": element.name}
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                if element.name == "h1":
                    tag_dict["tag"] = "h3"
                elif element.name == "h2":
                    tag_dict["tag"] = "h4"
                else:
                    tag_dict["tag"] = "p"
                    tag_dict["children"] = [
                        {"tag": "strong", "children": element.contents}
                    ]

                if element.attrs:
                    tag_dict["attributes"] = element.attrs
                if element.contents:
                    children = []
                    for child in element.contents:
                        if isinstance(child, str):
                            children.append(child.strip())
                        else:
                            children.append(parse_element(child))
                    tag_dict["children"] = children
            else:
                if element.attrs:
                    tag_dict["attributes"] = element.attrs
                if element.contents:
                    children = []
                    for child in element.contents:
                        if isinstance(child, str):
                            children.append(child.strip())
                        else:
                            children.append(parse_element(child))
                    if children:
                        tag_dict["children"] = children
            return tag_dict

        new_dom = []
        for element in soup.contents:
            if isinstance(element, str) and not element.strip():
                continue
            elif isinstance(element, str):
                new_dom.append({"tag": "text", "content": element.strip()})
            else:
                new_dom.append(parse_element(element))

        return new_dom

    async def get(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=self.proxy) as response:
                if not response.ok:
                    raise Exception(f"Failed to get: {await response.text()}")

                return await response.json()

    async def post(self, url, data):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, proxy=self.proxy) as response:
                if not response.ok:
                    raise Exception(f"Failed to create issue: {await response.text()}")

                return await response.json()


class TelegraphProvider:
    def __init__(self, api: TelegraphAPI):
        self.api = api

    async def share(self, convo: Topic):
        md_content = messages_to_segments(convo.messages, 65535)[0]
        result = await self.api.create_page_md(
            title=convo.title,
            markdown_text=md_content,
        )

        if "url" not in result:
            raise Exception("Failed to create page")

        return result.get("url")

    async def share_text(self, article_id: str, title: str, content: str):
        result = await self.api.create_page_md(
            title=title,
            markdown_text=content,
        )
        if "url" not in result:
            raise Exception("Failed to create page")

        return result.get("url")

    async def update_text(self, path, title, content):
        return await self.api.edit_page_md(
            path=path,
            title=title,
            markdown_text=content,
        )

    async def create_page(self, title, content):
        return await self.api.create_page_md(title=title, markdown_text=content)

    def get_token(self):
        return self.api.access_token


async def create(params: dict, config):
    author = params.get("author", "meiqiu")
    short_name = params.get("short_name", author)
    proxy_url = config.proxy_url
    api = await TelegraphAPI.create(
        access_token=params.get("token"),
        short_name=short_name,
        author_name=author,
        proxy_url=proxy_url,
    )

    return TelegraphProvider(api)
