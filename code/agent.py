#!/usr/bin/env python3

import os
import subprocess
import tempfile
import shutil
import requests
import base64
import re
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")

from google.adk.agents import Agent


def diagnose_git_setup():
    """Diagnose Git and GitHub setup issues."""
    try:
        diagnosis = {
            "status": "success",
            "checks": [],
            "recommendations": []
        }

        # Check 1: Git installation
        try:
            git_version = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
            if git_version.returncode == 0:
                diagnosis["checks"].append(f"✅ Git installed: {git_version.stdout.strip()}")
            else:
                diagnosis["checks"].append("❌ Git not working properly")
                diagnosis["recommendations"].append("Install Git: brew install git (macOS) or apt install git (Ubuntu)")
        except FileNotFoundError:
            diagnosis["checks"].append("❌ Git not found")
            diagnosis["recommendations"].append("Install Git from https://git-scm.com/")
        except subprocess.TimeoutExpired:
            diagnosis["checks"].append("❌ Git command timed out")

        # Check 2: GitHub token
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            diagnosis["checks"].append("✅ GITHUB_TOKEN environment variable found")

            # Test GitHub API access
            try:
                headers = {'Authorization': f'token {github_token}'}
                response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
                if response.status_code == 200:
                    user_data = response.json()
                    diagnosis["checks"].append(
                        f"✅ GitHub API access verified for user: {user_data.get('login', 'Unknown')}")
                else:
                    diagnosis["checks"].append(f"❌ GitHub API access failed: {response.status_code}")
                    diagnosis["recommendations"].append("Check if GitHub token is valid and has repo scope")
            except Exception as e:
                diagnosis["checks"].append(f"❌ GitHub API test failed: {str(e)}")
        else:
            diagnosis["checks"].append("❌ GITHUB_TOKEN not found")
            diagnosis["recommendations"].append(
                "Set GITHUB_TOKEN in .env file with a valid GitHub Personal Access Token")

        # Check 3: Git configuration
        try:
            git_user = subprocess.run(['git', 'config', '--global', 'user.name'], capture_output=True, text=True)
            git_email = subprocess.run(['git', 'config', '--global', 'user.email'], capture_output=True, text=True)

            if git_user.returncode == 0 and git_user.stdout.strip():
                diagnosis["checks"].append(f"✅ Git user.name: {git_user.stdout.strip()}")
            else:
                diagnosis["checks"].append("⚠️ Git user.name not set globally")
                diagnosis["recommendations"].append("Run: git config --global user.name 'Your Name'")

            if git_email.returncode == 0 and git_email.stdout.strip():
                diagnosis["checks"].append(f"✅ Git user.email: {git_email.stdout.strip()}")
            else:
                diagnosis["checks"].append("⚠️ Git user.email not set globally")
                diagnosis["recommendations"].append("Run: git config --global user.email 'your.email@example.com'")
        except Exception as e:
            diagnosis["checks"].append(f"❌ Git config check failed: {str(e)}")

        # Check 4: Test directory permissions
        try:
            test_dir = tempfile.mkdtemp(prefix="git_test_")
            diagnosis["checks"].append(f"✅ Can create temporary directories: {test_dir}")
            shutil.rmtree(test_dir)
        except Exception as e:
            diagnosis["checks"].append(f"❌ Cannot create temporary directories: {str(e)}")
            diagnosis["recommendations"].append("Check file system permissions")

        # Check 5: Network connectivity to GitHub
        try:
            response = requests.get('https://github.com', timeout=10)
            if response.status_code == 200:
                diagnosis["checks"].append("✅ Network access to GitHub")
            else:
                diagnosis["checks"].append(f"❌ GitHub not accessible: {response.status_code}")
        except Exception as e:
            diagnosis["checks"].append(f"❌ Network connectivity issue: {str(e)}")
            diagnosis["recommendations"].append("Check internet connection and firewall settings")

        return diagnosis

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Diagnostic failed: {str(e)}"
        }


