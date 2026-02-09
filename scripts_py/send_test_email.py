"""Send a simple hello-world email to a specified address."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path so we can import python_app from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.email_sender import send_email
from python_app.logger import setup_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Send a hello-world test email.")
    parser.add_argument("to_email", help="Recipient email address")
    args = parser.parse_args()

    subject = "Hello World"
    html = "<p>Hello World</p>"
    logger.info(f"Sending hello-world test email to {args.to_email}")
    send_email(args.to_email, subject, html)
    logger.info("Test email sent.")


if __name__ == "__main__":
    main()
