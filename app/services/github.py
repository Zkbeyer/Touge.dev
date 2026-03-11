from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from app.config import settings

GITHUB_API_BASE = "https://api.github.com"
EVENTS_PER_PAGE = 100


class GitHubRateLimitError(Exception):
    pass


class GitHubClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def fetch_push_events_debug(self, github_username: str, target_date: date, user_tz: str = "UTC") -> list[dict]:
        """Return simplified push events for target_date — for debugging only."""
        tz = ZoneInfo(user_tz)
        events_out = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, 4):
                url = f"{GITHUB_API_BASE}/users/{github_username}/events"
                resp = await client.get(url, headers=self.headers, params={"per_page": EVENTS_PER_PAGE, "page": page})
                if resp.status_code != 200:
                    events_out.append({"error": f"HTTP {resp.status_code}", "page": page})
                    break
                events = resp.json()
                if not events:
                    break
                found_older = False
                for event in events:
                    if event.get("type") != "PushEvent":
                        continue
                    created_at_str = event.get("created_at", "")
                    event_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    event_date = event_dt.astimezone(tz).date()
                    if event_date < target_date:
                        found_older = True
                        break
                    if event_date == target_date:
                        payload = event.get("payload", {})
                        commits = payload.get("commits", [])
                        events_out.append({
                            "repo": event.get("repo", {}).get("name"),
                            "pushed_at": created_at_str,
                            "pushed_at_local": event_dt.astimezone(tz).isoformat(),
                            "size": payload.get("size", 0),
                            "distinct_size": payload.get("distinct_size", 0),
                            "counted_as": payload.get("size") or payload.get("distinct_size") or 1,
                            "commits_in_payload": len(commits),
                            "commits": [{"sha": c["sha"][:7], "message": c["message"][:60], "author": c.get("author", {}).get("name")} for c in commits],
                        })
                if found_older:
                    break
        return events_out

    async def fetch_commit_count(self, github_username: str, target_date: date, user_tz: str = "UTC") -> tuple[int, int]:
        """Count pushes and distinct repos pushed to by github_username on target_date (in user's timezone).
        Returns (commit_count, repo_count)."""
        tz = ZoneInfo(user_tz)
        # We need to look at events — fetch up to 3 pages of PushEvents
        commit_count = 0
        repos_seen: set[str] = set()
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, 4):  # max 3 pages = 300 events
                url = f"{GITHUB_API_BASE}/users/{github_username}/events"
                resp = await client.get(
                    url,
                    headers=self.headers,
                    params={"per_page": EVENTS_PER_PAGE, "page": page},
                )
                remaining = int(resp.headers.get("X-RateLimit-Remaining", 100))
                if remaining < 10:
                    raise GitHubRateLimitError(f"Rate limit low: {remaining} remaining")

                if resp.status_code == 403:
                    raise GitHubRateLimitError("GitHub rate limit exceeded")
                resp.raise_for_status()

                events = resp.json()
                if not events:
                    break

                found_older = False
                for event in events:
                    if event.get("type") != "PushEvent":
                        continue

                    # Parse event timestamp and convert to user's TZ
                    created_at_str = event.get("created_at", "")
                    if not created_at_str:
                        continue
                    event_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    event_date = event_dt.astimezone(tz).date()

                    if event_date < target_date:
                        found_older = True
                        break

                    if event_date == target_date:
                        # Any push on the target date counts as 1 qualifying push.
                        commit_count += 1
                        repo_name = event.get("repo", {}).get("name", "")
                        if repo_name:
                            repos_seen.add(repo_name)

                if found_older:
                    break

                # If all events on this page are newer than target_date, fetch next page
                # (GitHub returns newest first)

        return commit_count, len(repos_seen)

    async def get_user_info(self, access_token: str) -> dict:
        """Fetch authenticated user info from GitHub."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def exchange_code(code: str) -> dict:
        """Exchange OAuth code for access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
