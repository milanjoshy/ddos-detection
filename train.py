"""
Main Training Script for DDoS Detection System

Complete training pipeline from data generation to model evaluation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from torch.utils.data import DataLoader, TensorDataset, random_split
import numpy as np
import argparse
from pathlib import Path
import json

from ssm_model import DDoSDetector
from trainer import DDoSTrainer, MetricsCalculator
from generate_dataset import TrafficGenerator
from feature_extraction import FeatureNormalizer
from config import Config


def setup_seed(seed):
    """Set random seeds for reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)


def prepare_data(config: Config):
    """Prepare training, validation, and test data."""
    print("\n" + "="*80)
    print("DATA PREPARATION")
    print("="*80)
    
    data_dir = Path(config.get('paths.data_dir')) / 'generated_dataset'
    
    # Check if dataset exists
    if not (data_dir / 'sequences.npy').exists():
        print("\nDataset not found. Generating new dataset...")
        sequences, labels, attack_types = TrafficGenerator.generate_dataset(
            num_normal=config.get('data.num_normal_sequences'),
            num_attacks_per_type=config.get('data.num_attack_sequences_per_type'),
            sequence_length=config.get('data.sequence_length'),
            include_transitions=config.get('data.include_transitions')
        )
        TrafficGenerator.save_dataset(sequences, labels, attack_types, str(data_dir))
    else:
        print("\nLoading existing dataset...")
        sequences, labels, attack_types = TrafficGenerator.load_dataset(str(data_dir))
    
    print(f"Dataset loaded: {len(sequences)} sequences")
    print(f"  Normal: {np.sum(labels == 0)}")
    print(f"  Attacks: {np.sum(labels == 1)}")
    
    # Normalize features
    if config.get('data.normalize_features'):
        print("\nNormalizing features...")
        normalizer = FeatureNormalizer(
            feature_dim=sequences.shape[2],
            momentum=config.get('data.normalization_momentum')
        )
        
        # Fit normalizer on all data
        for seq in sequences:
            normalizer.update(seq)
        
        # Normalize all sequences
        normalized_sequences = np.array([
            normalizer.normalize(seq) for seq in sequences
        ])
        
        # Save normalizer
        normalizer.save(config.get('paths.normalizer_save_path'))
        print(f"Normalizer saved to {config.get('paths.normalizer_save_path')}")
    else:
        normalized_sequences = sequences
        normalizer = None
    
    # Convert to tensors
    X = torch.FloatTensor(normalized_sequences)
    y = torch.FloatTensor(labels)
    
    # Create dataset
    dataset = TensorDataset(X, y)
    
    # Split dataset
    train_size = int(config.get('training.train_split') * len(dataset))
    val_size = int(config.get('training.val_split') * len(dataset))
    test_size = len(dataset) - train_size - val_size
    
    train_dataset, val_dataset, test_dataset = random_split(
        dataset,
        [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(config.get('training.random_seed'))
    )
    
    print(f"\nDataset splits:")
    print(f"  Training: {len(train_dataset)}")
    print(f"  Validation: {len(val_dataset)}")
    print(f"  Testing: {len(test_dataset)}")
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.get('training.batch_size'),
        shuffle=True,
        num_workers=0
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.get('training.batch_size'),
        shuffle=False,
        num_workers=0
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=config.get('training.batch_size'),
        shuffle=False,
        num_workers=0
    )
    
    return train_loader, val_loader, test_loader, normalizer


