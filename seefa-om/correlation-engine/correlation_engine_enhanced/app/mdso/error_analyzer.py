"""MDSO error analyzer with pattern matching"""
import re
import structlog
from typing import List, Dict, Optional
from opentelemetry import trace

from .models import MDSOError

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class MDSOErrorAnalyzer:
    """Analyzes and categorizes MDSO errors"""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
    
    def _load_error_patterns(self) -> Dict[str, str]:
        """Load error patterns from configuration
        
        In production, load from database or config file
        """
        return {
            "DE-1000": r"unable to connect to device",
            "DE-1001": r"authentication failed",
            "DE-1002": r"timeout.*device",
            "DE-1003": r"configuration commit failed",
            "DE-1004": r"invalid.*configuration",
            "DE-1005": r"resource.*not found",
            "DE-1006": r"network.*unreachable",
            "DE-1007": r"permission denied",
            "DE-1008": r"syntax error",
            "DE-1009": r"duplicate.*entry",
            "DE-1010": r"constraint.*violation",
        }
    
    def categorize_error(self, error_text: str) -> Optional[str]:
        """Categorize error using regex patterns"""
        with tracer.start_as_current_span(
            "mdso.categorize_error",
            attributes={"error.length": len(error_text)}
        ) as span:
            error_lower = error_text.lower()
            
            for defect_code, pattern in self.error_patterns.items():
                if re.search(pattern, error_lower, re.IGNORECASE):
                    span.set_attribute("error.defect_code", defect_code)
                    span.set_attribute("error.pattern_matched", pattern)
                    return defect_code
            
            span.set_attribute("error.defect_code", "NEW_ERROR")
            return None
    
    def analyze_errors(self, logs: List[Dict]) -> List[MDSOError]:
        """Analyze and categorize errors from logs"""
        with tracer.start_as_current_span(
            "mdso.analyze_errors",
            attributes={"log_count": len(logs)}
        ) as span:
            errors = []
            
            for log in logs:
                if error_text := log.get("error"):
                    defect_code = self.categorize_error(error_text)
                    
                    error = MDSOError(
                        circuit_id=log.get("circuit_id", "unknown"),
                        resource_id=log.get("resource_id", "unknown"),
                        error_text=error_text[:500],
                        error_code=defect_code,
                        defect_number=defect_code,
                        timestamp=log.get("timestamp"),
                        device_tid=log.get("device_tid"),
                        management_ip=log.get("management_ip"),
                        resource_type=log.get("resource_type"),
                    )
                    errors.append(error)
            
            span.set_attribute("errors.categorized", len(errors))
            
            # Count by defect code
            defect_counts = {}
            for error in errors:
                code = error.defect_number or "UNCATEGORIZED"
                defect_counts[code] = defect_counts.get(code, 0) + 1
            
            for code, count in defect_counts.items():
                span.set_attribute(f"errors.{code}", count)
            
            logger.info(
                "mdso_errors_analyzed",
                total=len(errors),
                defect_counts=defect_counts
            )
            
            return errors
    
    def get_error_summary(self, errors: List[MDSOError]) -> Dict[str, int]:
        """Get summary of errors by defect code"""
        summary = {}
        for error in errors:
            code = error.defect_number or "UNCATEGORIZED"
            summary[code] = summary.get(code, 0) + 1
        return summary
