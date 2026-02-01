#!/usr/bin/env python3
"""
AI Code Review for Azure DevOps Pull Requests

Uses the comprehensive code-review skill with language-specific references.

This script integrates with Azure DevOps to:
1. Fetch PR diff/changes
2. Load the code-review skill and relevant language references
3. Send to OpenAI for AI-powered code review
4. Post review comments (inline + summary) back to the PR

Environment Variables Required:
- SYSTEM_ACCESSTOKEN: Azure DevOps access token (auto-provided in pipelines)
- OPENAI_API_KEY: OpenAI API key
- PR_ID: Pull Request ID
- ORG_URL: Azure DevOps organization URL
- PROJECT: Project name
- REPO_ID: Repository ID

Optional:
- SKILL_PATH: Path to code-review skill directory (default: ~/.kimi/skills/code-review)
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Optional, Set
from dataclasses import dataclass

# Try to import OpenAI - handle both old and new versions
try:
    from openai import OpenAI
    OPENAI_NEW_VERSION = True
except ImportError:
    import openai
    OPENAI_NEW_VERSION = False


# ============================================================
# Configuration
# ============================================================

@dataclass
class Config:
    org_url: str
    project: str
    repo_id: str
    pr_id: str
    access_token: str
    openai_api_key: str
    skill_path: Path
    model: str = "gpt-5.2-codex"
    max_files: int = 50
    max_lines_per_file: int = 1000
    debug: bool = False


def load_config() -> Config:
    """Load configuration from environment variables."""
    required_vars = ['SYSTEM_ACCESSTOKEN', 'OPENAI_API_KEY', 'PR_ID', 'ORG_URL', 'PROJECT', 'REPO_ID']
    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # Determine skill path
    default_skill_path = Path.home() / '.kimi' / 'skills' / 'code-review'
    skill_path = Path(os.environ.get('SKILL_PATH', str(default_skill_path)))

    return Config(
        org_url=os.environ['ORG_URL'].rstrip('/'),
        project=os.environ['PROJECT'],
        repo_id=os.environ['REPO_ID'],
        pr_id=os.environ['PR_ID'],
        access_token=os.environ['SYSTEM_ACCESSTOKEN'],
        openai_api_key=os.environ['OPENAI_API_KEY'],
        skill_path=skill_path,
        model=os.environ.get('OPENAI_MODEL', 'gpt-5.2-codex'),
        max_files=int(os.environ.get('MAX_FILES', '50')),
        max_lines_per_file=int(os.environ.get('MAX_LINES_PER_FILE', '1000')),
        debug=os.environ.get('DEBUG', '').lower() == 'true'
    )


# ============================================================
# Code Review Skill Loader
# ============================================================

# Language detection based on file extensions
LANGUAGE_MAP = {
    '.py': 'python',
    '.pyw': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'javascript',
    '.tsx': 'javascript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    '.cs': 'csharp',
    '.java': 'java',
    '.kt': 'java',
    '.scala': 'java',
    '.go': 'go',
    '.rs': 'rust',
    '.c': 'cpp',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.h': 'cpp',
    '.hpp': 'cpp',
    '.vue': 'frontend',
    '.svelte': 'frontend',
    '.tsx': 'frontend',
    '.jsx': 'frontend',
}

# Framework detection based on file patterns
FRAMEWORK_PATTERNS = {
    'frontend': ['Component', 'React', 'Vue', 'Angular', 'useState', 'useEffect', '.vue', '.tsx', '.jsx'],
    'backend': ['Controller', 'Service', 'Repository', 'FastAPI', 'Flask', 'Express', 'Spring', 'app.', 'router.'],
}


def load_skill_content(skill_path: Path) -> str:
    """Load the main SKILL.md content."""
    skill_file = skill_path / 'SKILL.md'
    if skill_file.exists():
        content = skill_file.read_text(encoding='utf-8')
        # Remove YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content
    return ""


def load_reference(skill_path: Path, ref_name: str) -> str:
    """Load a specific reference file."""
    ref_file = skill_path / 'references' / f'{ref_name}.md'
    if ref_file.exists():
        content = ref_file.read_text(encoding='utf-8')
        return f"\n\n## {ref_name.upper()} Reference\n\n{content}"
    return ""


def detect_languages(files: list) -> Set[str]:
    """Detect programming languages from file list."""
    languages = set()
    for file in files:
        path = file.get('path', '')
        ext = Path(path).suffix.lower()
        if ext in LANGUAGE_MAP:
            languages.add(LANGUAGE_MAP[ext])
    return languages


def detect_frameworks(files: list) -> Set[str]:
    """Detect frameworks from file content."""
    frameworks = set()
    for file in files:
        content = file.get('content', '')
        path = file.get('path', '').lower()

        for framework, patterns in FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in path or pattern in content:
                    frameworks.add(framework)
                    break
    return frameworks


def build_review_prompt(skill_path: Path, files: list) -> str:
    """Build the complete review prompt with relevant references."""
    # Load main skill
    prompt = load_skill_content(skill_path)

    if not prompt:
        print("Warning: Could not load SKILL.md, using embedded prompt")
        prompt = get_fallback_prompt()
        return prompt

    # Detect languages and frameworks
    languages = detect_languages(files)
    frameworks = detect_frameworks(files)

    print(f"Detected languages: {languages}")
    print(f"Detected frameworks: {frameworks}")

    # Load relevant references
    loaded_refs = []

    # Always load security and architecture (core references)
    for core_ref in ['security', 'architecture', 'performance']:
        ref_content = load_reference(skill_path, core_ref)
        if ref_content:
            prompt += ref_content
            loaded_refs.append(core_ref)

    # Load language-specific references
    for lang in languages:
        ref_content = load_reference(skill_path, lang)
        if ref_content:
            prompt += ref_content
            loaded_refs.append(lang)

    # Load framework-specific references
    for fw in frameworks:
        ref_content = load_reference(skill_path, fw)
        if ref_content:
            prompt += ref_content
            loaded_refs.append(fw)

    print(f"Loaded references: {loaded_refs}")

    return prompt


def get_fallback_prompt() -> str:
    """Fallback prompt if skill files are not available."""
    return """# Code Review

