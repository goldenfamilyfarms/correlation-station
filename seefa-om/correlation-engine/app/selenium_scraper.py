"""
Selenium-based scraper for MDSO error reports
Navigates http://159.56.4.94/reports to extract tracebacks
"""
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import structlog

logger = structlog.get_logger()


@dataclass
class ScrapedError:
    circuit_id: str
    date: str
    traceback: Optional[str]
    log_file: Optional[str]
    categorized_error: Optional[str]
    affected_files: List[str]


class MDSOReportScraper:
    """Scrape MDSO error reports using Selenium"""

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

    def navigate_to_reports(self):
        """Navigate to reports page"""
        if not self.driver:
            raise RuntimeError("Driver not started")

        self.driver.get(self.base_url)
        logger.info("Navigated to reports page", url=self.base_url)

        # Wait for table to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//body/section/table/tbody"))
        )

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

    def download_log_file(self, report_url: str) -> Optional[str]:
        """
        Navigate to report URL and download .txt log file
        
        Returns: Log file content as string
        """
        if not self.driver:
            raise RuntimeError("Driver not started")

        try:
            self.driver.get(report_url)
            logger.info("Navigated to report", url=report_url)

            # Wait for page to load
            time.sleep(2)

            # Find .txt download link
            txt_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.txt')]")

            if not txt_links:
                logger.warning("No .txt log file found", url=report_url)
                return None

            # Click first .txt link
            txt_link = txt_links[0]
            txt_url = txt_link.get_attribute("href")

            logger.info("Downloading log file", url=txt_url)

            # Navigate to .txt file (will display in browser)
            self.driver.get(txt_url)
            time.sleep(1)

            # Get page source (the .txt content)
            log_content = self.driver.find_element(By.TAG_NAME, "body").text

            logger.info("Log file downloaded", size=len(log_content))
            return log_content

        except Exception as e:
            logger.error("Error downloading log file", url=report_url, error=str(e))
            return None

    def extract_traceback_from_log(self, log_content: str) -> Optional[str]:
        """Extract Python traceback from log content"""
        traceback_pattern = r'(Traceback \(most recent call last\):.*?(?:Exception|Error): .+?)(?:\n\n|\n\d{4}-\d{2}-\d{2}|$)'

        match = re.search(traceback_pattern, log_content, re.DOTALL)

        if match:
            return match.group(1).strip()

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
        Scrape error details for a specific circuit
        
        Args:
            circuit_id: Circuit ID (e.g., "33.L1XX.801233..TWCC")
            date: Date string (e.g., "2025-12-10_01-59-32")
        
        Returns:
            ScrapedError object or None if not found
        """
        if not self.driver:
            self.start_driver()

        try:
            # Navigate to reports page
            self.navigate_to_reports()

            # Find matching report
            report_url = self.find_matching_report(circuit_id, date)
            if not report_url:
                return None

            # Download log file
            log_content = self.download_log_file(report_url)
            if not log_content:
                return None

            # Extract traceback
            traceback = self.extract_traceback_from_log(log_content)
            if not traceback:
                logger.warning("No traceback found in log", circuit_id=circuit_id)
                return ScrapedError(
                    circuit_id=circuit_id,
                    date=date,
                    traceback=None,
                    log_file=report_url,
                    categorized_error="MDSO | Unknown Error",
                    affected_files=[]
                )

            # Extract affected files
            affected_files = self.extract_affected_files(traceback)

            # Categorize error
            categorized_error = self.categorize_error(traceback)

            return ScrapedError(
                circuit_id=circuit_id,
                date=date,
                traceback=traceback,
                log_file=report_url,
                categorized_error=categorized_error,
                affected_files=affected_files
            )

        except Exception as e:
            logger.error("Error scraping circuit", circuit_id=circuit_id, error=str(e))
            return None

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

            # Small delay between requests
            time.sleep(1)

        logger.info("Scraping complete", total=len(circuit_list), successful=len(results))
        return results
