"""
Configuration file for DDoS Detection System

Contains all hyperparameters, paths, and settings for the system.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


DEFAULT_CONFIG = {
    # Model Configuration
    'model': {
        'input_dim': 8,  # Number of traffic features
        'state_dim': 32,  # SSM hidden state dimension
        'hidden_dim': 64,  # Feedforward layer dimension
        'num_layers': 2,  # Number of SSM layers
        'dropout': 0.1,  # Dropout probability
        'use_attention': True,  # Use attention pooling
    },
    
    # Training Configuration
    'training': {
        'batch_size': 32,
        'num_epochs': 100,
        'learning_rate': 0.001,
        'weight_decay': 1e-5,
        'early_stopping_patience': 15,
        'gradient_clip_norm': 1.0,
        
        # Loss function
        'use_focal_loss': True,
        'focal_alpha': 0.25,
        'focal_gamma': 2.0,
        
        # Learning rate scheduler
        'scheduler_patience': 5,
        'scheduler_factor': 0.5,
        
        # Data split
        'train_split': 0.7,
        'val_split': 0.15,
        'test_split': 0.15,
        
        # Random seed
        'random_seed': 42,
    },
    
    # Data Configuration
    'data': {
        'sequence_length': 60,  # Number of time steps
        'window_size': 1.0,  # Time window in seconds
        'stride': 1,  # Stride for sliding window
        
        # Feature normalization
        'normalize_features': True,
        'normalization_momentum': 0.99,
        
        # Dataset generation
        'num_normal_sequences': 2000,
        'num_attack_sequences_per_type': 500,
        'include_transitions': True,
    },
    
    # Inference Configuration
    'inference': {
        'detection_threshold': 0.5,
        'confidence_threshold': 0.7,
        'batch_inference': False,
        'use_quantization': False,  # Use quantized model for edge
    },
    
    # Real-time Detection Configuration
    'realtime': {
        'window_size': 1.0,  # Seconds
        'max_packets_per_window': 10000,
        'buffer_size': 60,  # Number of windows to buffer
        'async_processing': True,
        'packet_queue_size': 10000,
        'result_queue_size': 100,
    },
    
    # Dashboard Configuration
    'dashboard': {
        'max_history': 500,  # Maximum data points to display
        'refresh_rate': 2,  # Seconds between updates
        'top_sources': 20,  # Number of top source IPs to show
        'port': 8501,  # Streamlit port
    },
    
    # Paths
    'paths': {
        'data_dir': './data',
        'checkpoint_dir': './checkpoints',
        'log_dir': './logs',
        'output_dir': './outputs',
        'model_save_path': './checkpoints/best_model.pt',
        'normalizer_save_path': './checkpoints/normalizer.npz',
    },
    
    # Logging
    'logging': {
        'level': 'INFO',
        'log_to_file': True,
        'log_to_console': True,
        'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    },
    
    # Edge Deployment
    'edge': {
        'target_device': 'cpu',
        'max_memory_mb': 512,  # Maximum memory usage
        'target_latency_ms': 100,  # Target inference latency
        'enable_model_compression': True,
        'quantization_bits': 8,
    },
    
    # Alert System
    'alerts': {
        'enable_alerts': True,
        'alert_threshold': 0.8,  # Probability threshold for alerts
        'alert_cooldown': 60,  # Seconds between alerts
        'alert_methods': ['console', 'log'],  # 'email', 'webhook' available
    }
}


class Config:
    """Configuration manager."""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize configuration.
        
        Args:
            config_dict: Configuration dictionary (uses defaults if None)
        """
        self.config = DEFAULT_CONFIG.copy()
        if config_dict:
            self._update_config(self.config, config_dict)
        
        # Create necessary directories
        self._create_directories()
    
    def _update_config(self, base: Dict, update: Dict):
        """Recursively update configuration dictionary."""
        for key, value in update.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._update_config(base[key], value)
            else:
                base[key] = value
    
    def _create_directories(self):
        """Create necessary directories."""
        for key, path in self.config['paths'].items():
            if 'dir' in key:
                Path(path).mkdir(parents=True, exist_ok=True)
    
    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Path to config value (e.g., 'model.state_dim')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Path to config value
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self, filepath: str):
        """Save configuration to YAML file."""
        with open(filepath, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'Config':
        """Load configuration from YAML file."""
        with open(filepath, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(config_dict)
    
    def to_dict(self) -> Dict:
        """Get configuration as dictionary."""
        return self.config.copy()
    
    def __repr__(self) -> str:
        return f"Config({yaml.dump(self.config, default_flow_style=False)})"


def create_default_config_file(filepath: str = './config.yaml'):
    """Create default configuration file."""
    config = Config()
    config.save(filepath)
    print(f"Default configuration saved to {filepath}")


if __name__ == "__main__":
    # Create default config file
    create_default_config_file()
    
    # Example usage
    config = Config()
    
    print("Model Configuration:")
    print(f"  State Dimension: {config.get('model.state_dim')}")
    print(f"  Number of Layers: {config.get('model.num_layers')}")
    
    print("\nTraining Configuration:")
    print(f"  Batch Size: {config.get('training.batch_size')}")
    print(f"  Learning Rate: {config.get('training.learning_rate')}")
    
    print("\nPaths:")
    print(f"  Checkpoint Directory: {config.get('paths.checkpoint_dir')}")
