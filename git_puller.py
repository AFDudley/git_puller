#!/usr/bin/env python3
"""
GitHub Organization Repository Puller

This script takes a GitHub organization URL as input and clones all repositories
from that organization into a local directory named after the organization.
"""

import os
import sys
import re
import argparse
from pathlib import Path
from github import Github
import git


def parse_github_url(url):
    """Extract organization name from GitHub URL."""
    # Match patterns like https://github.com/organization or github.com/organization
    pattern = r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)/?.*'
    match = re.match(pattern, url)
    
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    
    return match.group(1)


def clone_repos(org_name, token=None, output_dir=None, skip_existing=False, use_https=False):
    """Clone all repositories from the specified GitHub organization."""
    # Initialize GitHub API client
    g = Github(token) if token else Github()
    
    try:
        # Get the organization
        org = g.get_organization(org_name)
        print(f"Found organization: {org.name or org_name}")
        
        # Create output directory named after the organization
        if output_dir:
            output_path = Path(output_dir) / org_name
        else:
            output_path = Path(org_name)
        
        output_path.mkdir(exist_ok=True, parents=True)
        print(f"Repositories will be cloned to: {output_path.absolute()}")
        
        # Get all repositories for the organization
        repos = list(org.get_repos())
        print(f"Found {len(repos)} repositories")
        
        # Clone each repository
        for repo in repos:
            repo_path = output_path / repo.name
            
            if repo_path.exists() and skip_existing:
                print(f"Skipping existing repository: {repo.name}")
                continue
            
            print(f"Cloning {repo.name}...")
            
            if use_https:
                if token:
                    # Use token for authentication in HTTPS URL
                    clone_url = repo.clone_url.replace('https://', f'https://{token}@')
                else:
                    clone_url = repo.clone_url
            else:
                # Use SSH URL for cloning (default)
                clone_url = f"git@github.com:{org_name}/{repo.name}.git"
                print(f"Using SSH URL: {clone_url}")
            
            try:
                git.Repo.clone_from(clone_url, repo_path)
                print(f"Successfully cloned {repo.name}")
            except Exception as e:
                print(f"Error cloning {repo.name}: {e}")
        
        print(f"Finished cloning repositories from {org_name}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Close the GitHub client connection
        g.close()


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Clone all repositories from a GitHub organization"
    )
    parser.add_argument(
        "url", 
        help="GitHub organization URL (e.g., https://github.com/organization)"
    )
    parser.add_argument(
        "-t", "--token", 
        help="GitHub personal access token for authentication"
    )
    parser.add_argument(
        "-o", "--output-dir", 
        help="Base directory to store the cloned repositories"
    )
    parser.add_argument(
        "-s", "--skip-existing",
        action="store_true",
        help="Skip repositories that already exist locally"
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS for cloning instead of SSH (SSH is default)"
    )
    
    args = parser.parse_args()
    
    try:
        # Parse the organization name from the URL
        org_name = parse_github_url(args.url)
        
        # Clone all repositories
        clone_repos(
            org_name, 
            token=args.token, 
            output_dir=args.output_dir,
            skip_existing=args.skip_existing,
            use_https=args.https
        )
    
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()