import argparse
import logging

from .config import load_config
from .sync_engine import SyncEngine

def main():
    """
    The main entry point for the tool_sync application.
    """
    parser = argparse.ArgumentParser(description="A bidirectional synchronization tool for Azure DevOps.")
    parser.add_argument(
        "command",
        choices=["sync"],
        help="The command to execute."
    )
    parser.add_argument(
        "--config",
        default="config.yml",
        help="The path to the configuration file."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="The logging level to use."
    )
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    if args.command == "sync":
        try:
            logger.info(f"Loading configuration from {args.config}...")
            config = load_config(args.config)

            logger.info("Initializing sync engine...")
            engine = SyncEngine(config)

            engine.run()

        except FileNotFoundError:
            logger.error(f"Configuration file not found at {args.config}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()
