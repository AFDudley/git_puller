#!/usr/bin/env python3
"""
Git Repository Puller

This script takes a GitHub or Gitea URL as input and clones repositories.

- Organization URL (e.g., https://github.com/organization): Clones all repositories
- Repository URL (e.g., https://github.com/org/repo): Clones a single repository

Note: For GitHub organizations with private repositories, you must provide a personal access
token using the -t/--token option. Without a token, only public repositories will be discovered
and cloned, even if you have SSH access to private repositories.
"""

import shutil
import argparse
import requests
from pathlib import Path
from github import Github
import git
from urllib.parse import urlparse


def parse_git_url(url):
    """
    Parse a GitHub or Gitea URL to extract host, organization, repo name, and determine platform.

    Returns:
        tuple: (hostname, organization name, repo name or None, platform type)
    """
    parsed_url = urlparse(url)

    # If URL doesn't have a scheme, add one for parsing
    if not parsed_url.scheme:
        parsed_url = urlparse(f"https://{url}")

    # Extract the hostname and path
    hostname = parsed_url.netloc
    path_parts = parsed_url.path.strip('/').split('/')

    if not path_parts or not path_parts[0]:
        raise ValueError(f"Could not extract organization name from URL: {url}")

    org_name = path_parts[0]

    # If path has 2+ parts, second part is repo name
    repo_name = path_parts[1] if len(path_parts) > 1 else None

    # Strip .git suffix if present
    if repo_name and repo_name.endswith('.git'):
        repo_name = repo_name[:-4]

    # Determine if it's GitHub or Gitea
    if 'github.com' in hostname:
        platform = 'github'
    else:
        platform = 'gitea'  # Default to Gitea for other hosts

    return hostname, org_name, repo_name, platform


def build_clone_url(hostname, org_name, repo_name, token=None, use_https=False):
    """Build clone URL for any platform."""
    if use_https:
        if token:
            return f"https://{token}@{hostname}/{org_name}/{repo_name}.git"
        return f"https://{hostname}/{org_name}/{repo_name}.git"
    return f"git@{hostname}:{org_name}/{repo_name}.git"


def clone_or_update_mirror(repo_path, clone_url, repo_name, update=True, working_path=None):
    """Clone a new mirror or update an existing one. Returns True if cloned.

    If working_path is provided and the mirror doesn't exist but the working
    directory does, updates the working directory instead of re-cloning.
    """
    # Check if mirror exists
    if repo_path.exists():
        if update:
            print(f"Updating existing mirror: {repo_name}")
            existing_repo = git.Repo(repo_path)
            existing_repo.git.remote('update')
            print(f"Successfully updated {repo_name}")
        return False

    # Check if working directory exists (mirror was converted)
    if working_path and working_path.exists():
        if update:
            print(f"Updating existing repository: {repo_name}")
            existing_repo = git.Repo(working_path)
            existing_repo.git.fetch('--all')
            print(f"Successfully updated {repo_name}")
        return False

    print(f"Cloning mirror of {repo_name}...")
    cloned_repo = git.Repo.clone_from(clone_url, repo_path, multi_options=['--mirror'])
    branches = [
        ref.name.replace('refs/heads/', '')
        for ref in cloned_repo.refs
        if ref.name.startswith('refs/heads/')
    ]
    print(f"Successfully cloned mirror of {repo_name} ({len(branches)} branches):")
    for branch in branches:
        print(f"  {branch}")
    return True


def convert_mirror_to_working(mirror_path, working_path, repo_name):
    """Convert a mirror clone to a working directory.

    Uses a temporary directory for atomicity - if any step fails,
    the mirror remains intact.
    """
    print(f"Converting {repo_name} to working directory...")

    temp_working = working_path.parent / f".{repo_name}.tmp"

    # Clean up any leftover temp directory from previous failed attempt
    if temp_working.exists():
        shutil.rmtree(temp_working)

    # Clone from the mirror to temp directory
    git.Repo.clone_from(str(mirror_path), str(temp_working))

    # Remove the cloned .git and replace with mirror
    shutil.rmtree(temp_working / ".git")
    shutil.move(str(mirror_path), str(temp_working / ".git"))

    # Update config to convert from mirror to normal repo
    working_repo = git.Repo(temp_working)
    with working_repo.config_writer() as config:
        config.set_value('core', 'bare', 'false')
        # Fix remote config for normal fetch operations
        config.set_value('remote "origin"', 'fetch', '+refs/heads/*:refs/remotes/origin/*')
        config.remove_option('remote "origin"', 'mirror')
        config.remove_option('remote "origin"', 'tagopt')

    # Reset the index to match the working tree
    working_repo.git.reset()

    # Atomic rename to final location
    temp_working.rename(working_path)

    print(f"Converted {repo_name}")