def test_simple_clone(repository_url: str):
    """Test a simple Git clone operation with detailed error reporting."""
    try:
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            return {
                "status": "error",
                "error_message": "No GitHub token found",
                "suggestion": "Set GITHUB_TOKEN in your .env file"
            }

        # Parse repository URL
        url_pattern = r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
        match = re.search(url_pattern, repository_url.replace('https://', '').replace('http://', ''))

        if not match:
            return {
                "status": "error",
                "error_message": f"Invalid GitHub URL format: {repository_url}"
            }

        owner, repo = match.groups()

        # Test different clone methods
        results = {
            "status": "testing",
            "repository": f"{owner}/{repo}",
            "tests": []
        }

        # Method 1: Clone with token in URL
        clone_url_with_token = f"https://{github_token}@github.com/{owner}/{repo}.git"
        temp_dir = tempfile.mkdtemp(prefix="clone_test_")
        repo_dir = os.path.join(temp_dir, repo)

        try:
            print(f"Testing clone of {owner}/{repo}...")
            clone_result = subprocess.run([
                'git', 'clone', clone_url_with_token, repo_dir
            ], capture_output=True, text=True, timeout=30)

            if clone_result.returncode == 0:
                results["tests"].append({
                    "method": "Token in URL",
                    "status": "success",
                    "message": "Clone successful"
                })
                results["status"] = "success"

                # Check if we can access the repository
                if os.path.exists(os.path.join(repo_dir, '.git')):
                    results["tests"].append({
                        "method": "Repository structure",
                        "status": "success",
                        "message": ".git directory found"
                    })

            else:
                results["tests"].append({
                    "method": "Token in URL",
                    "status": "failed",
                    "error": clone_result.stderr,
                    "stdout": clone_result.stdout
                })

        except subprocess.TimeoutExpired:
            results["tests"].append({
                "method": "Token in URL",
                "status": "timeout",
                "error": "Clone operation timed out after 30 seconds"
            })

        except Exception as e:
            results["tests"].append({
                "method": "Token in URL",
                "status": "error",
                "error": str(e)
            })

        finally:
            # Cleanup
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                results["tests"].append({
                    "method": "Cleanup",
                    "status": "warning",
                    "message": f"Could not clean up: {e}"
                })

        # Method 2: Test repository access via API first
        try:
            headers = {'Authorization': f'token {github_token}'}
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            api_response = requests.get(api_url, headers=headers, timeout=10)

            if api_response.status_code == 200:
                repo_data = api_response.json()
                results["tests"].append({
                    "method": "API Access",
                    "status": "success",
                    "message": f"Repository accessible via API. Private: {repo_data.get('private', 'unknown')}"
                })
            elif api_response.status_code == 404:
                results["tests"].append({
                    "method": "API Access",
                    "status": "failed",
                    "error": "Repository not found or no access"
                })
            else:
                results["tests"].append({
                    "method": "API Access",
                    "status": "failed",
                    "error": f"API returned {api_response.status_code}"
                })

        except Exception as e:
            results["tests"].append({
                "method": "API Access",
                "status": "error",
                "error": str(e)
            })

        return results

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Clone test failed: {str(e)}"
        }


def get_github_file(repository_url: str, file_path: str, branch: str = "main"):
    """Read files from GitHub repositories using GitHub API."""
    try:
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            return {
                "status": "error",
                "error_message": "GitHub token not found. Please set GITHUB_TOKEN in your .env file.",
                "instructions": "Get a token from https://github.com/settings/tokens with 'repo' scope"
            }

        # Parse GitHub URL
        url_pattern = r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
        match = re.search(url_pattern, repository_url.replace('https://', '').replace('http://', ''))

        if not match:
            return {
                "status": "error",
                "error_message": f"Invalid GitHub URL format: {repository_url}",
                "example": "Use format: https://github.com/owner/repo"
            }

        owner, repo = match.groups()

        # Make API request
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        if branch != "main":
            api_url += f"?ref={branch}"

        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Decode content
            if data.get('encoding') == 'base64':
                content = base64.b64decode(data['content']).decode('utf-8')
            else:
                content = data.get('content', '')

            return {
                "status": "success",
                "repository": f"{owner}/{repo}",
                "file_path": file_path,
                "branch": branch,
                "size": data.get('size', 0),
                "content": content,
                "sha": data.get('sha'),
                "message": f"Successfully read {file_path} from {owner}/{repo}"
            }

        elif response.status_code == 404:
            return {
                "status": "error",
                "error_message": f"File not found: {file_path} in {owner}/{repo}",
                "suggestion": "Check the file path and branch name"
            }

        else:
            return {
                "status": "error",
                "error_message": f"GitHub API error: {response.status_code}",
                "details": response.text[:200]
            }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Unexpected error: {str(e)}"
        }


