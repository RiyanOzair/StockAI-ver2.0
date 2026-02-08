import logging
import os
from pathlib import Path
from colorama import Fore, Style, Back


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console."""
    
    COLORS = {
        'DEBUG': Fore.CYAN + Style.BRIGHT,
        'INFO': Fore.GREEN + Style.BRIGHT,
        'WARNING': Fore.YELLOW + Style.BRIGHT,
        'ERROR': Fore.RED + Style.BRIGHT,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        message = super().format(record)
        if record.levelname in self.COLORS:
            message = self.COLORS[record.levelname] + message + Style.RESET_ALL
        return message


class CustomLogger:
    """Custom logger with file and console handlers."""
    
    def __init__(self):
        # Use absolute path based on this file's location
        log_dir = Path(__file__).parent
        self.log_file = log_dir / 'stockai.log'
        
        # Ensure log directory exists
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('StockAI')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers on reimport
        if self.logger.handlers:
            return
        
        # File handler for persistent logs
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        plain_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(plain_formatter)
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # Less verbose in console
        colored_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(colored_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)


log = CustomLogger()
