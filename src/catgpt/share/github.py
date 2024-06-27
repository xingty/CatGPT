import aiohttp

from ..storage.types import Topic
from ..utils.text import messages_to_segments

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    # "Authorization": "Bearer " + token,
    "X-GitHub-Api-Version": "2022-11-28",
}


class GithubProvider:
    def __init__(self, name: str, owner: str, repo: str, token: str, proxy=None):
        assert owner, "owner is required"
        assert repo, "repo is required"
        assert token, "token is required"

        self.name = name
        self.owner = owner
        self.repo = repo
        self.token = token
        self.proxy = proxy

    async def get_github_issue(self, label):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues"
        headers = HEADERS.copy()
        headers["Authorization"] = f"Bearer {self.token}"

        params = {"labels": label, "state": "open"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, params=params, proxy=self.proxy
            ) as response:
                if not response.ok:
                    raise Exception(f"Failed to search issues: {response.text}")

                issues = await response.json()
                return issues[0] if issues else None

    async def create_github_issue(self, title, body, label):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues"
        headers = HEADERS.copy()
        headers["Authorization"] = f"Bearer {self.token}"
        data = {"title": title, "body": body, "labels": [label]}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=data, proxy=self.proxy
            ) as response:
                if not response.ok:
                    raise Exception(f"Failed to create issue: {await response.text()}")

                return await response.json()

    async def update_github_issue(self, issue_number, title, body):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{issue_number}"
        headers = HEADERS.copy()
        headers["Authorization"] = f"Bearer {self.token}"
        data = {"title": title, "body": body}

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                url, headers=headers, json=data, proxy=self.proxy
            ) as response:
                if not response.ok:
                    raise Exception(f"Failed to update issue: {response.text}")

                return await response.json()

    async def create_or_update_issue(self, title, body, label):
        issue = await self.get_github_issue(label)
        if issue:
            issue = await self.update_github_issue(issue["number"], title, body)
        else:
            issue = await self.create_github_issue(title, body, label)

        return issue.get("html_url")

    async def share(self, convo: Topic):
        body = messages_to_segments(convo.messages, 65535)[0]
        return await self.create_or_update_issue(
            title=convo.title,
            body=body,
            label=convo.label,
        )

    async def share_text(self, article_id, title, content):
        return await self.create_or_update_issue(
            title=title,
            body=content,
            label=article_id,
        )

    def get_token(self):
        return self.token


async def create(params: dict, config):
    return GithubProvider(
        name=params.get("name"),
        owner=params.get("owner"),
        repo=params.get("repo"),
        token=params.get("token"),
        proxy=params.get("proxy"),
    )
