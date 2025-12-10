"""Background task implementations for SECA processing"""
from datetime import datetime
import io
import os
import zipfile
import json
import logging
import shutil

logger = logging.getLogger(__name__)


def process_seca_file(tmp_path: str, original_filename: str) -> str:
    """Process the uploaded SECA XLSX file synchronously and return path to zip output.

    The zip will contain the reformatted xlsx, a PDF/text report, and summary.json.
    Caller is responsible for cleanup of the input file.
    """
    try:
        from app.seca_xlsx_processor import SECAXLSXProcessor
        from app.seca_scraper import SECAScraper
    except Exception as e:
        logger.exception("Missing SECA processing modules", exc_info=e)
        raise

    processor = SECAXLSXProcessor(tmp_path)
    processor.load_xlsx()
    processor.parse_circuit_data()

    target_errors = processor.to_dict()

    scraping_error = None
    scraper_results = {}

    try:
        scraper = SECAScraper(headless=True)
        try:
            scraper.initialize_driver()
        except Exception as e:
            scraping_error = f"Failed to init webdriver: {e}"
            scraper = None

        if scraper and scraper.driver:
            try:
                scraper_results = scraper.scrape_product_reports(target_errors)
            except Exception as e:
                scraping_error = f"Error during scraping: {e}"
            finally:
                try:
                    scraper.close_driver()
                except Exception:
                    pass
    except Exception as e:
        scraping_error = f"SECAScraper error: {e}"

    # Merge results
    for ck, sres in (scraper_results or {}).items():
        if ck in processor.errors:
            err_obj = processor.errors[ck]
            try:
                err_obj.traceback = getattr(sres, 'traceback', None)
                err_obj.affected_files = getattr(sres, 'affected_files', None) or []
                err_obj.log_file_path = getattr(sres, 'log_file_path', None)
                err_obj.categorized_error = getattr(sres, 'categorized_error', None)
            except Exception:
                pass

    # Generate reformatted xlsx
    reformatted_path = tmp_path + "-reformatted.xlsx"
    try:
        processor.generate_reformatted_xlsx(reformatted_path)
    except Exception:
        try:
            shutil.copy(tmp_path, reformatted_path)
        except Exception:
            reformatted_path = None

    # Generate PDF report via ReportLab if available, fallback to text
    pdf_path = tmp_path + "-report.pdf"
    try:
        try:
            from app.utils.pdf_report import generate_pdf_summary
            # Pass the developer prompt as requested (could be a constant or configured)
            developer_prompt = (
                "Please help summarize root causes and actionable steps for the following tracebacks."
            )
            # processor.errors is mapping of concat_key -> CircuitError objects
            generate_pdf_summary(processor.to_dict(), pdf_path, developer_prompt)
        except Exception:
            # Fallback to simple text report saved with .txt extension
            pdf_path = tmp_path + "-report.txt"
            with open(pdf_path, 'w', encoding='utf-8') as f:
                f.write(f"SECA Processing Report\nSource: {original_filename}\nProcessed: {datetime.utcnow().isoformat()}Z\n\n")
                if scraping_error:
                    f.write(f"Scraping note: {scraping_error}\n\n")
                for ck, err in processor.errors.items():
                    f.write(f"{ck} | {err.product_name} | {err.service_request_type}\n")
                    f.write((err.traceback or "(no traceback)") + "\n\n")
    except Exception:
        pdf_path = None

    # Create zip
    zip_fd, zip_path = None, None
    try:
        import tempfile
        zip_fd, zip_path = tempfile.mkstemp(suffix='-seca-output.zip')
        os.close(zip_fd)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if reformatted_path and os.path.exists(reformatted_path):
                zf.write(reformatted_path, arcname=os.path.basename(reformatted_path))
            else:
                zf.write(tmp_path, arcname=os.path.basename(tmp_path))

            if pdf_path and os.path.exists(pdf_path):
                zf.write(pdf_path, arcname=os.path.basename(pdf_path))

            summary = {
                'source_filename': original_filename,
                'processed_at': datetime.utcnow().isoformat() + 'Z',
                'total_circuits': len(processor.errors),
                'scraping_error': scraping_error,
            }
            zf.writestr('summary.json', json.dumps(summary, indent=2))

    except Exception as e:
        logger.exception("Failed to build zip", exc_info=e)
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
        raise

    # Cleanup intermediate files, keep zip
    try:
        os.remove(tmp_path)
    except Exception:
        pass
    try:
        if reformatted_path and os.path.exists(reformatted_path):
            os.remove(reformatted_path)
    except Exception:
        pass
    try:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
    except Exception:
        pass

    return zip_path
