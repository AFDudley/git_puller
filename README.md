# Git Puller

A Python utility to clone all repositories from GitHub or Gitea organizations using SSH by default.

## Installation

Requires [uv](https://docs.astral.sh/uv/). The script is self-contained and manages its own dependencies.

```
git clone https://github.com/yourusername/git_puller.git
cd git_puller
```

## Usage

Basic usage:
```
./git_puller https://github.com/organization-name
```

This will create a directory named after the organization and clone all repositories into it using SSH.

### Platform Support

#### GitHub
- Supports both public and private repositories
- Token is optional (but recommended for private repos and to avoid rate limits)
- SSH is used by default, HTTPS is available as an option

#### Gitea
- Supports any Gitea instance (self-hosted or cloud)
- Token is **required** for authentication
- SSH is used by default, HTTPS is available as an option
- Any URL not containing "github.com" is treated as a Gitea instance

### SSH Authentication

By default, Git Puller uses SSH for cloning. Make sure your SSH key is:
1. Generated (`ssh-keygen`)
2. Added to your GitHub/Gitea account
3. Added to the SSH agent (`ssh-add ~/.ssh/id_rsa`)

### Options

- `-t, --token`: Personal access token for authentication (optional for GitHub, **required for Gitea**)
  - **GitHub tokens**: Must have `repo` scope to access private repositories
  - **Security recommendation**: Delete the token immediately after use to minimize exposure
- `-o, --output-dir`: Base directory to store the cloned repositories
- `-u, --no-update`: Don't fetch updates for repositories that already exist locally
- `--https`: Use HTTPS instead of SSH for cloning repositories

### Examples

Clone GitHub repositories using the default SSH method:
```
./git_puller https://github.com/organization-name
```

Clone Gitea repositories (token is required):
```
./git_puller https://gitea.example.com/organization-name -t your_gitea_token
```

Clone repositories using HTTPS with a token:
```
./git_puller https://github.com/organization-name --https -t your_github_token
```

Specify output directory:
```
./git_puller https://github.com/organization-name -o ~/projects
```

Skip updating existing repositories:
```
./git_puller https://github.com/organization-name -u
```

## License

MIT
