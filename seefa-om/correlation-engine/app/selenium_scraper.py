"""
Selenium-based scraper for MDSO error reports with orch_trace support
Navigates http://159.56.4.94/reports to extract tracebacks

Blueprint Section 4.2 & 4.3 Compliance:
- Standard log file scraping
- Special orch_trace handling (find FAILED, extract log_file, get traceback)
- Structured status tracking (ok, artifact_not_found, traceback_not_found, error)
"""
import re
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import structlog

logger = structlog.get_logger()


@dataclass
class AffectedFileResult:
    """
    Detailed information about a scraped file
    (Blueprint Section 4.4 - structured output)
    """
    source: str  # "orch_trace" or "other_log"
    log_file: Optional[str]  # filename or path
    traceback: Optional[str]  # full extracted traceback
    artifact_url: Optional[str]  # URL used by Selenium
    selenium_status: str  # "ok", "artifact_not_found", "traceback_not_found", "error"


@dataclass
class ScrapedError:
    """Legacy format for backward compatibility"""
    circuit_id: str
    date: str
    traceback: Optional[str]
    log_file: Optional[str]
    categorized_error: Optional[str]
    affected_files: List[AffectedFileResult]  # Now uses structured format


class MDSOReportScraper:
    """
    Scrape MDSO error reports using Selenium

    Blueprint Compliance:
    - Section 4.2: Standard Selenium scraping with robustness improvements
    - Section 4.3: Special orch_trace handling (FAILED detection, log_file extraction)
    - Section 4.4: Structured output format
    """

    def __init__(self, base_url: str = "http://159.56.4.94/reports", headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def __enter__(self):
        self.start_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_driver()

    def start_driver(self):
        """Initialize Chrome WebDriver"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')

        self.driver = webdriver.Chrome(options=options)
        logger.info("Selenium driver started", headless=self.headless)

    def close_driver(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("Selenium driver closed")

    def navigate_to_reports(self, timeout: int = 10):
        """
        Navigate to reports page with timeout handling
        (Blueprint 4.2: Robustness for slow loads)
        """
        if not self.driver:
            raise RuntimeError("Driver not started")

        try:
            self.driver.get(self.base_url)
            logger.info("Navigated to reports page", url=self.base_url)

            # Wait for table to load
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, "//body/section/table/tbody"))
            )
        except TimeoutException:
            logger.error("Timeout waiting for reports page", url=self.base_url, timeout=timeout)
            raise

    def find_matching_report(self, circuit_id: str, date: str) -> Optional[str]:
        """
        Find report link matching circuit_id and date

        Returns: URL of matching report or None
        """
        if not self.driver:
            raise RuntimeError("Driver not started")

        try:
            # Find all rows in report table
            tbody = self.driver.find_element(By.XPATH, "//body/section/table/tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")

            logger.info("Searching for matching report", circuit_id=circuit_id, date=date, total_rows=len(rows))

            for row in rows:
                try:
                    # Extract circuit ID and date from row
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 2:
                        continue

                    row_circuit = cells[0].text.strip()
                    row_date = cells[1].text.strip()

                    # Check for match
                    if circuit_id in row_circuit and date in row_date:
                        # Find link in row
                        link = row.find_element(By.TAG_NAME, "a")
                        href = link.get_attribute("href")

                        logger.info("Found matching report", circuit_id=circuit_id, href=href)
                        return href

                except NoSuchElementException:
                    continue

            logger.warning("No matching report found", circuit_id=circuit_id, date=date)
            return None

        except Exception as e:
            logger.error("Error finding report", circuit_id=circuit_id, error=str(e))
            return None

    def find_artifact_links(self, report_url: str) -> Dict[str, List[str]]:
        """
        Navigate to report and find all artifact links

        Returns: {"txt": [...], "orch_trace": [...], "other": [...]}
        (Blueprint 4.3: Detect orch_trace links)
        """
        if not self.driver:
            raise RuntimeError("Driver not started")

        try:
            self.driver.get(report_url)
            logger.info("Navigated to report", url=report_url)

            # Wait for page to load
            time.sleep(2)

            # Find all links
            all_links = self.driver.find_elements(By.TAG_NAME, "a")

            artifacts = {
                "txt": [],
                "orch_trace": [],
                "other": []
            }

            for link in all_links:
                href = link.get_attribute("href")
                if not href:
                    continue

                # Blueprint 4.3: Detect orch_trace links
                if "orch_trace" in href.lower():
                    artifacts["orch_trace"].append(href)
                elif href.endswith(".txt"):
                    artifacts["txt"].append(href)
                else:
                    artifacts["other"].append(href)

            logger.info(
                "Found artifacts",
                url=report_url,
                txt_count=len(artifacts["txt"]),
                orch_trace_count=len(artifacts["orch_trace"]),
                other_count=len(artifacts["other"])
            )

            return artifacts

        except Exception as e:
            logger.error("Error finding artifacts", url=report_url, error=str(e))
            return {"txt": [], "orch_trace": [], "other": []}

    def download_log_file(self, log_url: str) -> Optional[str]:
        """
        Download .txt log file content

        Returns: Log file content as string or None
        (Blueprint 4.2: Robustness for missing artifacts)
        """
        if not self.driver:
            raise RuntimeError("Driver not started")

        try:
            logger.info("Downloading log file", url=log_url)

            # Navigate to .txt file (will display in browser)
            self.driver.get(log_url)
            time.sleep(1)

            # Get page source (the .txt content)
            log_content = self.driver.find_element(By.TAG_NAME, "body").text

            logger.info("Log file downloaded", url=log_url, size=len(log_content))
            return log_content

        except Exception as e:
            logger.error("Error downloading log file", url=log_url, error=str(e))
            return None

    def extract_traceback_from_log(self, log_content: str) -> Optional[str]:
        """
        Extract Python traceback from log content

        Pattern: Traceback (most recent call last): ... Exception: ...
        """
        traceback_pattern = r'(Traceback \(most recent call last\):.*?(?:Exception|Error): .+?)(?:\n\n|\n\d{4}-\d{2}-\d{2}|$)'

        match = re.search(traceback_pattern, log_content, re.DOTALL)

        if match:
            return match.group(1).strip()

        return None

    def extract_failed_from_orch_trace(self, orch_trace_content: str) -> Optional[Dict]:
        """
        Extract first FAILED occurrence from orch_trace JSON/text

        Blueprint Section 4.3: Find FAILED, capture log_file

        Returns: {"state": "FAILED", "log_file": "...", ...} or None
        """
        try:
            # Try to parse as JSON first
            orch_data = json.loads(orch_trace_content)

            # Handle list of trace entries
            if isinstance(orch_data, list):
                for entry in orch_data:
                    if isinstance(entry, dict) and entry.get("state") == "FAILED":
                        return entry

            # Handle single dict
            if isinstance(orch_data, dict) and orch_data.get("state") == "FAILED":
                return orch_data

        except json.JSONDecodeError:
            # If not JSON, try to parse as text
            # Look for "state": "FAILED" pattern
            failed_pattern = r'"state"\s*:\s*"FAILED".*?"log_file"\s*:\s*"([^"]+)"'
            match = re.search(failed_pattern, orch_trace_content, re.DOTALL)

            if match:
                return {"state": "FAILED", "log_file": match.group(1)}

        logger.warning("No FAILED occurrence found in orch_trace")
        return None

    def extract_affected_files(self, traceback: str) -> List[str]:
        """Extract file paths from traceback"""
        file_pattern = r'File "([^"]+)"'
        files = re.findall(file_pattern, traceback)

        return list(set(files))

    def categorize_error(self, traceback: str) -> str:
        """Categorize error based on traceback content"""
        if "Unable to connect to device" in traceback:
            return "MDSO | Device Connectivity"
        elif "Timeout" in traceback or "timeout" in traceback:
            return "MDSO | Timeout"
        elif "Permission denied" in traceback or "Unauthorized" in traceback:
            return "MDSO | Authentication"
        elif "KeyError" in traceback or "AttributeError" in traceback:
            return "MDSO | Data Error"
        elif "ConnectionError" in traceback or "ConnectionRefusedError" in traceback:
            return "MDSO | Network Error"
        else:
            return "MDSO | Process Error"

    def scrape_circuit_error(self, circuit_id: str, date: str) -> Optional[ScrapedError]:
        """
        Scrape error details for a specific circuit with orch_trace support

        Blueprint Compliance:
        - Section 4.2: Standard scraping with robustness
        - Section 4.3: Special orch_trace handling
        - Section 4.4: Structured output format

        Args:
            circuit_id: Circuit ID (e.g., "33.L1XX.801233..TWCC")
            date: Date string (e.g., "2025-12-10_01-59-32")

        Returns:
            ScrapedError object with structured affected_files or None
        """
        if not self.driver:
            self.start_driver()

        try:
            # Navigate to reports page
            self.navigate_to_reports()

            # Find matching report
            report_url = self.find_matching_report(circuit_id, date)
            if not report_url:
                return ScrapedError(
                    circuit_id=circuit_id,
                    date=date,
                    traceback=None,
                    log_file=None,
                    categorized_error="MDSO | Report Not Found",
                    affected_files=[AffectedFileResult(
                        source="other_log",
                        log_file=None,
                        traceback=None,
                        artifact_url=None,
                        selenium_status="artifact_not_found"
                    )]
                )

            # Find all artifact links (standard .txt and orch_trace)
            artifacts = self.find_artifact_links(report_url)

            affected_files = []
            main_traceback = None
            categorized_error = "MDSO | Unknown Error"

            # Process regular .txt files
            for txt_url in artifacts["txt"]:
                log_content = self.download_log_file(txt_url)

                if not log_content:
                    affected_files.append(AffectedFileResult(
                        source="other_log",
                        log_file=txt_url.split("/")[-1],
                        traceback=None,
                        artifact_url=txt_url,
                        selenium_status="artifact_not_found"
                    ))
                    continue

                traceback = self.extract_traceback_from_log(log_content)

                if traceback:
                    if not main_traceback:
                        main_traceback = traceback
                        categorized_error = self.categorize_error(traceback)

                    affected_files.append(AffectedFileResult(
                        source="other_log",
                        log_file=txt_url.split("/")[-1],
                        traceback=traceback,
                        artifact_url=txt_url,
                        selenium_status="ok"
                    ))
                else:
                    affected_files.append(AffectedFileResult(
                        source="other_log",
                        log_file=txt_url.split("/")[-1],
                        traceback=None,
                        artifact_url=txt_url,
                        selenium_status="traceback_not_found"
                    ))

            # BLUEPRINT 4.3: Process orch_trace files
            for orch_url in artifacts["orch_trace"]:
                orch_content = self.download_log_file(orch_url)

                if not orch_content:
                    affected_files.append(AffectedFileResult(
                        source="orch_trace",
                        log_file=None,
                        traceback=None,
                        artifact_url=orch_url,
                        selenium_status="artifact_not_found"
                    ))
                    continue

                # Extract FAILED occurrence
                failed_entry = self.extract_failed_from_orch_trace(orch_content)

                if failed_entry:
                    log_file = failed_entry.get("log_file")

                    # Try to extract traceback from orch_trace content
                    traceback = self.extract_traceback_from_log(orch_content)

                    if traceback:
                        if not main_traceback:
                            main_traceback = traceback
                            categorized_error = self.categorize_error(traceback)

                        affected_files.append(AffectedFileResult(
                            source="orch_trace",
                            log_file=log_file,
                            traceback=traceback,
                            artifact_url=orch_url,
                            selenium_status="ok"
                        ))
                    else:
                        affected_files.append(AffectedFileResult(
                            source="orch_trace",
                            log_file=log_file,
                            traceback=None,
                            artifact_url=orch_url,
                            selenium_status="traceback_not_found"
                        ))
                else:
                    affected_files.append(AffectedFileResult(
                        source="orch_trace",
                        log_file=None,
                        traceback=None,
                        artifact_url=orch_url,
                        selenium_status="error"
                    ))

            return ScrapedError(
                circuit_id=circuit_id,
                date=date,
                traceback=main_traceback,
                log_file=report_url,
                categorized_error=categorized_error,
                affected_files=affected_files
            )

        except Exception as e:
            logger.error("Error scraping circuit", circuit_id=circuit_id, error=str(e))
            return ScrapedError(
                circuit_id=circuit_id,
                date=date,
                traceback=None,
                log_file=None,
                categorized_error="MDSO | Scraping Error",
                affected_files=[AffectedFileResult(
                    source="other_log",
                    log_file=None,
                    traceback=None,
                    artifact_url=None,
                    selenium_status="error"
                )]
            )

    def scrape_multiple_circuits(self, circuit_list: List[Tuple[str, str]]) -> Dict[str, ScrapedError]:
        """
        Scrape multiple circuits

        Args:
            circuit_list: List of (circuit_id, date) tuples

        Returns:
            Dictionary mapping concat_key to ScrapedError
        """
        results = {}

        for circuit_id, date in circuit_list:
            concat_key = f"{circuit_id}_{date}"
            logger.info("Scraping circuit", circuit_id=circuit_id, date=date)

            scraped = self.scrape_circuit_error(circuit_id, date)
            if scraped:
                results[concat_key] = scraped

            # Small delay between requests to avoid overwhelming server
            time.sleep(1)

        logger.info("Scraping complete", total=len(circuit_list), successful=len(results))
        return results
