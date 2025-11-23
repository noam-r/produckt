"""Configuration file loader for security scanner."""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.security.scanner import ScanConfig

from backend.security.models.finding import Severity


class ConfigLoader:
    """Load and parse security scanner configuration files."""
    
    DEFAULT_CONFIG_NAMES = [
        ".security-scan.yaml",
        ".security-scan.yml",
        "security-scan.yaml",
        "security-scan.yml",
    ]
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None, project_root: str = ".") -> Optional["ScanConfig"]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Explicit path to config file (optional)
            project_root: Project root directory to search for default config files
            
        Returns:
            ScanConfig if file found and parsed successfully, None otherwise
        """
        # If explicit path provided, use it
        if config_path:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            return cls._parse_config_file(config_file)
        
        # Search for default config files in project root
        project_path = Path(project_root)
        for config_name in cls.DEFAULT_CONFIG_NAMES:
            config_file = project_path / config_name
            if config_file.exists():
                print(f"Found configuration file: {config_file}")
                return cls._parse_config_file(config_file)
        
        # No config file found
        return None
    
    @classmethod
    def _parse_config_file(cls, config_file: Path) -> "ScanConfig":
        """
        Parse YAML configuration file into ScanConfig.
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            ScanConfig object
            
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        
        if not config_data:
            config_data = {}
        
        # Import here to avoid circular dependency
        from backend.security.scanner import ScanConfig
        
        # Parse configuration sections
        config = ScanConfig()
        
        # Include patterns
        if "include" in config_data:
            include = config_data["include"]
            if isinstance(include, list):
                config.include_patterns = include
            else:
                raise ValueError("'include' must be a list of patterns")
        
        # Exclude patterns
        if "exclude" in config_data:
            exclude = config_data["exclude"]
            if isinstance(exclude, list):
                config.exclude_patterns.extend(exclude)
            else:
                raise ValueError("'exclude' must be a list of patterns")
        
        # Analyzers
        if "analyzers" in config_data:
            analyzers = config_data["analyzers"]
            if isinstance(analyzers, list):
                config.enabled_analyzers = analyzers
            else:
                raise ValueError("'analyzers' must be a list")
        
        # Severity settings
        if "severity" in config_data:
            severity_config = config_data["severity"]
            if isinstance(severity_config, dict):
                if "min_level" in severity_config:
                    min_level = severity_config["min_level"].lower()
                    severity_map = {
                        "info": Severity.INFO,
                        "low": Severity.LOW,
                        "medium": Severity.MEDIUM,
                        "high": Severity.HIGH,
                        "critical": Severity.CRITICAL,
                    }
                    if min_level not in severity_map:
                        raise ValueError(f"Invalid severity level: {min_level}")
                    config.min_severity = severity_map[min_level]
            else:
                raise ValueError("'severity' must be a dictionary")
        
        # Output settings
        if "output" in config_data:
            output_config = config_data["output"]
            if isinstance(output_config, dict):
                if "format" in output_config:
                    format_type = output_config["format"].lower()
                    if format_type not in ["json", "markdown", "html"]:
                        raise ValueError(f"Invalid output format: {format_type}")
                    config.output_format = format_type
                
                if "path" in output_config:
                    config.output_path = output_config["path"]
            else:
                raise ValueError("'output' must be a dictionary")
        
        # Performance settings
        if "performance" in config_data:
            perf_config = config_data["performance"]
            if isinstance(perf_config, dict):
                if "max_workers" in perf_config:
                    max_workers = perf_config["max_workers"]
                    if not isinstance(max_workers, int) or max_workers < 1:
                        raise ValueError("'max_workers' must be a positive integer")
                    config.max_workers = max_workers
                
                if "timeout" in perf_config:
                    timeout = perf_config["timeout"]
                    if not isinstance(timeout, int) or timeout < 1:
                        raise ValueError("'timeout' must be a positive integer")
                    config.timeout_seconds = timeout
                
                if "file_size_limit_mb" in perf_config:
                    limit = perf_config["file_size_limit_mb"]
                    if not isinstance(limit, (int, float)) or limit <= 0:
                        raise ValueError("'file_size_limit_mb' must be a positive number")
                    config.file_size_limit_mb = limit
            else:
                raise ValueError("'performance' must be a dictionary")
        
        return config
    
    @classmethod
    def merge_configs(cls, base_config: "ScanConfig", cli_overrides: Dict[str, Any]) -> "ScanConfig":
        """
        Merge CLI arguments with file-based configuration.
        
        CLI arguments take precedence over file configuration.
        
        Args:
            base_config: Configuration loaded from file
            cli_overrides: Dictionary of CLI argument overrides
            
        Returns:
            Merged ScanConfig
        """
        # Start with base config
        merged = base_config
        
        # Apply CLI overrides
        if "analyzers" in cli_overrides and cli_overrides["analyzers"]:
            merged.enabled_analyzers = cli_overrides["analyzers"]
        
        if "min_severity" in cli_overrides and cli_overrides["min_severity"]:
            merged.min_severity = cli_overrides["min_severity"]
        
        if "output_format" in cli_overrides and cli_overrides["output_format"]:
            merged.output_format = cli_overrides["output_format"]
        
        if "output_path" in cli_overrides and cli_overrides["output_path"]:
            merged.output_path = cli_overrides["output_path"]
        
        if "max_workers" in cli_overrides and cli_overrides["max_workers"]:
            merged.max_workers = cli_overrides["max_workers"]
        
        if "include" in cli_overrides and cli_overrides["include"]:
            merged.include_patterns = cli_overrides["include"]
        
        if "exclude" in cli_overrides and cli_overrides["exclude"]:
            merged.exclude_patterns.extend(cli_overrides["exclude"])
        
        return merged
