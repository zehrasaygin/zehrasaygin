import os
import json
import html
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen

USERNAME = "zehrasaygin"
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!, $from: DateTime!) {
  user(login: $login) {
    followers {
      totalCount
    }
    following {
      totalCount
    }
    repositories(
      first: 100
      privacy: PUBLIC
      ownerAffiliations: OWNER
      orderBy: { field: UPDATED_AT, direction: DESC }
    ) {
      totalCount
      nodes {
        languages(first: 10, orderBy: { field: SIZE, direction: DESC }) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
      }
    }
    contributionsCollection(from: $from) {
      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""


def get_github_data():
    since = (
        datetime.now(timezone.utc) - timedelta(days=365)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")

    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "login": USERNAME,
            "from": since
        }
    }).encode("utf-8")

    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-stats"
        }
    )

    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if result.get("errors"):
        raise RuntimeError(result["errors"])

    user = result["data"]["user"]

    if user is None:
        raise RuntimeError("GitHub user not found.")

    return user


def create_stats_svg(user):
    metrics = [
        ("Public Repositories",
         user["repositories"]["totalCount"]),

        ("Followers",
         user["followers"]["totalCount"]),

        ("Following",
         user["following"]["totalCount"]),

        ("Contributions · 12 mo",
         user["contributionsCollection"]
         ["contributionCalendar"]["totalContributions"])
    ]

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="520" height="175" viewBox="0 0 520 175">',

        '<rect x="1" y="1" width="518" height="173" '
        'rx="9" fill="#fff7fb" stroke="#e7cde2"/>',

        '<text x="26" y="37" font-family="Arial" '
        'font-size="17" font-weight="bold" fill="#9b6ba5">'
        'GitHub Overview</text>'
    ]

    column_width = 130

    for i, (label, value) in enumerate(metrics):
        center = column_width * i + column_width // 2

        if i > 0:
            parts.append(
                f'<line x1="{column_width*i}" y1="60" '
                f'x2="{column_width*i}" y2="145" '
                'stroke="#ead6e6"/>'
            )

        parts.append(
            f'<text x="{center}" y="91" text-anchor="middle" '
            'font-family="Arial" font-size="24" '
            'font-weight="bold" fill="#28212b">'
            f'{value:,}</text>'
        )

        parts.append(
            f'<text x="{center}" y="117" text-anchor="middle" '
            'font-family="Arial" font-size="10" '
            'fill="#9b83a2">'
            f'{html.escape(label)}</text>'
        )

    parts.append("</svg>")

    with open("assets/github-stats.svg", "w", encoding="utf-8") as file:
        file.write("\n".join(parts))


def create_languages_svg(user):
    totals = {}

    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            language = edge["node"]["name"]

            if language not in totals:
                totals[language] = {
                    "size": 0,
                    "color": edge["node"].get("color")
                }

            totals[language]["size"] += edge["size"]

    languages = sorted(
        totals.items(),
        key=lambda item: item[1]["size"],
        reverse=True
    )[:6]

    total_size = sum(item["size"]["size"] for item in languages)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="520" height="190" viewBox="0 0 520 190">',

        '<rect x="1" y="1" width="518" height="188" '
        'rx="9" fill="#fff7fb" stroke="#e7cde2"/>',

        '<text x="26" y="37" font-family="Arial" '
        'font-size="17" font-weight="bold" fill="#9b6ba5">'
        'Most Used Languages</text>'
    ]

    if total_size == 0:
        parts.append(
            '<text x="260" y="110" text-anchor="middle" '
            'font-family="Arial" font-size="13" fill="#6f5875">'
            'No public language data available</text>'
        )
    else:
        x = 27
        bar_width = 466

        colors = [
            "#c88fba", "#9b6ba5", "#e5aacd",
            "#b69acb", "#d88fbd", "#ad8db7"
        ]

        for i, (name, info) in enumerate(languages):
            width = bar_width * info["size"] / total_size
            color = info["color"] or colors[i % len(colors)]

            parts.append(
                f'<rect x="{x:.2f}" y="59" '
                f'width="{width:.2f}" height="12" '
                f'fill="{html.escape(color, quote=True)}"/>'
            )

            x += width

        for i, (name, info) in enumerate(languages):
            column = i % 2
            row = i // 2

            x = 30 + column * 235
            y = 105 + row * 27

            color = info["color"] or colors[i % len(colors)]
            percentage = info["size"] / total_size * 100

            parts.append(
                f'<circle cx="{x+5}" cy="{y-4}" r="5" '
                f'fill="{html.escape(color, quote=True)}"/>'
            )

            parts.append(
                f'<text x="{x+18}" y="{y}" '
                'font-family="Arial" font-size="12" '
                'font-weight="bold" fill="#6f5875">'
                f'{html.escape(name)}</text>'
            )

            parts.append(
                f'<text x="{x+215}" y="{y}" '
                'text-anchor="end" font-family="Arial" '
                'font-size="11" fill="#9b83a2">'
                f'{percentage:.1f}%</text>'
            )

    parts.append("</svg>")

    with open("assets/top-languages.svg", "w", encoding="utf-8") as file:
        file.write("\n".join(parts))


def main():
    os.makedirs("assets", exist_ok=True)

    user = get_github_data()

    create_stats_svg(user)
    create_languages_svg(user)

    print("GitHub profile cards updated successfully.")


if __name__ == "__main__":
    main()