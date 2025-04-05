import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import yaml

class Logger:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.config = self._load_config()
        self.logger = self._setup_logger()
    
    def _load_config(self) -> dict:
        """Carga la configuración desde config.yaml"""
        try:
            with open("config.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config['logging']
        except Exception as e:
            # Configuración por defecto si hay error
            return {
                'level': 'INFO',
                'base_dir': 'logs',
                'date_format': '%Y-%m-%d %H:%M:%S',
                'rotation': 7,
                'max_size': 10
            }
    
    def _setup_logger(self) -> logging.Logger:
        """Configura y retorna un logger"""
        logger = logging.getLogger(self.module_name)
        logger.setLevel(getattr(logging, self.config['level']))
        
        # Crear directorios si no existen
        log_dirs = {
            'general': os.path.join(self.config['base_dir'], 'general'),
            'error': os.path.join(self.config['base_dir'], 'errors'),
            'debug': os.path.join(self.config['base_dir'], 'debug')
        }
        
        for dir_path in log_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # Formato común para todos los handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt=self.config['date_format']
        )
        
        # Handler para logs generales
        general_handler = RotatingFileHandler(
            os.path.join(log_dirs['general'], f'{self.module_name}.log'),
            maxBytes=self.config['max_size'] * 1024 * 1024,
            backupCount=self.config['rotation']
        )
        general_handler.setLevel(logging.INFO)
        general_handler.setFormatter(formatter)
        
        # Handler para errores
        error_handler = RotatingFileHandler(
            os.path.join(log_dirs['error'], f'{self.module_name}_error.log'),
            maxBytes=self.config['max_size'] * 1024 * 1024,
            backupCount=self.config['rotation']
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Handler para debug
        debug_handler = RotatingFileHandler(
            os.path.join(log_dirs['debug'], f'{self.module_name}_debug.log'),
            maxBytes=self.config['max_size'] * 1024 * 1024,
            backupCount=self.config['rotation']
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Agregar handlers al logger
        logger.addHandler(general_handler)
        logger.addHandler(error_handler)
        logger.addHandler(debug_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log an info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log an error message"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log a critical message"""
        self.logger.critical(message) 