"""
Train S5 Model on Real CIC-DDoS2019 Data

This script trains the S5 model on the real-world CIC-DDoS2019 dataset
to validate performance on actual network traffic data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from pathlib import Path
import json
from sklearn.model_selection import train_test_split

from ssm_model import DDoSDetector
from trainer import DDoSTrainer
from config import Config


def load_real_data(processed_file='cic_ddos2019_processed.npz'):
    """
    Load the processed CIC-DDoS2019 real-world dataset.
    
    Note: The processed file contains mostly attacks. For better binary classification,
    we'll treat different attack types as positive class (attack=1) and measure 
    performance on distinguishing attacks from each other.
    
    Returns:
        Train, val, test loaders and normalizer stats
    """
    print("\n" + "="*80)
    print("LOADING REAL CIC-DDoS2019 DATA")
    print("="*80)
    
    if not Path(processed_file).exists():
        raise FileNotFoundError(
            f"Processed data file not found: {processed_file}\n"
            "Please run: python cic_ddos2019_loader.py"
        )
    
    # Load processed data
    print(f"\nLoading from {processed_file}...")
    data = np.load(processed_file)
    
    X_train = data['X_train']
    y_train = data['y_train']
    X_val = data['X_val']
    y_val = data['y_val']
    X_test = data['X_test']
    y_test = data['y_test']
    
    # Get normalizer stats
    mean = data['mean']
    std = data['std']
    
    print(f"\n✅ Data loaded successfully!")
    print(f"Training samples: {len(X_train):,}")
    print(f"Validation samples: {len(X_val):,}")
    print(f"Test samples: {len(X_test):,}")
    
    # Check class distribution in raw labels
    print(f"\nRaw CIC-DDoS2019 training set distribution:")
    unique, counts = np.unique(y_train, return_counts=True)
    for label, count in zip(unique, counts):
        pct = 100 * count / len(y_train)
        attack_names = {1: 'SYN Flood', 2: 'UDP Flood', 4: 'DNS Amplification'}
        label_name = attack_names.get(int(label), f'Attack Type {int(label)}')
        print(f"  {label_name}: {count:,} ({pct:.1f}%)")
    
    # For binary classification: Use attack type distribution as multi-task learning
    # Label = 0 for SYN (type 1), 1 for UDP (type 2), 2 for DNS (type 4)
    label_map = {1: 0, 2: 1, 4: 2}
    y_train_mapped = np.array([label_map.get(int(y), 2) for y in y_train])
    y_val_mapped = np.array([label_map.get(int(y), 2) for y in y_val])
    y_test_mapped = np.array([label_map.get(int(y), 2) for y in y_test])
    
    # Convert to binary: 0 = SYN, 1 = other attacks (for binary classification)
    y_train_binary = (y_train_mapped > 0).astype(np.float32)
    y_val_binary = (y_val_mapped > 0).astype(np.float32)
    y_test_binary = (y_test_mapped > 0).astype(np.float32)
    
    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.FloatTensor(y_train_binary)
    X_val_t = torch.FloatTensor(X_val)
    y_val_t = torch.FloatTensor(y_val_binary)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.FloatTensor(y_test_binary)
    
    # Create datasets
    train_dataset = TensorDataset(X_train_t, y_train_t)
    val_dataset = TensorDataset(X_val_t, y_val_t)
    test_dataset = TensorDataset(X_test_t, y_test_t)
    
    # Create data loaders
    batch_size = 32
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, val_loader, test_loader, (mean, std)


def train_real_model(config: Config, train_loader, val_loader):
    """Train the S5 model on real data."""
    print("\n" + "="*80)
    print("TRAINING ON REAL DATA")
    print("="*80)
    
    # Initialize model
    print("\nInitializing S5 model...")
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
    
    # Create checkpoint directory for real data
    checkpoint_dir = Path(config.get('paths.checkpoint_dir')) / 'real_data'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Train model
    print("\nStarting training on real data...")
    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=config.get('training.num_epochs'),
        early_stopping_patience=config.get('training.early_stopping_patience'),
        checkpoint_dir=str(checkpoint_dir),
        verbose=True
    )
    
    # Plot training history
    print("\nPlotting training history...")
    trainer.plot_training_history(
        save_path=Path(config.get('paths.output_dir')) / 'training_history_real_data.png'
    )
    
    return trainer, history


def evaluate_real_model(trainer, test_loader, config: Config):
    """Evaluate model on real test set."""
    print("\n" + "="*80)
    print("EVALUATION ON REAL DATA")
    print("="*80)
    
    # Evaluate
    test_metrics = trainer.validate(test_loader)
    
    print("\n✅ Real Data Test Set Performance:")
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
    metrics_file = output_path / 'test_metrics_real_data.json'
    with open(metrics_file, 'w') as f:
        json.dump(test_metrics, f, indent=2)
    
    print(f"\n✅ Real data metrics saved to {metrics_file}")
    
    return test_metrics


def compare_results():
    """Compare synthetic vs real data results."""
    print("\n" + "="*80)
    print("COMPARISON: SYNTHETIC vs REAL DATA")
    print("="*80)
    
    output_path = Path('./outputs')
    
    # Load synthetic results
    synthetic_file = output_path / 'test_metrics.json'
    real_file = output_path / 'test_metrics_real_data.json'
    
    if not synthetic_file.exists():
        print("\n⚠️  Synthetic results not found")
        return None
    
    if not real_file.exists():
        print("\n⚠️  Real data results not found")
        return None
    
    with open(synthetic_file) as f:
        synthetic_metrics = json.load(f)
    
    with open(real_file) as f:
        real_metrics = json.load(f)
    
    # Create comparison table
    comparison = {
        'metric': ['Accuracy', 'Precision', 'Recall', 'F1 Score', 'ROC AUC', 'Specificity', 'MCC'],
        'synthetic': [
            synthetic_metrics['accuracy'],
            synthetic_metrics['precision'],
            synthetic_metrics['recall'],
            synthetic_metrics['f1_score'],
            synthetic_metrics['roc_auc'],
            synthetic_metrics['specificity'],
            synthetic_metrics['mcc']
        ],
        'real_data': [
            real_metrics['accuracy'],
            real_metrics['precision'],
            real_metrics['recall'],
            real_metrics['f1_score'],
            real_metrics['roc_auc'],
            real_metrics['specificity'],
            real_metrics['mcc']
        ]
    }
    
    # Calculate differences
    comparison['gap'] = [
        comparison['synthetic'][i] - comparison['real_data'][i]
        for i in range(len(comparison['metric']))
    ]
    
    # Print comparison table
    print("\n📊 RESULTS COMPARISON TABLE")
    print("-" * 85)
    print(f"{'Metric':<15} {'Synthetic':<15} {'Real Data':<15} {'Gap':<15}")
    print("-" * 85)
    
    for i, metric in enumerate(comparison['metric']):
        syn = comparison['synthetic'][i]
        real = comparison['real_data'][i]
        gap = comparison['gap'][i]
        print(f"{metric:<15} {syn:>14.4f} {real:>14.4f} {gap:>14.4f}")
    
    print("-" * 85)
    
    # Save comparison
    comparison_file = output_path / 'comparison_synthetic_vs_real.json'
    with open(comparison_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    print(f"\n✅ Comparison saved to {comparison_file}")
    
    # Summary
    print("\n📈 KEY FINDINGS:")
    avg_gap = np.mean(comparison['gap'])
    print(f"  Average performance gap: {avg_gap:+.4f}")
    
    if avg_gap < 0.05:
        print("  ✅ Excellent generalization - minimal gap between synthetic and real data")
    elif avg_gap < 0.10:
        print("  ✅ Good generalization - small gap (expected for real-world data)")
    else:
        print("  ⚠️  Notable performance drop - consider hyperparameter tuning")
    
    return comparison


def main():
    """Main training pipeline for real data."""
    
    # Load configuration
    config = Config()
    print(f"\nUsing configuration from: default")
    
    # Set random seed
    torch.manual_seed(config.get('training.random_seed'))
    np.random.seed(config.get('training.random_seed'))
    
    # Load real data
    train_loader, val_loader, test_loader, stats = load_real_data()
    
    # Train on real data
    trainer, history = train_real_model(config, train_loader, val_loader)
    
    # Evaluate on real data
    test_metrics = evaluate_real_model(trainer, test_loader, config)
    
    # Compare synthetic vs real
    compare_results()
    
    print("\n" + "="*80)
    print("REAL DATA TRAINING COMPLETE!")
    print("="*80)
    print(f"\nResults saved to ./outputs/")
    print(f"  - test_metrics_real_data.json")
    print(f"  - comparison_synthetic_vs_real.json")
    print(f"  - training_history_real_data.png")
    
    return trainer, test_metrics


if __name__ == "__main__":
    main()