def get_output_path(org_name, output_dir=None):
    """Build and create output directory for cloned repos."""
    if output_dir:
        output_path = Path(output_dir) / org_name
    else:
        output_path = Path(org_name)
    output_path.mkdir(exist_ok=True, parents=True)
    return output_path


def clone_repos(repo_names, hostname, org_name, output_path, token=None, update=True, use_https=False):
    """Clone a list of repositories as mirrors and convert to working directories."""
    for repo_name in repo_names:
        mirror_path = output_path / f"{repo_name}.git"
        working_path = output_path / repo_name
        clone_url = build_clone_url(hostname, org_name, repo_name, token, use_https)

        clone_or_update_mirror(mirror_path, clone_url, repo_name, update, working_path)

        if mirror_path.exists() and not working_path.exists():
            convert_mirror_to_working(mirror_path, working_path, repo_name)


def clone_single_repo(hostname, org_name, repo_name, token=None, output_dir=None, update=True, use_https=False):
    """Clone a single repository."""
    output_path = get_output_path(org_name, output_dir)
    print(f"Repository will be cloned to: {output_path.absolute()}")

    clone_repos([repo_name], hostname, org_name, output_path, token, update, use_https)

    print(f"Finished cloning {org_name}/{repo_name}")


def clone_github_repos(hostname, org_name, token=None, output_dir=None, update=True, use_https=False):
    """Clone all repositories from the specified GitHub organization."""
    g = Github(token) if token else Github()

    try:
        org = g.get_organization(org_name)
        print(f"Found GitHub organization: {org.name or org_name}")

        output_path = get_output_path(org_name, output_dir)
        print(f"Repositories will be cloned to: {output_path.absolute()}")

        if not token:
            print("Note: No token provided, only public repos will be pulled")
        repos = list(org.get_repos())
        print(f"Found {len(repos)} repositories")

        clone_repos([r.name for r in repos], hostname, org_name, output_path, token, update, use_https)

        print(f"Finished cloning repositories from {org_name}")
    finally:
        g.close()


def clone_gitea_repos(hostname, org_name, token=None, output_dir=None, update=True, use_https=False):
    """Clone all repositories from the specified Gitea organization."""
    if not token:
        raise ValueError("Gitea API requires a token for authentication. Use -t or --token option.")

    api_url = f"https://{hostname}/api/v1/orgs/{org_name}/repos"
    headers = {"Authorization": f"token {token}"}

    repos = []
    page = 1
    while True:
        response = requests.get(api_url, headers=headers, params={"page": page, "limit": 50})
        response.raise_for_status()
        page_repos = response.json()
        if not page_repos:
            break
        repos.extend(page_repos)
        page += 1

    print(f"Found Gitea organization: {org_name}")

    output_path = get_output_path(org_name, output_dir)
    print(f"Repositories will be cloned to: {output_path.absolute()}")
    print(f"Found {len(repos)} repositories")

    clone_repos([r['name'] for r in repos], hostname, org_name, output_path, token, update, use_https)

    print(f"Finished cloning repositories from {org_name}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Clone repositories from a GitHub or Gitea organization or a single repository"
    )
    parser.add_argument(
        "url",
        help="Organization or repository URL (e.g., https://github.com/org or https://github.com/org/repo)"
    )
    parser.add_argument(
        "-t", "--token", 
        help="Personal access token for authentication (required for Gitea, required for GitHub private repos)"
    )
    parser.add_argument(
        "-o", "--output-dir", 
        help="Base directory to store the cloned repositories"
    )
    parser.add_argument(
        "-u", "--no-update",
        action="store_true",
        help="Don't fetch updates for repositories that already exist locally"
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS for cloning instead of SSH (SSH is default)"
    )
    
    args = parser.parse_args()

    # Parse the URL to determine the platform and extract organization/repo name
    hostname, org_name, repo_name, platform = parse_git_url(args.url)
    print(f"Detected platform: {platform.capitalize()}")

    if repo_name:
        # Single repo mode
        print(f"Repository: {org_name}/{repo_name}")
        clone_single_repo(
            hostname,
            org_name,
            repo_name,
            token=args.token,
            output_dir=args.output_dir,
            update=not args.no_update,
            use_https=args.https
        )
    else:
        # Organization mode - clone all repos
        print(f"Organization: {org_name}")
        if platform == 'github':
            clone_github_repos(
                hostname,
                org_name,
                token=args.token,
                output_dir=args.output_dir,
                update=not args.no_update,
                use_https=args.https
            )
        else:  # Gitea
            clone_gitea_repos(
                hostname,
                org_name,
                token=args.token,
                output_dir=args.output_dir,
                update=not args.no_update,
                use_https=args.https
            )


if __name__ == "__main__":
    main()