def train_model(config: Config, train_loader, val_loader, checkpoint_path=None):
    """Train the DDoS detection model."""
    print("\n" + "="*80)
    print("MODEL TRAINING")
    print("="*80)

    # Check if checkpoint exists — try to load, but continue training if incompatible
    best_model_path = Path(config.get('paths.checkpoint_dir')) / 'best_model.pt'
    if best_model_path.exists() and checkpoint_path is None:
        print(f"\nFound existing trained model at {best_model_path} — attempting to load")
        try:
            checkpoint = torch.load(best_model_path, map_location=config.get('edge.target_device'))

            # Initialize model with saved config
            model_config = checkpoint.get('model_config', {
                'input_dim': config.get('model.input_dim'),
                'state_dim': config.get('model.state_dim'),
                'hidden_dim': config.get('model.hidden_dim'),
                'num_layers': config.get('model.num_layers'),
                'dropout': config.get('model.dropout'),
                'use_attention': config.get('model.use_attention')
            })

            model = DDoSDetector(**model_config)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.to(config.get('edge.target_device'))

            # Initialize trainer for evaluation
            trainer = DDoSTrainer(
                model=model,
                device=config.get('edge.target_device'),
                learning_rate=config.get('training.learning_rate'),
                weight_decay=config.get('training.weight_decay'),
                use_focal_loss=config.get('training.use_focal_loss'),
                focal_alpha=config.get('training.focal_alpha'),
                focal_gamma=config.get('training.focal_gamma')
            )

            print("✅ Model loaded successfully - skipping training")
            return trainer, None  # Return trainer for evaluation, None for history
        except Exception as e:
            print(f"⚠️  Failed to load existing checkpoint (will train from scratch): {e}")
            # Fall through to training from scratch

    # Initialize model
    print("\nInitializing new model...")
    model = DDoSDetector(
        input_dim=config.get('model.input_dim'),
        state_dim=config.get('model.state_dim'),
        hidden_dim=config.get('model.hidden_dim'),
        num_layers=config.get('model.num_layers'),
        dropout=config.get('model.dropout'),
        use_attention=config.get('model.use_attention')
    )
    
    # Print model info
    model_size = model.get_model_size()
    print(f"\nModel Statistics:")
    print(f"  Total Parameters: {model_size['num_parameters']:,}")
    print(f"  Model Size: {model_size['total_mb']:.2f} MB")
    print(f"  Device: {config.get('edge.target_device')}")
    
    # Initialize trainer
    trainer = DDoSTrainer(
        model=model,
        device=config.get('edge.target_device'),
        learning_rate=config.get('training.learning_rate'),
        weight_decay=config.get('training.weight_decay'),
        use_focal_loss=config.get('training.use_focal_loss'),
        focal_alpha=config.get('training.focal_alpha'),
        focal_gamma=config.get('training.focal_gamma')
    )
    
    # Train model
    print("\nStarting training...")
    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=config.get('training.num_epochs'),
        early_stopping_patience=config.get('training.early_stopping_patience'),
        checkpoint_dir=config.get('paths.checkpoint_dir'),
        verbose=True
    )
    
    # Plot training history
    print("\nPlotting training history...")
    trainer.plot_training_history(
        save_path=Path(config.get('paths.output_dir')) / 'training_history.png'
    )
    
    return trainer, history


