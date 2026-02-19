#!/usr/bin/env python3
"""
Auto-update GitHub profile README with categorized repository list.

This script fetches all repositories from a GitHub user, classifies them
into categories using a hybrid approach (topics > language > keywords),
and updates the README.md file with a formatted list.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

import requests

# Configuration
GITHUB_USERNAME = "juanjoseexpositogonzalez"
README_PATH = Path(__file__).parent.parent / "README.md"
GITHUB_API = "https://api.github.com"

# Markers for auto-generated content
START_MARKER = "<!-- REPOS-START -->"
END_MARKER = "<!-- REPOS-END -->"

# Category definitions with classification rules
CATEGORIES = {
    "AI/RAG": {
        "topics": ["ai", "rag", "llm", "agent", "ml", "machine-learning", "nlp", "chatbot"],
        "keywords": ["ai", "agent", "rag", "chatbot", "llm", "ml", "gpt", "openai", "langchain"],
        "languages": [],  # Python is checked separately with keywords
    },
    "Blockchain/DeFi": {
        "topics": ["blockchain", "defi", "web3", "solidity", "ethereum", "smart-contracts", "nft"],
        "keywords": ["defi", "dao", "amm", "nft", "dapp", "crowdsale", "foundry", "token",
                    "swap", "stake", "lottery", "loteria", "bank", "market", "blockchain", "contract", "solidity", "ethereum", "web3"],
        "languages": ["solidity", "vyper"],
    },
    "Rust": {
        "topics": ["rust"],
        "keywords": ["rust"],
        "languages": ["rust"],
    },
    "Web/Frontend": {
        "topics": ["frontend", "web", "react", "nextjs", "typescript"],
        "keywords": ["frontend", "web", "react", "next", "vue", "angular"],
        "languages": [],  # TypeScript/JS checked with keywords
    },
    "Learning": {
        "topics": ["learning", "course", "tutorial", "bootcamp", "education"],
        "keywords": ["bootcamp", "course", "aoc", "learning", "tutorial", "awesome"],
        "languages": [],
    },
    "Python Tools": {
        "topics": ["python", "cli", "tool", "utility"],
        "keywords": [],  # Catch-all for Python repos not matched above
        "languages": ["python"],
    },
}

# Order for displaying categories
CATEGORY_ORDER = ["AI/RAG", "Blockchain/DeFi", "Python Tools", "Web/Frontend", "Rust", "Learning"]


@dataclass
class Repository:
    """Represents a GitHub repository."""
    name: str
    description: str | None
    language: str | None
    url: str
    topics: list[str]
    is_fork: bool
    is_archived: bool
    stars: int
    updated_at: str


def fetch_repositories() -> list[Repository]:
    """Fetch all repositories for the configured GitHub user."""
    repos = []
    page = 1
    per_page = 100

    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    while True:
        url = f"{GITHUB_API}/users/{GITHUB_USERNAME}/repos"
        params = {"per_page": per_page, "page": page, "sort": "updated"}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data:
            break

        for repo in data:
            repos.append(Repository(
                name=repo["name"],
                description=repo["description"],
                language=repo["language"],
                url=repo["html_url"],
                topics=repo.get("topics", []),
                is_fork=repo["fork"],
                is_archived=repo["archived"],
                stars=repo["stargazers_count"],
                updated_at=repo["updated_at"],
            ))

        if len(data) < per_page:
            break
        page += 1

    return repos


def classify_repository(repo: Repository) -> str:
    """
    Classify a repository into a category using hybrid approach.

    Priority: topics > language > name/description keywords > default
    """
    name_lower = repo.name.lower()
    desc_lower = (repo.description or "").lower()
    language_lower = (repo.language or "").lower()
    topics_lower = [t.lower() for t in repo.topics]
    searchable_text = f"{name_lower} {desc_lower}"

    # 1. Check topics first (highest priority)
    for category, rules in CATEGORIES.items():
        if any(topic in topics_lower for topic in rules["topics"]):
            return category

    # 2. Check language-based categories (Solidity, Rust)
    for category, rules in CATEGORIES.items():
        if language_lower in rules["languages"] and category in ["Blockchain/DeFi", "Rust"]:
            return category

    # 3. Check name AND description for keywords (in priority order)
    # Check Blockchain/DeFi first (higher priority than AI/RAG for mixed cases)
    blockchain_rules = CATEGORIES["Blockchain/DeFi"]
    if any(kw in searchable_text for kw in blockchain_rules["keywords"]):
        return "Blockchain/DeFi"

    # Then check AI/RAG (requires Python context)
    ai_rules = CATEGORIES["AI/RAG"]
    if any(kw in searchable_text for kw in ai_rules["keywords"]):
        if language_lower in ["python", "jupyter notebook", ""]:
            return "AI/RAG"

    # Check Learning
    learning_rules = CATEGORIES["Learning"]
    if any(kw in searchable_text for kw in learning_rules["keywords"]):
        return "Learning"

    # Check Web/Frontend (requires JS/TS context)
    web_rules = CATEGORIES["Web/Frontend"]
    if any(kw in searchable_text for kw in web_rules["keywords"]):
        if language_lower in ["typescript", "javascript", ""]:
            return "Web/Frontend"

    # 4. Default Python repos to Python Tools
    if language_lower in ["python", "jupyter notebook"]:
        return "Python Tools"

    # 5. Default JS/TS to Web/Frontend
    if language_lower in ["typescript", "javascript"]:
        return "Web/Frontend"

    return "Other"


def generate_description(repo: Repository) -> str:
    """Generate a description for a repo if none exists."""
    if repo.description:
        # Clean up and truncate if needed
        desc = repo.description.strip()
        if len(desc) > 100:
            desc = desc[:97] + "..."
        return desc

    # Generate from name
    name_parts = repo.name.replace("-", " ").replace("_", " ").title()
    return f"{name_parts} project"


def generate_markdown(categorized_repos: dict[str, list[Repository]]) -> str:
    """Generate markdown for all categorized repositories."""
    lines = [
        "## Repository Showcase",
        "",
        "*Auto-updated daily. Organized by primary focus area.*",
        "",
    ]

    for category in CATEGORY_ORDER:
        repos = categorized_repos.get(category, [])
        if not repos:
            continue

        # Sort by stars (descending), then by name
        repos.sort(key=lambda r: (-r.stars, r.name.lower()))

        lines.append(f"### {category}")
        lines.append("")

        for repo in repos:
            description = generate_description(repo)
            language = repo.language or "Various"
            stars_badge = f" ⭐ {repo.stars}" if repo.stars > 0 else ""

            lines.append(f"- **[{repo.name}]({repo.url})** - {description}")
            lines.append(f"  `{language}`{stars_badge}")
            lines.append("")

    # Handle "Other" category if any
    other_repos = categorized_repos.get("Other", [])
    if other_repos:
        lines.append("### Other Projects")
        lines.append("")
        for repo in sorted(other_repos, key=lambda r: r.name.lower()):
            description = generate_description(repo)
            language = repo.language or "Various"
            lines.append(f"- **[{repo.name}]({repo.url})** - {description}")
            lines.append(f"  `{language}`")
            lines.append("")

    return "\n".join(lines)


def update_readme(new_content: str) -> bool:
    """
    Update README.md with new content between markers.

    Returns True if changes were made, False otherwise.
    """
    if not README_PATH.exists():
        print(f"ERROR: README not found at {README_PATH}")
        return False

    readme_content = README_PATH.read_text(encoding="utf-8")

    # Check if markers exist
    if START_MARKER not in readme_content:
        print(f"ERROR: Start marker '{START_MARKER}' not found in README")
        return False

    if END_MARKER not in readme_content:
        print(f"ERROR: End marker '{END_MARKER}' not found in README")
        return False

    # Replace content between markers
    pattern = re.compile(
        f"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL
    )

    new_section = f"{START_MARKER}\n\n{new_content}\n{END_MARKER}"
    updated_content = pattern.sub(new_section, readme_content)

    if updated_content == readme_content:
        print("No changes detected")
        return False

    README_PATH.write_text(updated_content, encoding="utf-8")
    print("README updated successfully")
    return True


def main():
    """Main entry point."""
    print(f"Fetching repositories for {GITHUB_USERNAME}...")
    repos = fetch_repositories()
    print(f"Found {len(repos)} repositories")

    # Filter out forks, archived, and profile repo
    repos = [
        r for r in repos
        if not r.is_fork
        and not r.is_archived
        and r.name != GITHUB_USERNAME
    ]
    print(f"After filtering: {len(repos)} repositories")

    # Classify repositories
    categorized: dict[str, list[Repository]] = {}
    for repo in repos:
        category = classify_repository(repo)
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(repo)
        print(f"  {repo.name} -> {category}")

    # Generate markdown
    markdown = generate_markdown(categorized)

    # Update README
    update_readme(markdown)


if __name__ == "__main__":
    main()
