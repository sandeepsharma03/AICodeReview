#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Code Reviewer
Main orchestrator for AI-powered code reviews using GitHub Copilot CLI.
"""

import os
import sys
import time
import yaml
import json
import subprocess
import tempfile
from typing import Dict, List, Optional
from pathlib import Path

from github_client import GitHubClient, FileChange
from code_analyzer import CodeAnalyzer
from review_formatter import ReviewFormatter

class AICodeReviewer:
    """Main AI code reviewer orchestrator."""
    
    def __init__(self):
        """Initialize the AI code reviewer."""
        # Load environment variables
        # GHE_TOKEN: For GitHub Enterprise API (ghe.coxautoinc.com)
        # GITHUB_TOKEN: For Copilot CLI (github.com)
        try:
            self.ghe_token = os.environ["GHE_TOKEN"]
            self.pr_number = int(os.environ["PR_NUMBER"])
            self.repo_owner = os.environ["REPO_OWNER"]
            self.repo_name = os.environ["REPO_NAME"]
            self.base_sha = os.environ["BASE_SHA"]
            self.head_sha = os.environ["HEAD_SHA"]
        except KeyError as e:
            raise ValueError(f"Missing required environment variable: {e.args[0]}") from e
        except ValueError as e:
            raise ValueError(f"Invalid environment variable value: {e}") from e
        
        # Optional: GITHUB_TOKEN for Copilot CLI
        self.github_token = os.environ.get("GITHUB_TOKEN")
        
        # Initialize clients with GHE token
        self.github_client = GitHubClient(
            self.ghe_token,
            self.repo_owner,
            self.repo_name
        )
        
        # Check if GitHub Copilot CLI is available
        self.copilot_cmd = None
        self.copilot_available = self._check_copilot_cli()
        if self.copilot_available:
            print("✅ GitHub Copilot CLI detected")
        else:
            print("⚠️  GitHub Copilot CLI not available, using pattern-based analysis")
            print("    Install from: https://github.com/github/copilot-cli")
        
        # Load configuration
        self.config = self._load_config()
        self.analyzer = CodeAnalyzer(self.config)
        self.formatter = ReviewFormatter(self.config)
        
        # Review settings
        self.review_settings = self.config.get("review_settings", {})
        self.max_files = self.review_settings.get("max_files_per_review", 25)
        self.max_total_lines = self.review_settings.get("max_total_lines", 2000)
    
    def _check_copilot_cli(self) -> bool:
        """Check if GitHub Copilot CLI is available."""
        cmd_name = "copilot"
        # Try with PATH first
        try:
            result = subprocess.run(
                [cmd_name, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.copilot_cmd = cmd_name
                version = result.stdout.strip()
                print(f"    Using Copilot CLI: {cmd_name} (version detected)")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        
        print("    ⚠️  Copilot CLI not found. Install via: npm install -g @github/copilot")
        return False
    
    def _call_copilot_cli(self, prompt: str) -> Optional[str]:
        """
        Call GitHub Copilot CLI with a prompt.
        
        Args:
            prompt: The prompt to send to Copilot
            
        Returns:
            Copilot's response or None if failed
        """
        if not self.copilot_available or not self.copilot_cmd:
            return None
            
        try:
            # Use the new Copilot CLI with prompt mode (-p for non-interactive)
            # and silent mode (-s) to get clean output
            cmd = [
                self.copilot_cmd,
                "-p", prompt,
                "--log-level=all"
                "--allow-all-tools",  # Allow code analysis
                "--model", "gpt-4.1",  # Use GPT-4 for better analysis
                "--no-color"  # Disable color for easier parsing
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,  # Increased timeout for AI processing
                env= os.environ
            )
            
            # Check for errors
            if result.returncode != 0:
                print(f"    ⚠️  Copilot CLI error (exit code {result.returncode})")
                if result.stderr:
                    # Sanitize error message - avoid printing full errors that may contain tokens/paths
                    stderr_preview = result.stderr[:100].split('\n')[0]  # Only first line, truncated
                    print(f"    Error details: {stderr_preview}...")
                return None
            
            # Get response
            response = result.stdout.strip()
            
            if not response:
                print(f"    ⚠️  Copilot returned empty response")
                return None
            
            return response
        
        except subprocess.TimeoutExpired:
            print(f"    ⚠️  Copilot CLI timeout (exceeded 120s)")
            return None
        except Exception as e:
            print(f"    ⚠️  Error calling Copilot CLI: {str(e)}")
            return None
      
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        config_path = Path(__file__).parent.parent / "ai_review_config.yml"
        
        if not config_path.exists():
            print("Warning: Configuration file not found, using defaults")
            return {"review_settings": {}}
        
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def run(self) -> int:
        """
        Run the AI code review process.
        
        Returns:
            Exit code (0 for success)
        """
        print(f"🤖 Starting AI Code Review for PR #{self.pr_number}")
        print(f"Repository: {self.repo_owner}/{self.repo_name}")
        
        start_time = time.time()
        
        try:
            # Get PR information
            pr = self.github_client.get_pull_request(self.pr_number)
            print(f"PR Title: {pr.title}")
            print(f"Branch: {pr.head_branch} -> {pr.base_branch}")
            
            # Get changed files
            print("\n📁 Fetching changed files...")
            files = self.github_client.get_pr_files(self.pr_number)
            print(f"Found {len(files)} changed files")
            
            # Filter and prioritize files
            reviewable_files = self._filter_files(files)
            print(f"Selected {len(reviewable_files)} files for review")
            
            if not reviewable_files:
                print("No files to review")
                self._post_no_issues_comment()
                return 0
            
            # Check if Copilot CLI is available
            if not self.copilot_available:
                print("⚠️  Warning: GitHub Copilot CLI not available")
                print("Performing basic security analysis only...")
                all_findings = self._basic_security_analysis(reviewable_files)
            else:
                # Perform AI-powered review
                print("\n🔍 Performing AI code review with Copilot CLI...")
                all_findings = self._review_files(reviewable_files, pr)
            
            # Generate and post review
            end_time = time.time()
            review_time = int(end_time - start_time)
            
            review_stats = {
                "total_files_reviewed": len(reviewable_files),
                "total_findings": sum(len(findings) for findings in all_findings.values()),
                "review_time_seconds": review_time,
                "reviewed_files": [f.filename for f in reviewable_files]
            }
            
            print(f"\n📊 Review complete in {review_time}s")
            print(f"Total findings: {review_stats['total_findings']}")
            
            # Post results
            self._post_review(all_findings, pr, review_stats)
            
            print("\n✅ AI Code Review completed successfully")
            return 0
        
        except Exception as e:
            print(f"\n❌ Error during review: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try to post error comment
            try:
                error_comment = self.formatter.format_error_comment(str(e))
                self.github_client.create_issue_comment(self.pr_number, error_comment)
            except:
                pass
            
            return 1
    
    def _filter_files(self, files: List[FileChange]) -> List[FileChange]:
        """Filter and prioritize files for review."""
        reviewable = []
        
        print(f"\n🔍 Filtering {len(files)} changed files...")
        for file in files:
            print(f"  Checking: {file.filename} (status: {file.status}, changes: {file.changes})")
            
            # Skip deleted files
            if file.status == "removed":
                print(f"    ❌ Skipped: file removed")
                continue
            
            # Check if file should be reviewed
            if not self.analyzer.should_review_file(file.filename):
                print(f"    ❌ Skipped: excluded by config")
                continue
            
            # Check file size
            if file.changes > self.analyzer.max_lines_per_file:
                print(f"    ❌ Skipped: too large ({file.changes} > {self.analyzer.max_lines_per_file} lines)")
                continue
            
            print(f"    ✅ Included for review")
            reviewable.append(file)
        
        # Prioritize files
        file_dicts = [
            {"filename": f.filename, "changes": f.changes}
            for f in reviewable
        ]
        prioritized_dicts = self.analyzer.prioritize_files(file_dicts)
        
        # Reorder based on priority
        priority_map = {f["filename"]: i for i, f in enumerate(prioritized_dicts)}
        reviewable.sort(key=lambda f: priority_map.get(f.filename, 999))
        
        # Limit total files
        return reviewable[:self.max_files]
    
    def _review_files(self, files: List[FileChange], pr) -> Dict[str, List[Dict]]:
        """Review files using Copilot CLI."""
        all_findings = {}
        total_lines_reviewed = 0
        
        prompts = self.config.get("review_settings", {}).get("prompts", {})
        base_prompt = prompts.get("general", "Review this code for issues.")
        
        print(f"\n📝 Using review prompt from config:")
        print(f"   Prompt length: {len(base_prompt)} characters")
        print(f"   Available prompt types: {list(prompts.keys())}")
        if base_prompt != "Review this code for issues.":
            print(f"   ✅ Custom prompt loaded from ai_review_config.yml")
        else:
            print(f"   ⚠️  Using default prompt (config not loaded properly)")
        
        for i, file in enumerate(files, 1):
            print(f"  [{i}/{len(files)}] Reviewing {file.filename}...")
            
            # Check if we've exceeded line limit
            if total_lines_reviewed >= self.max_total_lines:
                print(f"    Reached max total lines limit ({self.max_total_lines})")
                break
            
            try:
                # Get file content
                content = self.github_client.get_file_content(file.filename, pr.head_sha)
                
                if not content:
                    print(f"    Could not get content, skipping")
                    continue
                
                # Review with Copilot CLI
                focus_areas = self.analyzer.get_focus_areas(file.language)
                findings = self._review_code_with_copilot(
                    file.filename,
                    content[:50000],  # Limit content size (increased for better analysis)
                    file.language,
                    focus_areas,
                    base_prompt
                )
                
                if findings:
                    all_findings[file.filename] = findings
                    print(f"    Found {len(findings)} issues")
                else:
                    print(f"    No issues found")
                
                total_lines_reviewed += len(content.split("\n"))
                
                # Rate limiting
                time.sleep(1)
            
            except Exception as e:
                print(f"    Error reviewing file: {str(e)}")
                continue
        
        return all_findings
    
    def _review_code_with_copilot(
        self,
        file_path: str,
        code_content: str,
        language: str,
        focus_areas: List[str],
        base_prompt: str
    ) -> List[Dict]:
        """
        Review code using GitHub Copilot CLI.
        
        Args:
            file_path: Path to the file
            code_content: Code to review
            language: Programming language
            focus_areas: Areas to focus on
            base_prompt: Base review prompt
            
        Returns:
            List of findings
        """
        if not self.copilot_available:
            return []
        
        focus_areas_str = ", ".join(focus_areas) if focus_areas else "general code quality"
        
        print(f"    🔍 Building prompt for {language} file")
        print(f"       Focus areas: {focus_areas_str}")
        print(f"       Base prompt preview: {base_prompt[:100]}...")
        
        # Build review prompt for text response
        prompt = f"""Review this {language} code from file: {file_path}

        {base_prompt}

        Focus areas: {focus_areas_str}

        Code to review:
        ```{language}
        {code_content}
        ```

        Provide a clear, concise code review listing any issues found.
        For each issue, specify:
        - Severity (critical/error/warning/info)
        - Category (security/performance/code_quality/best_practices)
        - Line number (if applicable)
        - Description of the issue
        - Specific recommendation to fix it

        Focus on actionable feedback. Only report real issues, not nitpicks.
        If the code is good, state "No issues found."""
        
        # Call Copilot CLI
        response = self._call_copilot_cli(prompt)
        
        if not response:
            print(f"    ℹ️  No response from Copilot CLI, using pattern-based analysis")
            return self._pattern_based_analysis(code_content, language)
        
        # Check if response indicates no issues
        if "no issues" in response.lower() or "looks good" in response.lower():
            print(f"    ✅ Copilot found no issues")
            return []
        
        # Parse text response into findings
        print(f"    ℹ️  Parsing Copilot text response")
        findings = self._parse_text_response(response, code_content, language)
        
        if findings:
            print(f"    ✅ Parsed {len(findings)} findings from Copilot response")
        else:
            print(f"    ℹ️  No structured findings from Copilot, using pattern-based analysis")
            findings = self._pattern_based_analysis(code_content, language)
        
        return findings
    
    def _parse_text_response(self, response: str, code_content: str, language: str) -> List[Dict]:
        """Parse plain text response from Copilot and convert to findings."""
        import re
        findings = []
        
        # Split response into lines and look for issue patterns
        lines = response.split('\n')
        
        current_finding = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for severity indicators
            severity_match = re.search(r'\b(critical|error|warning|info|suggestion)\b', line, re.IGNORECASE)
            if severity_match:
                # Save previous finding if exists
                if current_finding and current_finding.get('message'):
                    findings.append(current_finding)
                
                # Start new finding
                current_finding = {
                    'severity': severity_match.group(1).lower(),
                    'category': 'code_quality',
                    'message': '',
                    'line_number': None,
                    'suggestion': None,
                    'code_example': None
                }
            
            # Extract line numbers
            line_match = re.search(r'\bline\s+(\d+)\b', line, re.IGNORECASE)
            if line_match and current_finding:
                current_finding['line_number'] = int(line_match.group(1))
            
            # Extract category
            category_match = re.search(r'\b(security|performance|code_quality|best_practices|maintainability)\b', line, re.IGNORECASE)
            if category_match and current_finding:
                current_finding['category'] = category_match.group(1).lower()
            
            # Accumulate message text
            if current_finding and line:
                if current_finding['message']:
                    current_finding['message'] += '\n' + line
                else:
                    current_finding['message'] = line
        
        # Add last finding
        if current_finding and current_finding.get('message'):
            findings.append(current_finding)
        
        return findings
    
    def _pattern_based_analysis(self, code_content: str, language: str) -> List[Dict]:
        """Perform pattern-based code analysis as fallback."""
        findings = []
        
        print(f"    🔍 Running pattern analysis (language: {language}, code length: {len(code_content)} chars)")
        
        if language == "java":
            patterns = {
                "SQL Injection": (r"(?:SELECT|INSERT|UPDATE|DELETE).*['\"].*\+.*['\"]", "critical", "Use PreparedStatement with parameterized queries"),
                "Command Injection": (r"Runtime\.getRuntime\(\)\.exec\([^)]*\+", "critical", "Sanitize input and use ProcessBuilder with separate arguments"),
                "Hardcoded Password": (r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{3,}['\"]", "critical", "Store credentials securely using environment variables or vaults"),
                "XSS Vulnerability": (r"response\.getWriter\(\)\.print.*\+.*(?:request\.getParameter|userInput)", "critical", "Escape HTML entities before output"),
                "Resource Leak": (r"new\s+(?:FileInputStream|FileOutputStream|BufferedReader|Connection)\([^)]*\)(?!.*try-with-resources)", "error", "Use try-with-resources to prevent resource leaks"),
                "Empty Catch": (r"catch\s*\([^)]*\)\s*\{\s*\}", "warning", "Handle or log exceptions properly"),
                "MD5 Usage": (r"MessageDigest\.getInstance\(['\"]MD5['\"]\)", "critical", "Use SHA-256 or stronger hashing algorithms"),
                "String Comparison": (r"==.*['\"]|['\"].*==", "warning", "Use .equals() for String comparison"),
            }
        elif language == "python":
            patterns = {
                "SQL Injection": (r"(?:SELECT|INSERT|UPDATE|DELETE).*['\"].*%.*['\"]", "critical", "Use parameterized queries with ? placeholders"),
                "Command Injection": (r"os\.system\(.*\+|subprocess\.(?:call|run)\(.*\+", "critical", "Use subprocess with list arguments, not string concatenation"),
                "Hardcoded Secret": (r"(?:api_key|secret|token|password)\s*=\s*['\"][A-Za-z0-9]{10,}['\"]", "critical", "Use environment variables for secrets"),
                "Eval Usage": (r"\beval\(", "critical", "Avoid eval() - use safer alternatives like ast.literal_eval()"),
                "Bare Except": (r"except\s*:", "warning", "Catch specific exceptions instead of bare except"),
            }
        else:
            print(f"    ⚠️  No patterns defined for language: {language}")
            return []
        
        import re
        for issue_name, (pattern, severity, suggestion) in patterns.items():
            matches = list(re.finditer(pattern, code_content, re.MULTILINE | re.IGNORECASE))
            if matches:
                print(f"       Found {len(matches)} instances of {issue_name}")
            for match in matches:
                line_num = code_content[:match.start()].count('\n') + 1
                findings.append({
                    "severity": severity,
                    "category": "security" if severity == "critical" else "best_practices",
                    "message": f"{issue_name} detected",
                    "line_number": line_num,
                    "suggestion": suggestion,
                    "code_example": None
                })
        
        if findings:
            print(f"    ✅ Pattern analysis found {len(findings)} total issues")
        else:
            print(f"    ℹ️  No issues found in pattern analysis")
        
        return findings
    
    def _basic_security_analysis(self, files: List[FileChange]) -> Dict[str, List[Dict]]:
        """Perform basic security analysis without AI."""
        all_findings = {}
        
        for i, file in enumerate(files, 1):
            print(f"  [{i}/{len(files)}] Analyzing {file.filename}...")
            
            try:
                # Get file content
                content = self.github_client.get_file_content(file.filename, self.head_sha)
                
                if not content:
                    continue
                
                # Run security pattern detection
                security_issues = self.analyzer.detect_security_patterns(content, file.language)
                
                if security_issues:
                    findings = [
                        {
                            "severity": "warning",
                            "category": "security",
                            "message": issue["message"],
                            "line_number": None,
                            "suggestion": "Please review this code for security implications",
                            "code_example": None
                        }
                        for issue in security_issues
                    ]
                    all_findings[file.filename] = findings
                    print(f"    Found {len(findings)} potential issues")
            
            except Exception as e:
                print(f"    Error analyzing file: {str(e)}")
                continue
        
        return all_findings
    
    def _post_review(self, all_findings: Dict, pr, review_stats: Dict):
        """Post review findings to GitHub."""
        # Generate summary
        pr_info = {
            "number": pr.number,
            "title": pr.title
        }
        
        summary = self.formatter.format_review_summary(
            all_findings,
            pr_info,
            review_stats
        )
        
        # Post summary as PR comment
        print("\n💬 Posting review summary...")
        self.github_client.create_issue_comment(self.pr_number, summary)
        
        # Post inline comments for critical/error findings
        if self.config.get("integration", {}).get("create_review_thread", True):
            self._post_inline_comments(all_findings, pr.head_sha)
        
        # Save summary to file
        summary_file = Path(__file__).parent / "review_summary.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)
    
    def _post_inline_comments(self, all_findings: Dict, commit_sha: str):
        """Post inline comments for important findings."""
        print("💬 Posting inline comments...")
        
        comment_count = 0
        max_inline_comments = 10  # Limit to avoid spam
        
        for file_path, findings in all_findings.items():
            # Only post inline comments for critical/error findings
            important_findings = [
                f for f in findings
                if f.get("severity") in ["critical", "error"]
            ]
            
            for finding in important_findings[:3]:  # Max 3 per file
                if comment_count >= max_inline_comments:
                    break
                
                line_number = finding.get("line_number")
                if not line_number:
                    continue
                
                comment_body = self.formatter.format_inline_comment(finding, file_path)
                
                try:
                    self.github_client.create_review_comment(
                        self.pr_number,
                        commit_sha,
                        comment_body,
                        file_path,
                        line_number
                    )
                    comment_count += 1
                    print(f"  Posted comment on {file_path}:{line_number}")
                except Exception as e:
                    print(f"  Failed to post comment: {str(e)}")
            
            if comment_count >= max_inline_comments:
                print(f"  Reached max inline comments limit ({max_inline_comments})")
                break
    
    def _post_no_issues_comment(self):
        """Post a comment when no issues are found."""
        comment = self.formatter.format_no_issues_comment()
        self.github_client.create_issue_comment(self.pr_number, comment)


def main():
    """Main entry point."""
    try:
        reviewer = AICodeReviewer()
        exit_code = reviewer.run()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
