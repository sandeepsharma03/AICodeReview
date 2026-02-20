"""
Review Formatter
Formats review findings into readable comments and summaries.
"""

from typing import List, Dict
from datetime import datetime


class ReviewFormatter:
    """Formats review findings for GitHub comments."""
    
    def __init__(self, config: Dict):
        """
        Initialize review formatter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.comment_settings = config.get("comment_settings", {})
        self.severity_emojis = self.comment_settings.get("severity_emojis", {})
        self.include_suggestions = self.comment_settings.get("include_suggestions", True)
        self.include_code_examples = self.comment_settings.get("include_code_examples", True)
        self.max_comment_length = self.comment_settings.get("max_comment_length", 2000)
    
    def format_finding_comment(self, finding: Dict) -> str:
        """
        Format a single finding as a comment.
        
        Args:
            finding: Finding dictionary
            
        Returns:
            Formatted comment string
        """
        severity = finding.get("severity", "info")
        category = finding.get("category", "code_quality")
        message = finding.get("message", "")
        suggestion = finding.get("suggestion", "")
        code_example = finding.get("code_example", "")
        
        emoji = self.severity_emojis.get(severity, "💡")
        
        comment = f"{emoji} **{severity.upper()}** - {category.replace('_', ' ').title()}\n\n"
        comment += f"{message}\n"
        
        if suggestion and self.include_suggestions:
            comment += f"\n**Suggestion:**\n{suggestion}\n"
        
        if code_example and self.include_code_examples:
            comment += f"\n**Example:**\n```\n{code_example}\n```\n"
        
        comment += f"\n---\n*🤖 AI Code Review*"
        
        # Truncate if too long
        if len(comment) > self.max_comment_length:
            comment = comment[:self.max_comment_length - 50] + "\n\n... (truncated)"
        
        return comment
    
    def format_review_summary(
        self,
        all_findings: Dict[str, List[Dict]],
        pr_info: Dict,
        review_stats: Dict
    ) -> str:
        """
        Format a comprehensive review summary.
        
        Args:
            all_findings: Dictionary mapping file paths to findings
            pr_info: Pull request information
            review_stats: Review statistics
            
        Returns:
            Formatted summary string
        """
        total_files = review_stats.get("total_files_reviewed", 0)
        total_findings = review_stats.get("total_findings", 0)
        review_time = review_stats.get("review_time_seconds", 0)
        
        # Count by severity
        severity_counts = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
            "suggestion": 0
        }
        
        for findings in all_findings.values():
            for finding in findings:
                severity = finding.get("severity", "info")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Build summary
        summary = "## 🤖 AI Code Review Summary\n\n"
        
        # Overview section
        summary += "### 📊 Overview\n"
        summary += f"- **Files Reviewed:** {total_files}\n"
        summary += f"- **Total Findings:** {total_findings}\n"
        summary += f"- **Review Time:** {review_time}s\n"
        summary += "\n"
        
        # Findings breakdown
        if total_findings > 0:
            summary += "### 🔍 Findings Breakdown\n"
            
            if severity_counts["critical"] > 0:
                emoji = self.severity_emojis.get("critical", "🚨")
                summary += f"- {emoji} **Critical:** {severity_counts['critical']}\n"
            
            if severity_counts["error"] > 0:
                emoji = self.severity_emojis.get("error", "❌")
                summary += f"- {emoji} **Errors:** {severity_counts['error']}\n"
            
            if severity_counts["warning"] > 0:
                emoji = self.severity_emojis.get("warning", "⚠️")
                summary += f"- {emoji} **Warnings:** {severity_counts['warning']}\n"
            
            if severity_counts["info"] > 0:
                emoji = self.severity_emojis.get("info", "💡")
                summary += f"- {emoji} **Info:** {severity_counts['info']}\n"
            
            if severity_counts["suggestion"] > 0:
                emoji = self.severity_emojis.get("suggestion", "✨")
                summary += f"- {emoji} **Suggestions:** {severity_counts['suggestion']}\n"
            
            summary += "\n"
        
        # Critical and error details
        if severity_counts["critical"] > 0 or severity_counts["error"] > 0:
            summary += "### 🚨 Issues Requiring Attention\n\n"
            
            for file_path, findings in all_findings.items():
                critical_errors = [
                    f for f in findings 
                    if f.get("severity") in ["critical", "error"]
                ]
                
                if critical_errors:
                    summary += f"**`{file_path}`**\n"
                    
                    for finding in critical_errors[:3]:  # Limit to 3 per file
                        severity = finding.get("severity", "error")
                        emoji = self.severity_emojis.get(severity, "❌")
                        category = finding.get("category", "code_quality")
                        message = finding.get("message", "")
                        
                        summary += f"{emoji} *{category.replace('_', ' ').title()}:* {message}\n"
                    
                    if len(critical_errors) > 3:
                        summary += f"... and {len(critical_errors) - 3} more issues\n"
                    
                    summary += "\n"
        
        # Positive feedback if no major issues
        if severity_counts["critical"] == 0 and severity_counts["error"] == 0:
            summary += "### ✅ Good Work!\n"
            summary += "No critical issues or errors detected. "
            
            if severity_counts["warning"] > 0:
                summary += f"Please review the {severity_counts['warning']} warning(s) above.\n"
            elif severity_counts["suggestion"] > 0:
                summary += f"Consider the {severity_counts['suggestion']} suggestion(s) for potential improvements.\n"
            else:
                summary += "Code looks good!\n"
            
            summary += "\n"
        
        # Files reviewed list
        reviewed_files = review_stats.get("reviewed_files", [])
        if reviewed_files:
            summary += "### 📁 Files Reviewed\n"
            for file_path in sorted(reviewed_files):
                if file_path in all_findings:
                    finding_count = len(all_findings[file_path])
                    summary += f"- `{file_path}` ({finding_count} finding{'s' if finding_count != 1 else ''})\n"
                else:
                    summary += f"- `{file_path}` (✅ no issues)\n"
            summary += "\n"
        
        # Footer
        summary += "---\n"
        summary += f"*Generated by AI Code Review | {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
        summary += "\n"
        summary += "> **Note:** This is an automated review. Please use your judgment and "
        summary += "have human reviewers validate these findings.\n"
        
        return summary
    
    def format_inline_comment(self, finding: Dict, file_path: str) -> str:
        """
        Format a finding as an inline comment for specific line.
        
        Args:
            finding: Finding dictionary
            file_path: File path
            
        Returns:
            Formatted inline comment
        """
        severity = finding.get("severity", "info")
        category = finding.get("category", "code_quality")
        message = finding.get("message", "")
        suggestion = finding.get("suggestion", "")
        
        emoji = self.severity_emojis.get(severity, "💡")
        
        comment = f"{emoji} **{category.replace('_', ' ').title()}**\n\n{message}"
        
        if suggestion and self.include_suggestions:
            comment += f"\n\n💡 **Suggestion:** {suggestion}"
        
        return comment
    
    def format_no_issues_comment(self) -> str:
        """Format a comment when no issues are found."""
        return (
            "## ✅ AI Code Review - No Issues Found\n\n"
            "The AI code review has completed successfully with no issues detected. "
            "Great work! 🎉\n\n"
            "---\n"
            "*🤖 AI Code Review*"
        )
    
    def format_error_comment(self, error_message: str) -> str:
        """
        Format an error comment.
        
        Args:
            error_message: Error message
            
        Returns:
            Formatted error comment
        """
        return (
            "## ⚠️ AI Code Review - Error\n\n"
            f"The AI code review encountered an error:\n\n"
            f"```\n{error_message}\n```\n\n"
            "Please check the workflow logs for more details.\n\n"
            "---\n"
            "*🤖 AI Code Review*"
        )