def fix_git_setup():
    """Attempt to fix common Git setup issues."""
    try:
        fixes_applied = []

        # Fix 1: Set up Git user configuration
        try:
            subprocess.run(['git', 'config', '--global', 'user.name', 'AI Agent'], check=True)
            subprocess.run(['git', 'config', '--global', 'user.email', 'ai-agent@example.com'], check=True)
            fixes_applied.append("✅ Set Git user.name and user.email")
        except Exception as e:
            fixes_applied.append(f"❌ Could not set Git config: {e}")

        # Fix 2: Set up credential helper (for macOS)
        try:
            if os.system('which git-credential-osxkeychain') == 0:
                subprocess.run(['git', 'config', '--global', 'credential.helper', 'osxkeychain'], check=True)
                fixes_applied.append("✅ Set Git credential helper for macOS")
        except Exception as e:
            fixes_applied.append(f"⚠️ Could not set credential helper: {e}")

        # Fix 3: Clear any cached credentials that might be wrong
        try:
            subprocess.run(['git', 'credential', 'reject'], input='host=github.com\nprotocol=https\n\n',
                           text=True, capture_output=True)
            fixes_applied.append("✅ Cleared cached credentials")
        except Exception as e:
            fixes_applied.append(f"⚠️ Could not clear credentials: {e}")

        return {
            "status": "success",
            "fixes_applied": fixes_applied,
            "message": "Applied common Git fixes"
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Fix attempt failed: {str(e)}"
        }


def create_file_via_api(repository_url: str, file_path: str, file_content: str,
                        commit_message: str = "AI Agent: Created file"):
    """Create a file using GitHub API instead of Git clone (fallback method)."""
    try:
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            return {
                "status": "error",
                "error_message": "GitHub token not found"
            }

        # Parse repository URL
        url_pattern = r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
        match = re.search(url_pattern, repository_url.replace('https://', '').replace('http://', ''))

        if not match:
            return {
                "status": "error",
                "error_message": f"Invalid GitHub URL format: {repository_url}"
            }

        owner, repo = match.groups()

        # Create file using GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }

        # Encode content to base64
        encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

        data = {
            "message": commit_message,
            "content": encoded_content
        }

        response = requests.put(api_url, headers=headers, json=data, timeout=10)

        if response.status_code in [200, 201]:
            result_data = response.json()
            return {
                "status": "success",
                "repository": f"{owner}/{repo}",
                "file_path": file_path,
                "commit_sha": result_data.get('commit', {}).get('sha'),
                "message": f"Successfully created {file_path} using GitHub API",
                "method": "api_only"
            }
        else:
            return {
                "status": "error",
                "error_message": f"GitHub API error: {response.status_code}",
                "details": response.text[:200]
            }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"API file creation failed: {str(e)}"
        }


# Create the main agent with diagnostic capabilities
root_agent = Agent(
    name="diagnostic_git_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="AI agent with Git diagnostics and fallback capabilities",
    instruction="""You are an AI assistant with Git capabilities and diagnostic tools. When Git operations fail, you can diagnose the issue and provide solutions.

DIAGNOSTIC CAPABILITIES:
1. Check Git installation and configuration
2. Test GitHub token and API access
3. Diagnose clone failures with detailed error reporting
4. Apply common fixes for Git setup issues
5. Fallback to API-only operations when Git clone fails

AVAILABLE TOOLS:
1. diagnose_git_setup() - Check Git and GitHub configuration
2. test_simple_clone(repository_url) - Test cloning with detailed diagnostics
3. fix_git_setup() - Apply common Git configuration fixes
4. get_github_file(repository_url, file_path, branch) - Read files via API
5. create_file_via_api(repository_url, file_path, file_content, commit_message) - Create files via API

TROUBLESHOOTING WORKFLOW:
When a user reports Git clone failures:
1. First run diagnose_git_setup() to check the basic setup
2. Then run test_simple_clone() on their repository
3. If issues are found, run fix_git_setup() to apply fixes
4. As a fallback, use create_file_via_api() for file operations

EXAMPLE USAGE:

Diagnostics:
- "Diagnose my Git setup and check for issues"
- "Test cloning my repository and show detailed results"
- "Fix common Git configuration problems"

File Operations (when Git clone fails):
- "Read the README.md file using API access"
- "Create a new Python file using the GitHub API"

The agent will provide detailed diagnostic information and suggest specific fixes for common Git issues.""",
    tools=[diagnose_git_setup, test_simple_clone, fix_git_setup, get_github_file, create_file_via_api]
)

if __name__ == "__main__":
    print("🔧 Diagnostic Git Agent - Troubleshooting Tools")
    print("=" * 55)
    print("Diagnostic Capabilities:")
    print("✅ Check Git installation and configuration")
    print("✅ Test GitHub token and API access")
    print("✅ Diagnose clone failures with detailed reporting")
    print("✅ Apply common Git setup fixes")
    print("✅ Fallback to API-only operations")
    print("✅ Detailed error analysis and recommendations")
    print("\nUse this agent to troubleshoot Git clone issues")
    print("Run with: adk run . or python -m google.adk.cli run .")
