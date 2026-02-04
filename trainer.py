"""
Training Module for DDoS Detection System

Comprehensive training pipeline with support for:
- Early stopping
- Learning rate scheduling
- Model checkpointing
- Metrics tracking
- Cross-validation
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, random_split
import numpy as np
from typing import Dict, List, Optional, Tuple
import time
import json
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt


class FocalLoss(nn.Module):
    """Focal Loss for handling class imbalance."""
    
    def __init__(self, alpha: float = 0.25, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
    
    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            inputs: Predicted probabilities (after sigmoid)
            targets: Ground truth labels (0 or 1)
        """
        bce_loss = nn.functional.binary_cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-bce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * bce_loss
        return focal_loss.mean()


class MetricsCalculator:
    """Calculate classification metrics."""
    
    @staticmethod
    def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> Dict:
        """
        Calculate comprehensive metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_prob: Predicted probabilities
        
        Returns:
            Dictionary of metrics
        """
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score,
            roc_auc_score, confusion_matrix, matthews_corrcoef
        )
        
        # Basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        # ROC AUC
        try:
            roc_auc = roc_auc_score(y_true, y_prob)
        except:
            roc_auc = 0.0
        
        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        # Specificity
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        
        # False Positive Rate
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        
        # Matthews Correlation Coefficient
        mcc = matthews_corrcoef(y_true, y_pred)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'roc_auc': roc_auc,
            'specificity': specificity,
            'false_positive_rate': fpr,
            'mcc': mcc,
            'true_positives': int(tp),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn)
        }


class EarlyStopping:
    """Early stopping to prevent overfitting."""
    
    def __init__(self, patience: int = 10, min_delta: float = 0.0, mode: str = 'min'):
        """
        Args:
            patience: Number of epochs to wait for improvement
            min_delta: Minimum change to qualify as improvement
            mode: 'min' or 'max' - whether lower or higher is better
        """
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False
        
    def __call__(self, score: float) -> bool:
        """
        Check if training should stop.
        
        Args:
            score: Current validation score
        
        Returns:
            True if should stop, False otherwise
        """
        if self.best_score is None:
            self.best_score = score
            return False
        
        if self.mode == 'min':
            improved = score < (self.best_score - self.min_delta)
        else:
            improved = score > (self.best_score + self.min_delta)
        
        if improved:
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
                return True
        
        return False