You are an expert code reviewer. Review the provided PR diff and identify issues.

## Rules
- ONLY review changed lines (+ lines in diff)
- Do NOT flag issues in unchanged code
- Be specific with file paths and line numbers
- Provide actionable solutions with code examples

## Priority Order
1. **Critical**: Security vulnerabilities, data integrity risks, breaking changes
2. **High**: Logic errors, null handling, error handling issues
3. **Medium**: Performance, code quality, best practices
4. **Low**: Style, naming, minor improvements

## Output Format
Provide your review in this markdown format:

## Code Review Summary

**Overall Assessment**: [APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]

### Critical Issues (Blocking)
[List critical issues with file:line, problem, impact, solution]

### High Priority
[List high priority issues]

### Suggestions
[List suggestions and improvements]

### Positive Notes
[Acknowledge good code patterns]
"""


# ============================================================
# Azure DevOps API Client
# ============================================================

class AzureDevOpsClient:
    """Client for Azure DevOps REST API."""

    def __init__(self, config: Config):
        self.config = config
        self.headers = {
            'Authorization': f'Bearer {config.access_token}',
            'Content-Type': 'application/json'
        }
        self.base_url = f"{config.org_url}/{config.project}/_apis/git/repositories/{config.repo_id}"

    def get_pr_iterations(self) -> list:
        """Get all iterations for the PR."""
        url = f"{self.base_url}/pullRequests/{self.config.pr_id}/iterations?api-version=7.1"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get('value', [])

    def get_iteration_changes(self, iteration_id: int) -> list:
        """Get changed files for a specific iteration."""
        url = f"{self.base_url}/pullRequests/{self.config.pr_id}/iterations/{iteration_id}/changes?api-version=7.1"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get('changeEntries', [])

    def get_file_content(self, path: str, commit_id: str) -> Optional[str]:
        """Get file content at a specific commit."""
        url = f"{self.base_url}/items"
        params = {
            'path': path,
            'includeContent': 'true',
            'versionDescriptor.version': commit_id,
            'versionDescriptor.versionType': 'commit',
            'api-version': '7.1'
        }
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json().get('content', '')
        return None

    def post_pr_comment(self, content: str) -> bool:
        """Post a general comment thread on the PR."""
        url = f"{self.base_url}/pullRequests/{self.config.pr_id}/threads?api-version=7.1"

        body = {
            "comments": [{
                "parentCommentId": 0,
                "content": content,
                "commentType": 1
            }],
            "status": 1  # Active
        }

        response = requests.post(url, headers=self.headers, json=body)

        if response.status_code in [200, 201]:
            print("Posted summary comment")
            return True
        else:
            print(f"Failed to post comment: {response.status_code} - {response.text}")
            return False

    def post_inline_comment(
        self,
        file_path: str,
        line: int,
        content: str,
        change_tracking_id: int = 1,
        iteration_id: int = 1
    ) -> bool:
        """Post an inline comment on a specific file/line."""
        url = f"{self.base_url}/pullRequests/{self.config.pr_id}/threads?api-version=7.1"

        body = {
            "comments": [{
                "parentCommentId": 0,
                "content": content,
                "commentType": 1
            }],
            "status": 1,
            "threadContext": {
                "filePath": file_path,
                "rightFileStart": {"line": line, "offset": 1},
                "rightFileEnd": {"line": line, "offset": 1}
            },
            "pullRequestThreadContext": {
                "changeTrackingId": change_tracking_id,
                "iterationContext": {
                    "firstComparingIteration": iteration_id,
                    "secondComparingIteration": iteration_id
                }
            }
        }

        response = requests.post(url, headers=self.headers, json=body)

        if response.status_code in [200, 201]:
            print(f"  Posted inline comment on {file_path}:{line}")
            return True
        else:
            print(f"  Failed to post inline comment: {response.status_code}")
            if self.config.debug:
                print(f"    Response: {response.text}")
            return False


# ============================================================
# File Filtering
# ============================================================

# Extensions to review
REVIEW_EXTENSIONS = [
    '.py', '.js', '.ts', '.tsx', '.jsx',
    '.cs', '.java', '.go', '.rs', '.rb',
    '.cpp', '.c', '.h', '.hpp',
    '.swift', '.kt', '.scala',
    '.php', '.vue', '.svelte'
]

# Files/patterns to skip
SKIP_PATTERNS = [
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    '.min.js', '.min.css', '.bundle.js',
    'dist/', 'build/', 'node_modules/',
    '.generated.', '.Designer.cs',
    'migrations/', '__pycache__/'
]


def should_review_file(path: str) -> bool:
    """Check if file should be reviewed."""
    for pattern in SKIP_PATTERNS:
        if pattern in path:
            return False
    return any(path.endswith(ext) for ext in REVIEW_EXTENSIONS)


# ============================================================
# AI Review
# ============================================================

def perform_ai_review(files: list, config: Config) -> str:
    """Send files to AI for code review using the skill prompt."""
    if not files:
        return """## Code Review Summary

