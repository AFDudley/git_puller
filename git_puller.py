#!/usr/bin/env python3
"""
Git Repository Puller

This script takes a GitHub or Gitea organization URL as input and clones all repositories
from that organization into a local directory named after the organization.

Note: For GitHub organizations with private repositories, you must provide a personal access
token using the -t/--token option. Without a token, only public repositories will be discovered
and cloned, even if you have SSH access to private repositories.
"""

import os
import sys
import re
import argparse
import requests
from pathlib import Path
from github import Github
import git
from urllib.parse import urlparse


def parse_git_url(url):
    """
    Parse a GitHub or Gitea URL to extract host, organization, and determine platform.
    
    Returns:
        tuple: (hostname, organization name, platform type)
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
    
    # Determine if it's GitHub or Gitea
    if 'github.com' in hostname:
        platform = 'github'
    else:
        platform = 'gitea'  # Default to Gitea for other hosts
    
    return hostname, org_name, platform


def build_clone_url(hostname, org_name, repo_name, token=None, use_https=False):
    """Build clone URL for any platform."""
    if use_https:
        if token:
            return f"https://{token}@{hostname}/{org_name}/{repo_name}.git"
        return f"https://{hostname}/{org_name}/{repo_name}.git"
    return f"git@{hostname}:{org_name}/{repo_name}.git"


def clone_or_update_mirror(repo_path, clone_url, repo_name, update=True):
    """Clone a new mirror or update an existing one. Returns True if cloned."""
    if repo_path.exists():
        if update:
            print(f"Updating existing mirror: {repo_name}")
            try:
                existing_repo = git.Repo(repo_path)
                existing_repo.git.remote('update')
                print(f"Successfully updated {repo_name}")
            except Exception as e:
                print(f"Error updating {repo_name}: {e}")
        return False

    print(f"Cloning mirror of {repo_name}...")
    try:
        cloned_repo = git.Repo.clone_from(clone_url, repo_path, multi_options=['--mirror'])
        branches = [ref.name for ref in cloned_repo.refs if not ref.name.startswith('refs/')]
        print(f"Successfully cloned mirror of {repo_name} ({len(branches)} branches):")
        for branch in branches:
            print(f"  {branch}")
        return True
    except Exception as e:
        print(f"Error cloning {repo_name}: {e}")
        return False


def clone_github_repos(org_name, token=None, output_dir=None, update=True, use_https=False):
    """Clone all repositories from the specified GitHub organization.

    TODO: Consider adding a --skip-existing flag in the future to skip repos entirely.
    """
    # Initialize GitHub API client
    g = Github(token) if token else Github()
    
    try:
        # Get the organization
        org = g.get_organization(org_name)
        print(f"Found GitHub organization: {org.name or org_name}")
        
        # Create output directory named after the organization
        if output_dir:
            output_path = Path(output_dir) / org_name
        else:
            output_path = Path(org_name)
        
        output_path.mkdir(exist_ok=True, parents=True)
        print(f"Repositories will be cloned to: {output_path.absolute()}")
        
        # Get all repositories for the organization (PyGithub handles pagination)
        if not token:
            print("Note: No token provided, only public repos will be pulled")
        repos = list(org.get_repos())
        print(f"Found {len(repos)} repositories")
        
        # Clone each repository as a mirror
        for repo in repos:
            repo_path = output_path / f"{repo.name}.git"
            clone_url = build_clone_url("github.com", org_name, repo.name, token, use_https)
            clone_or_update_mirror(repo_path, clone_url, repo.name, update)

        print(f"Finished cloning repositories from {org_name}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Close the GitHub client connection
        g.close()


def clone_gitea_repos(hostname, org_name, token=None, output_dir=None, update=True, use_https=False):
    """Clone all repositories from the specified Gitea organization.

    TODO: Consider adding a --skip-existing flag in the future to skip repos entirely.
    """
    if not token:
        print("Error: Gitea API requires a token for authentication")
        print("Please provide a token with the -t or --token option")
        sys.exit(1)
        
    try:
        # Create API URL for the Gitea organization's repositories
        api_url = f"https://{hostname}/api/v1/orgs/{org_name}/repos"
        headers = {"Authorization": f"token {token}"}

        # Fetch all repositories with pagination
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
        
        # Create output directory named after the organization
        if output_dir:
            output_path = Path(output_dir) / org_name
        else:
            output_path = Path(org_name)
        
        output_path.mkdir(exist_ok=True, parents=True)
        print(f"Repositories will be cloned to: {output_path.absolute()}")
        
        print(f"Found {len(repos)} repositories")
        
        # Clone each repository as a mirror
        for repo in repos:
            repo_name = repo['name']
            repo_path = output_path / f"{repo_name}.git"
            clone_url = build_clone_url(hostname, org_name, repo_name, token, use_https)
            clone_or_update_mirror(repo_path, clone_url, repo_name, update)

        print(f"Finished cloning repositories from {org_name}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error accessing Gitea API: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Clone all repositories from a GitHub or Gitea organization"
    )
    parser.add_argument(
        "url", 
        help="Organization URL (e.g., https://github.com/organization or https://gitea.example.com/organization)"
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
    
    try:
        # Parse the URL to determine the platform and extract organization name
        hostname, org_name, platform = parse_git_url(args.url)
        print(f"Detected platform: {platform.capitalize()}")
        print(f"Organization: {org_name}")
        
        # Clone repositories based on the platform
        if platform == 'github':
            clone_github_repos(
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
    
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()