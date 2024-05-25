from context import config
import aiohttp

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    # "Authorization": "Bearer " + token,
    "X-GitHub-Api-Version": "2022-11-28",
}

PROXIES = config.proxy_url


async def get_github_issue(owner, repo, token, label):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {token}'

    params = {'labels': label, 'state': 'open'}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params, proxy=PROXIES) as response:
            if not response.ok:
                raise Exception(f"Failed to search issues: {response.text}")

            issues = await response.json()
            return issues[0] if issues else None


async def create_github_issue(owner, repo, token, title, body, label):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {token}'
    data = {
        'title': title,
        'body': body,
        'labels': [label]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data, proxy=PROXIES) as response:
            if not response.ok:
                raise Exception(f"Failed to create issue: {response.text}")

            return await response.json()


async def update_github_issue(owner, repo, token, issue_number, title, body):
    """更新现有的GitHub Issue"""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {token}'
    data = {
        'title': title,
        'body': body
    }

    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=data, proxy=PROXIES) as response:
            if not response.ok:
                raise Exception(f"Failed to update issue: {response.text}")

            return await response.json()


async def create_or_update_issue(owner, repo, token, title, body, label):
    issue = await get_github_issue(owner, repo, token, label)
    if issue:
        issue = await update_github_issue(owner, repo, token, issue['number'], title, body)
    else:
        issue = await create_github_issue(owner, repo, token, title, body, label)

    return issue.get('html_url')