**Overall Assessment**: APPROVE

No reviewable files found in this PR.

---
*Generated by AI Code Review*"""

    # Build the system prompt with relevant references
    system_prompt = build_review_prompt(config.skill_path, files)

    # Build the diff content
    diff_content = "\n\n".join([
        f"### File: {f['path']} ({f['change_type']})\n```diff\n{f['content']}\n```"
        for f in files
    ])

    user_prompt = f"""Review the following Pull Request changes.

**IMPORTANT REMINDERS:**
- Review ONLY the changed lines (+ lines in diff)
- Do NOT flag issues in unchanged context lines
- Provide specific file:line references from the diff
- Include concrete code solutions for each issue

## PR Diff to Review

{diff_content}

---

Provide your code review following the format specified in the skill prompt.
"""

    try:
        if OPENAI_NEW_VERSION:
            client = OpenAI(api_key=config.openai_api_key)
            response = client.chat.completions.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            return response.choices[0].message.content
        else:
            openai.api_key = config.openai_api_key
            response = openai.ChatCompletion.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            return response.choices[0].message.content

    except Exception as e:
        print(f"Error during AI review: {e}")
        return f"""## Code Review Summary

**Overall Assessment**: NEEDS DISCUSSION

AI review encountered an error: {str(e)}

Please review this PR manually.

