"""
Code Analyzer
Analyzes code changes and prepares them for review.
"""

import os
import re
from typing import List, Dict, Optional, Set
from pathlib import Path, PurePath


class CodeAnalyzer:
    """Analyzes code changes and filters files for review."""
    
    def __init__(self, config: Dict):
        """
        Initialize code analyzer.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.review_settings = config.get("review_settings", {})
        self.file_patterns = self.review_settings.get("file_patterns", {})
        self.language_settings = self.review_settings.get("languages", {})
        self.max_lines_per_file = self.review_settings.get("max_lines_per_file", 500)
        self.max_total_lines = self.review_settings.get("max_total_lines", 2000)
    
    def should_review_file(self, filename: str) -> bool:
        """
        Determine if a file should be reviewed.
        
        Args:
            filename: File path
            
        Returns:
            True if file should be reviewed
        """
        # Normalize path separators for consistent matching
        normalized_path = filename.replace('\\', '/')
        
        # Check exclude patterns first
        exclude_patterns = self.file_patterns.get("exclude", [])
        for pattern in exclude_patterns:
            if self._match_pattern(normalized_path, pattern):
                print(f"      Pattern match: {pattern} (EXCLUDED)")
                return False
        
        # Check include patterns
        include_patterns = self.file_patterns.get("include", [])
        if not include_patterns:
            return True
        
        for pattern in include_patterns:
            if self._match_pattern(normalized_path, pattern):
                print(f"      Pattern match: {pattern} (INCLUDED)")
                return True
        
        print(f"      No pattern matched (NOT INCLUDED)")
        return False
    
    def _match_pattern(self, filepath: str, pattern: str) -> bool:
        """
        Match a file path against a glob pattern.
        Supports ** for recursive directory matching.
        
        Args:
            filepath: File path (forward slashes)
            pattern: Glob pattern
            
        Returns:
            True if pattern matches
        """
        import fnmatch
        
        # Handle ** recursive matching
        if '**' in pattern:
            # Use placeholders to avoid replacement conflicts
            regex_pattern = pattern
            
            # Escape special regex characters
            regex_pattern = regex_pattern.replace('.', r'\.')
            regex_pattern = regex_pattern.replace('+', r'\+')
            regex_pattern = regex_pattern.replace('?', '__QUESTION__')
            
            # Replace ** patterns with placeholders first
            regex_pattern = regex_pattern.replace('**/', '__RECURSIVE_DIR__')
            regex_pattern = regex_pattern.replace('**', '__RECURSIVE_ANY__')
            
            # Replace single * with placeholder
            regex_pattern = regex_pattern.replace('*', '__SINGLE_STAR__')
            
            # Now replace placeholders with actual regex
            regex_pattern = regex_pattern.replace('__RECURSIVE_DIR__', '(.*/)?' )
            regex_pattern = regex_pattern.replace('__RECURSIVE_ANY__', '.*')
            regex_pattern = regex_pattern.replace('__SINGLE_STAR__', '[^/]*')
            regex_pattern = regex_pattern.replace('__QUESTION__', '.')
            
            # Add anchors
            regex_pattern = '^' + regex_pattern + '$'
            
            return bool(re.match(regex_pattern, filepath))
        else:
            # Use fnmatch for simple patterns
            return fnmatch.fnmatch(filepath, pattern)
    
    def get_focus_areas(self, language: str) -> List[str]:
        """
        Get focus areas for a specific language.
        
        Args:
            language: Programming language
            
        Returns:
            List of focus areas
        """
        lang_config = self.language_settings.get(language, {})
        focus_areas = lang_config.get("focus_areas", [])
        
        # Add general review aspects
        general_aspects = self.review_settings.get("review_aspects", [])
        
        return list(set(focus_areas + general_aspects))
    
    def extract_changed_lines(self, patch: str) -> List[Dict[str, any]]:
        """
        Extract changed lines from a patch.
        
        Args:
            patch: Git diff patch
            
        Returns:
            List of changed line information
        """
        if not patch:
            return []
        
        changes = []
        current_line = 0
        
        for line in patch.split("\n"):
            # Parse hunk header
            if line.startswith("@@"):
                match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if match:
                    current_line = int(match.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                # Added line
                changes.append({
                    "line_number": current_line,
                    "type": "addition",
                    "content": line[1:]
                })
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                # Deleted line
                changes.append({
                    "line_number": current_line,
                    "type": "deletion",
                    "content": line[1:]
                })
            else:
                # Context line
                current_line += 1
        
        return changes
    
    def calculate_complexity(self, code: str, language: str) -> Dict[str, any]:
        """
        Calculate basic complexity metrics for code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            Dictionary with complexity metrics
        """
        lines = code.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]
        
        metrics = {
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "complexity_score": 0
        }
        
        if language == "java":
            # Count complexity indicators
            if_count = len(re.findall(r'\bif\s*\(', code))
            for_count = len(re.findall(r'\bfor\s*\(', code))
            while_count = len(re.findall(r'\bwhile\s*\(', code))
            case_count = len(re.findall(r'\bcase\s+', code))
            catch_count = len(re.findall(r'\bcatch\s*\(', code))
            
            metrics["complexity_score"] = if_count + for_count + while_count + case_count + catch_count
            metrics["if_count"] = if_count
            metrics["loop_count"] = for_count + while_count
            metrics["case_count"] = case_count
            metrics["catch_count"] = catch_count
        
        elif language == "python":
            if_count = len(re.findall(r'\bif\s+', code))
            for_count = len(re.findall(r'\bfor\s+', code))
            while_count = len(re.findall(r'\bwhile\s+', code))
            except_count = len(re.findall(r'\bexcept\s*', code))
            
            metrics["complexity_score"] = if_count + for_count + while_count + except_count
            metrics["if_count"] = if_count
            metrics["loop_count"] = for_count + while_count
            metrics["except_count"] = except_count
        
        return metrics
    
    def detect_security_patterns(self, code: str, language: str) -> List[Dict[str, any]]:
        """
        Detect potential security issues in code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            List of potential security issues
        """
        issues = []
        
        if language == "java":
            # SQL injection patterns
            if re.search(r'Statement.*execute(?:Query|Update)?\s*\([^?]*\+|"SELECT.*"\s*\+', code):
                issues.append({
                    "type": "sql_injection",
                    "message": "Potential SQL injection: string concatenation in SQL query"
                })
            
            # Hardcoded credentials
            if re.search(r'(?:API_KEY|PASSWORD|SECRET_TOKEN|AWS_ACCESS_KEY|password|passwd|pwd|DATABASE_URL)\s*=\s*["\'][^"\']{8,}["\']', code, re.IGNORECASE):
                issues.append({
                    "type": "hardcoded_credentials",
                    "message": "Potential hardcoded credentials detected"
                })
            
            # Insecure random
            if re.search(r'new\s+Random\s*\(', code):
                issues.append({
                    "type": "weak_random",
                    "message": "Using java.util.Random for security-sensitive operations; consider SecureRandom"
                })
            
            # Command injection
            if re.search(r'Runtime\.getRuntime\(\)\.exec\(|ProcessBuilder\s*\([^)]*\+', code):
                issues.append({
                    "type": "command_injection",
                    "message": "Potential command injection: unsafe command execution"
                })
            
            # Unsafe deserialization
            if re.search(r'ObjectInputStream.*readObject\(\)', code):
                issues.append({
                    "type": "unsafe_deserialization",
                    "message": "Unsafe deserialization with ObjectInputStream detected"
                })
            
            # Weak crypto
            if re.search(r'MessageDigest\.getInstance\s*\(\s*["\']MD5["\']', code):
                issues.append({
                    "type": "weak_crypto",
                    "message": "Weak cryptography: MD5 is cryptographically broken"
                })
            
            # Resource leaks
            if re.search(r'new\s+File(?:Input|Output)Stream\((?!.*try-with-resources)', code):
                issues.append({
                    "type": "resource_leak",
                    "message": "Potential resource leak: file stream not used with try-with-resources"
                })
        
        elif language == "python":
            # SQL injection patterns
            if re.search(r'execute\s*\([^?]*f["\']|execute\s*\([^?]*%|execute\s*\([^?]*\.format\(', code):
                issues.append({
                    "type": "sql_injection",
                    "message": "Potential SQL injection: string formatting in SQL query"
                })
            
            # Hardcoded credentials
            if re.search(r'(?:API_KEY|PASSWORD|SECRET_TOKEN|AWS_ACCESS_KEY|password|passwd|pwd|secret|token)\s*=\s*["\'][^"\']{8,}["\']', code):
                issues.append({
                    "type": "hardcoded_credentials",
                    "message": "Potential hardcoded credentials detected"
                })
            
            # Unsafe deserialization
            if re.search(r'pickle\.loads?\(', code):
                issues.append({
                    "type": "unsafe_deserialization",
                    "message": "Unsafe deserialization with pickle detected"
                })
            
            # Command injection
            if re.search(r'os\.system\(|subprocess\.call\([^,]*shell\s*=\s*True', code):
                issues.append({
                    "type": "command_injection",
                    "message": "Potential command injection: unsafe system command execution"
                })
            
            # Use of eval
            if re.search(r'\beval\s*\(', code):
                issues.append({
                    "type": "code_injection",
                    "message": "Dangerous use of eval() detected"
                })
        
        return issues
    
    def prioritize_files(self, files: List[Dict]) -> List[Dict]:
        """
        Prioritize files for review based on importance.
        
        Args:
            files: List of file change dictionaries
            
        Returns:
            Sorted list of files by priority
        """
        def priority_score(file_info):
            filename = file_info.get("filename", "")
            changes = file_info.get("changes", 0)
            
            score = 0
            
            # High priority patterns
            if any(pattern in filename for pattern in ["Servlet", "Security", "Auth", "Login"]):
                score += 100
            if filename.endswith(".java") and "src/main" in filename:
                score += 50
            if filename.startswith(".github/workflows"):
                score += 40
            if filename.endswith(".xml") and any(x in filename for x in ["web.xml", "security"]):
                score += 80
            
            # Medium priority
            if filename.endswith((".properties", ".yml", ".yaml")):
                score += 30
            
            # Penalize test files (lower priority)
            if "/test/" in filename or filename.startswith("test/"):
                score -= 50
            
            # Factor in change size (but not too heavily)
            score += min(changes, 100) * 0.1
            
            return score
        
        return sorted(files, key=priority_score, reverse=True)
    
    def chunk_code(self, code: str, max_lines: int = 500) -> List[str]:
        """
        Split code into reviewable chunks.
        
        Args:
            code: Source code
            max_lines: Maximum lines per chunk
            
        Returns:
            List of code chunks
        """
        lines = code.split("\n")
        
        if len(lines) <= max_lines:
            return [code]
        
        chunks = []
        current_chunk = []
        
        for line in lines:
            current_chunk.append(line)
            
            if len(current_chunk) >= max_lines:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks
