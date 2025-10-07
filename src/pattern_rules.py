"""
Pattern-based section assignment rules for batch file mapping.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import re
import fnmatch
import logging


@dataclass
class PatternRule:
    """Represents a pattern-based section assignment rule."""
    pattern: str  # Pattern string (regex or wildcard)
    section_number: str
    description: str = ""  # Optional description of what this rule matches
    priority: int = 0  # Higher priority rules override lower ones
    is_regex: bool = True  # True for regex, False for wildcard
    is_active: bool = True  # Can temporarily disable rules
    
    def matches(self, filename: str) -> bool:
        """Check if filename matches this pattern rule."""
        if not self.is_active:
            return False
            
        try:
            if self.is_regex:
                # Use regex matching
                pattern = re.compile(self.pattern, re.IGNORECASE)
                return pattern.match(filename) is not None
            else:
                # Use simple wildcard matching
                return fnmatch.fnmatch(filename.lower(), self.pattern.lower())
        except (re.error, Exception) as e:
            logging.warning(f"Pattern matching error for '{self.pattern}': {e}")
            return False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern": self.pattern,
            "section_number": self.section_number,
            "description": self.description,
            "priority": self.priority,
            "is_regex": self.is_regex,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PatternRule':
        """Create from dictionary."""
        return cls(
            pattern=data["pattern"],
            section_number=data["section_number"],
            description=data.get("description", ""),
            priority=data.get("priority", 0),
            is_regex=data.get("is_regex", True),
            is_active=data.get("is_active", True)
        )


class PatternRuleManager:
    """Manages pattern rules and their application to file mappings."""
    
    def __init__(self):
        self.rules: List[PatternRule] = []
    
    def add_rule(self, rule: PatternRule) -> bool:
        """Add a new pattern rule."""
        # Check for duplicate patterns
        for existing in self.rules:
            if existing.pattern == rule.pattern:
                logging.warning(f"Pattern rule '{rule.pattern}' already exists")
                return False
        
        self.rules.append(rule)
        self.sort_rules()
        return True
    
    def remove_rule(self, pattern: str) -> bool:
        """Remove a pattern rule by pattern string."""
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.pattern != pattern]
        return len(self.rules) < original_count
    
    def update_rule(self, old_pattern: str, new_rule: PatternRule) -> bool:
        """Update an existing pattern rule."""
        for i, rule in enumerate(self.rules):
            if rule.pattern == old_pattern:
                self.rules[i] = new_rule
                self.sort_rules()
                return True
        return False
    
    def sort_rules(self):
        """Sort rules by priority (highest first)."""
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def find_matching_rule(self, filename: str) -> Optional[PatternRule]:
        """Find the highest priority rule that matches the filename."""
        for rule in self.rules:
            if rule.matches(filename):
                return rule
        return None
    
    def preview_matches(self, pattern: str, filenames: List[str], 
                       is_regex: bool = True) -> List[str]:
        """Preview which files would match a pattern."""
        temp_rule = PatternRule(pattern, "", is_regex=is_regex)
        return [f for f in filenames if temp_rule.matches(f)]
    
    def apply_rules_to_mappings(self, file_mappings: List, 
                               override_existing: bool = False) -> Dict[str, int]:
        """
        Apply pattern rules to file mappings.
        
        Args:
            file_mappings: List of FileMapping objects
            override_existing: If True, override existing section assignments
            
        Returns:
            Dictionary with counts: applied, skipped, failed
        """
        counts = {"applied": 0, "skipped": 0, "failed": 0}
        
        for mapping in file_mappings:
            # Skip ignored files
            if mapping.ignore:
                counts["skipped"] += 1
                continue
            
            # Skip if already has section and not overriding
            if mapping.section_number and not override_existing:
                counts["skipped"] += 1
                continue
            
            # Find matching rule
            rule = self.find_matching_rule(mapping.filename)
            if rule:
                old_section = mapping.section_number
                mapping.section_number = rule.section_number
                
                if old_section != rule.section_number:
                    counts["applied"] += 1
                    logging.info(f"Applied rule '{rule.pattern}' to {mapping.filename} "
                               f"-> Section {rule.section_number}")
                else:
                    counts["skipped"] += 1
            else:
                counts["skipped"] += 1
        
        return counts
    
    def validate_pattern(self, pattern: str, is_regex: bool = True) -> Tuple[bool, str]:
        """
        Validate a pattern string.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not pattern:
            return False, "Pattern cannot be empty"
        
        if is_regex:
            try:
                re.compile(pattern)
                return True, ""
            except re.error as e:
                return False, f"Invalid regex pattern: {e}"
        else:
            # Wildcard patterns are generally always valid
            return True, ""
    
    def get_rule_statistics(self, file_mappings: List) -> Dict[str, Dict]:
        """Get statistics about rule usage and coverage."""
        stats = {}
        
        for rule in self.rules:
            matching_files = []
            for mapping in file_mappings:
                if not mapping.ignore and rule.matches(mapping.filename):
                    matching_files.append(mapping.filename)
            
            stats[rule.pattern] = {
                "section": rule.section_number,
                "priority": rule.priority,
                "matches": len(matching_files),
                "files": matching_files[:10],  # First 10 matches for preview
                "has_more": len(matching_files) > 10
            }
        
        return stats
    
    def export_rules(self) -> List[Dict]:
        """Export rules as list of dictionaries."""
        return [rule.to_dict() for rule in self.rules]
    
    def import_rules(self, rules_data: List[Dict]):
        """Import rules from list of dictionaries."""
        self.rules.clear()
        for rule_data in rules_data:
            try:
                rule = PatternRule.from_dict(rule_data)
                self.rules.append(rule)
            except Exception as e:
                logging.error(f"Failed to import rule: {e}")
        
        self.sort_rules()


# Common pattern templates for user convenience
PATTERN_TEMPLATES = [
    {
        "name": "Files starting with prefix",
        "pattern": r"^f.*",
        "example": "Examples: ^f.* (starts with f), ^fslb.* (starts with fslb)",
        "is_regex": True
    },
    {
        "name": "Files ending with suffix",
        "pattern": r".*_ae$",
        "example": "Examples: .*_ae$ (ends with _ae), .*01$ (ends with 01)",
        "is_regex": True
    },
    {
        "name": "Files containing text",
        "pattern": r".*adverse.*",
        "example": "Examples: .*adverse.* (contains 'adverse'), .*01.* (contains '01')",
        "is_regex": True
    },
    {
        "name": "Numbered sequence",
        "pattern": r"^[a-z]+\d{2}[a-z]?$",
        "example": "Matches fslb01a, tsid02b, dmdd03",
        "is_regex": True
    },
    {
        "name": "Category prefixes",
        "pattern": r"^(ae|cm|dm|ex).*",
        "example": "Matches ae01, cm02, dm03, ex04",
        "is_regex": True
    },
    {
        "name": "Wildcard pattern",
        "pattern": "fslb*",
        "example": "fslb* matches fslb01, fslb_test",
        "is_regex": False
    },
    {
        "name": "Multiple wildcards",
        "pattern": "*_v*_final",
        "example": "Matches report_v1_final, data_v2_final",
        "is_regex": False
    }
]


def create_pattern_from_files(filenames: List[str]) -> Optional[str]:
    """
    Attempt to create a pattern from a list of similar filenames.

    Args:
        filenames: List of filenames to analyze

    Returns:
        Suggested pattern string or None if no pattern found
    """
    if not filenames:
        return None

    if len(filenames) == 1:
        # Single file - return exact match
        return f"^{re.escape(filenames[0])}$"

    # Find common prefix
    prefix = ""
    if all(filenames):
        for i, char in enumerate(filenames[0]):
            if all(len(f) > i and f[i] == char for f in filenames):
                prefix += char
            else:
                break

    # Find common suffix
    suffix = ""
    reversed_files = [f[::-1] for f in filenames]
    if all(reversed_files):
        for i, char in enumerate(reversed_files[0]):
            if all(len(f) > i and f[i] == char for f in reversed_files):
                suffix = char + suffix
            else:
                break

    # Build pattern based on what we found
    if len(prefix) >= 2:  # Meaningful prefix (lowered from 3 to 2)
        if suffix and len(suffix) >= 2:
            return f"^{re.escape(prefix)}.*{re.escape(suffix)}$"
        else:
            # Just use prefix - this is the most flexible approach
            return f"^{re.escape(prefix)}.*"
    elif suffix and len(suffix) >= 2:  # Meaningful suffix
        return f".*{re.escape(suffix)}$"
    else:
        # No common prefix or suffix - try pattern matching as fallback
        # This will match all selected files exactly
        escaped_names = [re.escape(f) for f in filenames]
        return f"^({'|'.join(escaped_names)})$"
