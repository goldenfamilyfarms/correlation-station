"""
SECA Web Scraper - Selenium-based error report scraper for 159.56.4.94/reports
"""
import json
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import structlog

logger = structlog.get_logger()


@dataclass
class ScrapedError:
    """Scraped error data"""
    circuit_id: str
    date: str
    concat_key: str
    traceback: Optional[str] = None
    affected_files: List[str] = None
    log_file_path: Optional[str] = None
    categorized_error: Optional[str] = None
    orch_trace_data: Optional[Dict] = None


class SECAScraper:
    """Selenium-based scraper for MDSO error reports"""

    def __init__(self, base_url: str = "http://159.56.4.94/reports", headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.results: Dict[str, ScrapedError] = {}

    def initialize_driver(self):
        """Initialize Selenium WebDriver"""
        logger.info("Initializing Selenium WebDriver", headless=self.headless)

        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Prefer a remote Selenium server if SELENIUM_REMOTE_URL is set
        remote_url = os.getenv("SELENIUM_REMOTE_URL")
        try:
            if remote_url:
                logger.info("Using remote Selenium WebDriver", url=remote_url)
                # Use Remote webdriver for a selenium/standalone-chrome container
                self.driver = webdriver.Remote(command_executor=remote_url, options=options)
            else:
                # Local Chrome (requires chromedriver available in PATH)
                self.driver = webdriver.Chrome(options=options)

            logger.info("WebDriver initialized")
        except Exception as e:
            logger.error("Failed to initialize WebDriver", error=str(e))
            raise

    def close_driver(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

    def scrape_product_reports(self, target_errors: Dict[str, any]) -> Dict[str, ScrapedError]:
        """
        Scrape product reports for matching circuits

        Steps:
        1. Navigate to 159.56.4.94/reports
        2. Find product table at /html/body/section/table/tbody
        3. Click each product link
        4. Search for matching circuit_id + date
        5. Extract traceback and error details
        """
        if not self.driver:
            raise RuntimeError("Must call initialize_driver() first")

        logger.info(
            "Starting report scraping",
            base_url=self.base_url,
            target_count=len(target_errors)
        )

        # Navigate to reports page
        self.driver.get(self.base_url)
        time.sleep(2)

        # Find product table
        try:
            product_table = self.driver.find_element(
                By.XPATH,
                "/html/body/section/table/tbody"
            )
        except NoSuchElementException:
            logger.error("Product table not found")
            return {}

        # Get all product links
        product_rows = product_table.find_elements(By.TAG_NAME, "tr")
        product_links = []

        for row in product_rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if cells:
                link_elem = cells[0].find_element(By.TAG_NAME, "a")
                product_links.append({
                    "name": link_elem.text,
                    "url": link_elem.get_attribute("href")
                })

        logger.info("Found product links", count=len(product_links))

        # Process each product
        for product in product_links:
            logger.info("Processing product", product=product["name"])

            try:
                self._scrape_product(product, target_errors)
            except Exception as e:
                logger.error(
                    "Failed to scrape product",
                    product=product["name"],
                    error=str(e)
                )
                continue

        logger.info("Scraping complete", results_count=len(self.results))

        return self.results

    def _scrape_product(self, product: Dict, target_errors: Dict):
        """Scrape a single product's error reports"""
        # Navigate to product page
        self.driver.get(product["url"])
        time.sleep(1)

        # Find report table
        try:
            report_table = self.driver.find_element(By.TAG_NAME, "tbody")
        except NoSuchElementException:
            logger.warning("No report table found", product=product["name"])
            return

        # Get all report links
        report_rows = report_table.find_elements(By.TAG_NAME, "tr")

        for row in report_rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue

            # Get report link
            try:
                link_elem = cells[0].find_element(By.TAG_NAME, "a")
                report_url = link_elem.get_attribute("href")
                report_name = link_elem.text
            except NoSuchElementException:
                continue

            # Check if this is an orch_trace link
            if "orch_trace" in report_url.lower():
                self._process_orch_trace(report_url, report_name, target_errors)
            else:
                # Regular log file
                self._process_log_file(report_url, report_name, target_errors)

    def _process_orch_trace(self, url: str, name: str, target_errors: Dict):
        """
        Process orchestration trace file

        Steps:
        1. Open orch_trace link
        2. Find first occurrence of FAILED
        3. Extract log_file value
        4. Go back and find matching .txt log file
        5. Extract traceback
        """
        logger.debug("Processing orch_trace", url=url)

        # Navigate to orch_trace
        self.driver.get(url)
        time.sleep(0.5)

        # Get page content
        page_text = self.driver.find_element(By.TAG_NAME, "body").text

        # Parse JSON
        try:
            orch_data = json.loads(page_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse orch_trace JSON", url=url)
            return

        # Find FAILED entry
        log_file_name = None
        failed_entry = None

        if isinstance(orch_data, list):
            for entry in orch_data:
                if entry.get("state") == "FAILED":
                    log_file_name = entry.get("log_file")
                    failed_entry = entry
                    break
        elif isinstance(orch_data, dict):
            if orch_data.get("state") == "FAILED":
                log_file_name = orch_data.get("log_file")
                failed_entry = orch_data

        if not log_file_name:
            logger.debug("No FAILED entry in orch_trace", url=url)
            return

        logger.debug("Found failed log file", log_file=log_file_name)

        # Go back to product page
        self.driver.back()
        time.sleep(0.5)

        # Find matching .txt log file
        try:
            log_link = self.driver.find_element(
                By.LINK_TEXT,
                log_file_name
            )

            log_url = log_link.get_attribute("href")

            # Process the log file
            self._extract_from_log_file(log_url, target_errors, failed_entry)

        except NoSuchElementException:
            logger.warning("Log file link not found", log_file=log_file_name)

        # Go back to product page
        self.driver.back()
        time.sleep(0.5)

    def _process_log_file(self, url: str, name: str, target_errors: Dict):
        """Process regular .txt log file"""
        self._extract_from_log_file(url, target_errors)

    def _extract_from_log_file(
        self,
        url: str,
        target_errors: Dict,
        orch_entry: Optional[Dict] = None
    ):
        """
        Extract traceback from log file and match to target errors

        Regex pattern for traceback:
        Traceback (most recent call last):
          File "/path/to/file.py", line 434, in run
            response = self.process()
        Exception: Unable to connect to device at DEVICE.FQDN.COM
        """
        logger.debug("Extracting from log file", url=url)

        # Navigate to log file
        self.driver.get(url)
        time.sleep(0.5)

        # Get log content
        log_text = self.driver.find_element(By.TAG_NAME, "pre").text

        # Extract traceback
        traceback = self._extract_traceback(log_text)

        if not traceback:
            logger.debug("No traceback found", url=url)
            # Go back
            self.driver.back()
            time.sleep(0.5)
            return

        logger.debug("Found traceback", length=len(traceback))

        # Extract affected files from traceback
        affected_files = self._extract_files_from_traceback(traceback)

        # Extract error message
        error_msg = self._extract_error_message(traceback)

        # Try to match to target errors
        # Look for circuit ID in traceback or log text
        circuit_pattern = r'\b\d{2}\.[A-Z0-9]{4}\.\d{6}\.\.[A-Z]{0,4}\b'
        circuits_in_log = re.findall(circuit_pattern, log_text)

        for circuit_id in circuits_in_log:
            # Find matching error in target_errors
            for concat_key, error_data in target_errors.items():
                if error_data.get("circuit_id") == circuit_id:
                    # Match found!
                    logger.info(
                        "Matched error to circuit",
                        circuit_id=circuit_id,
                        concat_key=concat_key
                    )

                    # Store result
                    self.results[concat_key] = ScrapedError(
                        circuit_id=circuit_id,
                        date=error_data.get("date", ""),
                        concat_key=concat_key,
                        traceback=traceback,
                        affected_files=affected_files,
                        log_file_path=url,
                        categorized_error=error_msg,
                        orch_trace_data=orch_entry
                    )

        # Go back
        self.driver.back()
        time.sleep(0.5)

    @staticmethod
    def _extract_traceback(text: str) -> Optional[str]:
        """Extract Python traceback from text"""
        pattern = r'(Traceback \(most recent call last\):.*?(?:Exception|Error): .+?)(?:\n\n|\n\d{4}-\d{2}-\d{2}|$)'
        match = re.search(pattern, text, re.DOTALL)

        if match:
            return match.group(1).strip()

        return None

    @staticmethod
    def _extract_files_from_traceback(traceback: str) -> List[str]:
        """Extract file paths from traceback"""
        file_pattern = r'File "([^"]+)"'
        files = re.findall(file_pattern, traceback)
        return list(set(files))

    @staticmethod
    def _extract_error_message(traceback: str) -> str:
        """Extract error message (last line of traceback)"""
        lines = traceback.strip().split("\n")

        if lines:
            return lines[-1].strip()

        return ""