---
*Generated by AI Code Review*"""


def extract_issues_from_review(review_text: str) -> list:
    """Extract structured issues from the review text for inline comments."""
    issues = []

    # Simple pattern matching for file:line references
    import re

    # Match patterns like "**File**: `path/to/file.cs:123`" or "`file.cs:45-50`"
    file_line_pattern = r'\*\*File\*\*:\s*`([^`]+):(\d+)(?:-\d+)?`'

    # Find all critical and high priority sections
    sections = re.split(r'###\s+', review_text)

    for section in sections:
        if 'Critical' in section or 'High Priority' in section or 'High' in section:
            severity = 'critical' if 'Critical' in section else 'high'

            # Find all file:line matches in this section
            matches = re.findall(file_line_pattern, section)

            for file_path, line_num in matches:
                # Extract the issue text around this match
                issues.append({
                    'file': file_path if file_path.startswith('/') else f'/{file_path}',
                    'line': int(line_num),
                    'severity': severity
                })

    return issues


# ============================================================
# Main Entry Point
# ============================================================

def main():
    print("=" * 60)
    print("AI Code Review for Azure DevOps")
    print("Using code-review skill with language references")
    print("=" * 60)

    # Load configuration
    config = load_config()
    client = AzureDevOpsClient(config)

    print(f"\nProject: {config.project}")
    print(f"PR ID: {config.pr_id}")
    print(f"Model: {config.model}")
    print(f"Skill path: {config.skill_path}")

    # Check if skill exists
    if config.skill_path.exists():
        print(f"Skill directory found")
    else:
        print(f"Skill directory not found, using fallback prompt")

    # Get PR iterations
    print("\nFetching PR information...")
    iterations = client.get_pr_iterations()

    if not iterations:
        print("No iterations found. Exiting.")
        client.post_pr_comment("## AI Code Review\n\nNo changes found to review.")
        return

    latest_iteration = iterations[-1]
    iteration_id = latest_iteration['id']
    source_commit = latest_iteration.get('sourceRefCommit', {}).get('commitId', '')
    target_commit = latest_iteration.get('targetRefCommit', {}).get('commitId', '')

    print(f"Latest iteration: {iteration_id}")
    print(f"Source commit: {source_commit[:8] if source_commit else 'N/A'}")
    print(f"Target commit: {target_commit[:8] if target_commit else 'N/A'}")

    # Get changed files
    print("\nFetching changed files...")
    changes = client.get_iteration_changes(iteration_id)
    print(f"Found {len(changes)} changed files")

    # Collect files for review
    files_to_review = []
    skipped_files = []

    for change in changes:
        item = change.get('item', {})
        path = item.get('path', '')
        change_type = change.get('changeType', 'edit')
        change_tracking_id = change.get('changeTrackingId', 1)

        # Skip deleted files
        if change_type == 'delete':
            skipped_files.append(f"{path} (deleted)")
            continue

        # Check if we should review this file
        if not should_review_file(path):
            skipped_files.append(f"{path} (skipped)")
            continue

        # Get file content
        content = client.get_file_content(path, source_commit) if source_commit else None

        if content:
            # Truncate very large files
            lines = content.split('\n')
            if len(lines) > config.max_lines_per_file:
                content = '\n'.join(lines[:config.max_lines_per_file])
                content += f"\n... (truncated, {len(lines) - config.max_lines_per_file} lines omitted)"

            files_to_review.append({
                'path': path,
                'content': content,
                'change_type': change_type,
                'change_tracking_id': change_tracking_id
            })
            print(f"  {path}")
        else:
            skipped_files.append(f"{path} (content not available)")

    # Limit number of files
    if len(files_to_review) > config.max_files:
        print(f"\nLimiting to {config.max_files} files (out of {len(files_to_review)})")
        files_to_review = files_to_review[:config.max_files]

    if skipped_files and config.debug:
        print(f"\nSkipped {len(skipped_files)} files:")
        for f in skipped_files[:10]:
            print(f"  - {f}")
        if len(skipped_files) > 10:
            print(f"  ... and {len(skipped_files) - 10} more")

    # Perform AI review
    print(f"\nSending {len(files_to_review)} files to AI for review...")
    print("This may take a moment...")

    review_result = perform_ai_review(files_to_review, config)

    # Add metadata footer
    review_with_footer = f"""{review_result}

---
**Files reviewed:** {len(files_to_review)}
**Model:** {config.model}
*Generated by AI Code Review using code-review skill*"""

    # Post summary comment
    print("\nPosting review comments...")
    client.post_pr_comment(review_with_footer)

    # Extract and post inline comments for critical/high issues
    issues = extract_issues_from_review(review_result)
    print(f"\nFound {len(issues)} issues for inline comments")

    inline_count = 0
    for issue in issues[:10]:  # Limit inline comments
        # Find the file in our reviewed list to get change_tracking_id
        tracking_id = 1
        for f in files_to_review:
            if f['path'] == issue.get('file') or f['path'].endswith(issue.get('file', '').lstrip('/')):
                tracking_id = f.get('change_tracking_id', 1)
                break

        severity_emoji = {"critical": "CRITICAL", "high": "HIGH"}.get(issue.get('severity', ''), 'ISSUE')
        comment = f"**{severity_emoji}** - See PR review comment for details."

        if client.post_inline_comment(
            issue.get('file', ''),
            issue.get('line', 1),
            comment,
            tracking_id,
            iteration_id
        ):
            inline_count += 1

    print(f"\nPosted {inline_count} inline comments")
    print("\n" + "=" * 60)
    print("AI Code Review completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
