# Git Puller

A Python utility to clone all repositories from a GitHub organization using SSH by default.

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/git_puller.git
   cd git_puller
   ```

2. Create a virtual environment and install dependencies using uv:
   ```
   uv venv
   uv pip install -r requirements.txt
   ```

## Usage

Basic usage:
```
python git_puller.py https://github.com/organization-name
```

This will create a directory named after the organization and clone all repositories into it using SSH.

### SSH Authentication

By default, Git Puller uses SSH for cloning. Make sure your SSH key is:
1. Generated (`ssh-keygen`)
2. Added to your GitHub account
3. Added to the SSH agent (`ssh-add ~/.ssh/id_rsa`)

### Options

- `-t, --token`: GitHub personal access token for authentication (only used with --https option)
- `-o, --output-dir`: Base directory to store the cloned repositories
- `-s, --skip-existing`: Skip repositories that already exist locally
- `--https`: Use HTTPS instead of SSH for cloning repositories

### Examples

Clone repositories using the default SSH method:
```
python git_puller.py https://github.com/organization-name
```

Clone repositories using HTTPS with a token:
```
python git_puller.py https://github.com/organization-name --https -t your_github_token
```

Specify output directory:
```
python git_puller.py https://github.com/organization-name -o ~/projects
```

Skip existing repositories:
```
python git_puller.py https://github.com/organization-name -s
```

## License

MIT