class DDoSTrainer:
    """Main trainer class for DDoS detection model."""
    
    def __init__(
        self,
        model: nn.Module,
        device: str = 'cpu',
        learning_rate: float = 0.001,
        weight_decay: float = 1e-5,
        use_focal_loss: bool = True,
        focal_alpha: float = 0.25,
        focal_gamma: float = 2.0
    ):
        """
        Initialize trainer.
        
        Args:
            model: DDoS detection model
            device: Device to train on ('cpu' or 'cuda')
            learning_rate: Initial learning rate
            weight_decay: L2 regularization weight
            use_focal_loss: Whether to use focal loss
            focal_alpha: Focal loss alpha parameter
            focal_gamma: Focal loss gamma parameter
        """
        self.model = model.to(device)
        self.device = device
        
        # Loss function
        if use_focal_loss:
            self.criterion = FocalLoss(alpha=focal_alpha, gamma=focal_gamma)
        else:
            self.criterion = nn.BCELoss()
        
        # Optimizer
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5
        )
        
        # Metrics tracking
        self.history = defaultdict(list)
        self.best_val_loss = float('inf')
        self.best_model_state = None
    
    def train_epoch(self, train_loader: DataLoader) -> Dict:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_labels = []
        all_probs = []
        
        for batch_idx, (data, labels) in enumerate(train_loader):
            data = data.to(self.device)
            labels = labels.to(self.device).float()
            
            # Forward pass
            self.optimizer.zero_grad()
            output = self.model(data, return_confidence=False, return_attack_type=False)
            predictions = output['final_prediction']
            
            # Compute loss
            loss = self.criterion(predictions, labels)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            # Track metrics
            total_loss += loss.item()
            all_preds.extend((predictions > 0.5).cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(predictions.detach().cpu().numpy())
        
        # Calculate metrics
        avg_loss = total_loss / len(train_loader)
        metrics = MetricsCalculator.calculate_metrics(
            np.array(all_labels),
            np.array(all_preds),
            np.array(all_probs)
        )
        metrics['loss'] = avg_loss
        
        return metrics
    
    def validate(self, val_loader: DataLoader) -> Dict:
        """Validate the model."""
        self.model.eval()
        total_loss = 0.0
        all_preds = []
        all_labels = []
        all_probs = []
        
        with torch.no_grad():
            for data, labels in val_loader:
                data = data.to(self.device)
                labels = labels.to(self.device).float()
                
                # Forward pass
                output = self.model(data, return_confidence=False, return_attack_type=False)
                predictions = output['final_prediction']
                
                # Compute loss
                loss = self.criterion(predictions, labels)
                
                # Track metrics
                total_loss += loss.item()
                all_preds.extend((predictions > 0.5).cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probs.extend(predictions.cpu().numpy())
        
        # Calculate metrics
        avg_loss = total_loss / len(val_loader)
        metrics = MetricsCalculator.calculate_metrics(
            np.array(all_labels),
            np.array(all_preds),
            np.array(all_probs)
        )
        metrics['loss'] = avg_loss
        
        return metrics
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        num_epochs: int = 100,
        early_stopping_patience: int = 15,
        checkpoint_dir: str = './checkpoints',
        verbose: bool = True
    ) -> Dict:
        """
        Full training loop.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            num_epochs: Maximum number of epochs
            early_stopping_patience: Patience for early stopping
            checkpoint_dir: Directory to save checkpoints
            verbose: Whether to print progress
        
        Returns:
            Training history
        """
        checkpoint_path = Path(checkpoint_dir)
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        early_stopping = EarlyStopping(patience=early_stopping_patience, mode='min')
        
        for epoch in range(num_epochs):
            start_time = time.time()
            
            # Train
            train_metrics = self.train_epoch(train_loader)
            
            # Validate
            val_metrics = self.validate(val_loader)
            
            # Update learning rate
            self.scheduler.step(val_metrics['loss'])
            
            # Track history
            for key, value in train_metrics.items():
                self.history[f'train_{key}'].append(value)
            for key, value in val_metrics.items():
                self.history[f'val_{key}'].append(value)
            self.history['epoch'].append(epoch + 1)
            self.history['lr'].append(self.optimizer.param_groups[0]['lr'])
            
            # Save best model
            if val_metrics['loss'] < self.best_val_loss:
                self.best_val_loss = val_metrics['loss']
                self.best_model_state = self.model.state_dict().copy()
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'val_loss': val_metrics['loss'],
                    'val_metrics': val_metrics
                }, checkpoint_path / 'best_model.pt')
            
            # Print progress
            if verbose:
                epoch_time = time.time() - start_time
                print(f"\nEpoch {epoch+1}/{num_epochs} - {epoch_time:.2f}s")
                print(f"Train Loss: {train_metrics['loss']:.4f} | "
                      f"Val Loss: {val_metrics['loss']:.4f}")
                print(f"Train Acc: {train_metrics['accuracy']:.4f} | "
                      f"Val Acc: {val_metrics['accuracy']:.4f}")
                print(f"Val F1: {val_metrics['f1_score']:.4f} | "
                      f"Val AUC: {val_metrics['roc_auc']:.4f}")
            
            # Early stopping check
            if early_stopping(val_metrics['loss']):
                print(f"\nEarly stopping triggered at epoch {epoch+1}")
                break
            
            # Save periodic checkpoint
            if (epoch + 1) % 10 == 0:
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                }, checkpoint_path / f'checkpoint_epoch_{epoch+1}.pt')
        
        # Load best model
        if self.best_model_state is not None:
            self.model.load_state_dict(self.best_model_state)
        
        # Save training history
        with open(checkpoint_path / 'training_history.json', 'w') as f:
            json.dump(self.history, f, indent=2)
        
        return dict(self.history)
    
    def plot_training_history(self, save_path: Optional[str] = None):
        """Plot training history."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Loss
        axes[0, 0].plot(self.history['epoch'], self.history['train_loss'], label='Train Loss')
        axes[0, 0].plot(self.history['epoch'], self.history['val_loss'], label='Val Loss')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].set_title('Training and Validation Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # Accuracy
        axes[0, 1].plot(self.history['epoch'], self.history['train_accuracy'], label='Train Acc')
        axes[0, 1].plot(self.history['epoch'], self.history['val_accuracy'], label='Val Acc')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Accuracy')
        axes[0, 1].set_title('Training and Validation Accuracy')
        axes[0, 1].legend()
        axes[0, 1].grid(True)
        
        # F1 Score
        axes[1, 0].plot(self.history['epoch'], self.history['train_f1_score'], label='Train F1')
        axes[1, 0].plot(self.history['epoch'], self.history['val_f1_score'], label='Val F1')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('F1 Score')
        axes[1, 0].set_title('F1 Score')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
        
        # Learning Rate
        axes[1, 1].plot(self.history['epoch'], self.history['lr'])
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Learning Rate')
        axes[1, 1].set_title('Learning Rate Schedule')
        axes[1, 1].set_yscale('log')
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def save_model(self, filepath: str):
        """Save model to file."""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'model_config': {
                'input_dim': self.model.input_dim,
                'state_dim': self.model.state_dim,
            },
            'best_val_loss': self.best_val_loss,
            'history': dict(self.history)
        }, filepath)
    
    def load_model(self, filepath: str):
        """Load model from file."""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.best_val_loss = checkpoint.get('best_val_loss', float('inf'))
        if 'history' in checkpoint:
            self.history = defaultdict(list, checkpoint['history'])