def evaluate_model(trainer, test_loader, config: Config):
    """Evaluate model on test set."""
    print("\n" + "="*80)
    print("MODEL EVALUATION")
    print("="*80)
    
    # Evaluate
    test_metrics = trainer.validate(test_loader)
    
    print("\nTest Set Performance:")
    print(f"  Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"  Precision: {test_metrics['precision']:.4f}")
    print(f"  Recall: {test_metrics['recall']:.4f}")
    print(f"  F1 Score: {test_metrics['f1_score']:.4f}")
    print(f"  ROC AUC: {test_metrics['roc_auc']:.4f}")
    print(f"  Specificity: {test_metrics['specificity']:.4f}")
    print(f"  MCC: {test_metrics['mcc']:.4f}")
    
    print("\nConfusion Matrix:")
    print(f"  True Positives: {test_metrics['true_positives']}")
    print(f"  True Negatives: {test_metrics['true_negatives']}")
    print(f"  False Positives: {test_metrics['false_positives']}")
    print(f"  False Negatives: {test_metrics['false_negatives']}")
    
    # Save test metrics
    output_path = Path(config.get('paths.output_dir'))
    with open(output_path / 'test_metrics.json', 'w') as f:
        json.dump(test_metrics, f, indent=2)
    
    print(f"\nTest metrics saved to {output_path / 'test_metrics.json'}")
    
    return test_metrics


def measure_performance(model, config: Config):
    """Measure model performance metrics."""
    print("\n" + "="*80)
    print("PERFORMANCE MEASUREMENT")
    print("="*80)
    
    from realtime_detector import ModelOptimizer
    
    # Measure inference time
    print("\nMeasuring inference time...")
    timing_stats = ModelOptimizer.measure_inference_time(
        model,
        input_shape=(1, config.get('data.sequence_length'), config.get('model.input_dim')),
        num_runs=100
    )
    
    print(f"\nInference Time (CPU):")
    print(f"  Mean: {timing_stats['mean_ms']:.2f} ms")
    print(f"  Std: {timing_stats['std_ms']:.2f} ms")
    print(f"  Min: {timing_stats['min_ms']:.2f} ms")
    print(f"  Max: {timing_stats['max_ms']:.2f} ms")
    print(f"  Median: {timing_stats['median_ms']:.2f} ms")
    
    # Check if meets edge requirements
    target_latency = config.get('edge.target_latency_ms')
    if timing_stats['mean_ms'] < target_latency:
        print(f"\n✅ Model meets target latency ({target_latency} ms)")
    else:
        print(f"\n⚠️  Model exceeds target latency ({target_latency} ms)")
    
    # Model size check
    model_size = model.get_model_size()
    max_memory = config.get('edge.max_memory_mb')
    if model_size['total_mb'] < max_memory:
        print(f"✅ Model fits in target memory ({max_memory} MB)")
    else:
        print(f"⚠️  Model exceeds target memory ({max_memory} MB)")
    
    # Save performance metrics
    output_path = Path(config.get('paths.output_dir'))
    with open(output_path / 'performance_metrics.json', 'w') as f:
        json.dump({
            'inference_time': timing_stats,
            'model_size': model_size,
            'meets_latency_requirement': bool(timing_stats['mean_ms'] < target_latency),
            'meets_memory_requirement': bool(model_size['total_mb'] < max_memory)
        }, f, indent=2)
    
    return timing_stats


def export_model(model, config: Config):
    """Export model for deployment."""
    print("\n" + "="*80)
    print("MODEL EXPORT")
    print("="*80)
    
    output_path = Path(config.get('paths.output_dir'))
    
    # Save PyTorch model
    torch.save(model.state_dict(), output_path / 'model.pt')
    print(f"\n✅ PyTorch model saved to {output_path / 'model.pt'}")
    
    # Export to ONNX
    try:
        from realtime_detector import ModelOptimizer
        onnx_path = output_path / 'model.onnx'
        ModelOptimizer.export_to_onnx(
            model,
            str(onnx_path),
            input_shape=(1, config.get('data.sequence_length'), config.get('model.input_dim'))
        )
        print(f"✅ ONNX model exported to {onnx_path}")
    except Exception as e:
        print(f"⚠️  ONNX export failed: {e}")
    
    # Quantize model if enabled
    if config.get('edge.enable_model_compression'):
        try:
            from realtime_detector import ModelOptimizer
            quantized_model = ModelOptimizer.quantize_model(model)
            torch.save(quantized_model.state_dict(), output_path / 'model_quantized.pt')
            print(f"✅ Quantized model saved to {output_path / 'model_quantized.pt'}")
        except Exception as e:
            print(f"⚠️  Quantization failed: {e}")


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(description='Train DDoS Detection Model')
    parser.add_argument('--config', type=str, default=None, help='Path to config file')
    parser.add_argument('--checkpoint', type=str, default=None, help='Path to checkpoint to resume from')
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = Config.load(args.config)
        print(f"Loaded configuration from {args.config}")
    else:
        config = Config()
        print("Using default configuration")
    
    # Set random seed
    setup_seed(config.get('training.random_seed'))
    
    # Prepare data
    train_loader, val_loader, test_loader, normalizer = prepare_data(config)
    
    # Train model
    trainer, history = train_model(config, train_loader, val_loader)
    
    # Evaluate model
    test_metrics = evaluate_model(trainer, test_loader, config)
    
    # Measure performance
    timing_stats = measure_performance(trainer.model, config)
    
    # Export model
    export_model(trainer.model, config)
    
    print("\n" + "="*80)
    print("TRAINING COMPLETE!")
    print("="*80)
    print(f"\nModel and results saved to {config.get('paths.output_dir')}")
    print("\nKey Metrics:")
    print(f"  Test Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"  Test F1 Score: {test_metrics['f1_score']:.4f}")
    print(f"  Inference Time: {timing_stats['mean_ms']:.2f} ms")
    
    return trainer, test_metrics


if __name__ == "__main__":
    main()
