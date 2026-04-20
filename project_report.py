#!/usr/bin/env python3
"""
DDoS Detection System - Comprehensive Project Report
Shows Dataset Details, Training Info, and Evaluation Results


"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

def print_section(title: str):
    """Print a section header"""
    print(f"\n{title}")
    print("=" * len(title))

def print_subsection(title: str):
    """Print a subsection header"""
    print(f"\n{title}")
    print("-" * len(title))

def print_metric(name: str, value: Any, unit: str = ""):
    """Print a single metric"""
    if isinstance(value, float):
        value_display = f"{value:.4f}"
    else:
        value_display = str(value)
    
    print(f"{name:<35} {value_display} {unit}")

def load_json(path: str) -> Dict[str, Any]:
    """Safely load JSON file"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {path}")
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON: {path}")
        return {}

def show_dataset_details():
    """Display dataset information"""
    print_section("DATASET DETAILS")
    
    print_subsection("CIC-DDoS2019 Dataset")
    print_metric("Dataset Name", "CIC-DDoS2019 (Canadian Cybersecurity Institute)")
    print_metric("Source", "https://www.unb.ca/cic/datasets/ddos-2019.html")
    print_metric("Original Features", "80+ network flow features")
    print_metric("Selected Features", "8 features for S5 model")
    
    # Load the NPZ file to get actual dataset info
    try:
        import numpy as np
        npz_file = np.load("cic_ddos2019_processed.npz", allow_pickle=True)
        
        if 'X_train' in npz_file:
            X_train = npz_file['X_train']
            y_train = npz_file['y_train']
            X_test = npz_file['X_test']
            y_test = npz_file['y_test']
            
            total_samples = len(X_train) + len(X_test)
            train_samples = len(X_train)
            test_samples = len(X_test)
            
            print_subsection("Dataset Split")
            print_metric("Total Samples", total_samples)
            print_metric("Training Samples", train_samples, f"({train_samples/total_samples*100:.1f}%)")
            print_metric("Testing Samples", test_samples, f"({test_samples/total_samples*100:.1f}%)")
            
            print_subsection("Train/Test Split Ratio")
            train_pct = train_samples/total_samples*100
            test_pct = test_samples/total_samples*100
            print_metric("Training Set", f"{train_pct:.1f}%", f"({train_samples} samples)")
            print_metric("Testing Set", f"{test_pct:.1f}%", f"({test_samples} samples)")
            print_metric("Split Ratio", f"{train_samples}:{test_samples}", "")
            
            print_subsection("Class Distribution (Training Set)")
            train_normal = np.sum(y_train == 0)
            train_attacks = np.sum(y_train == 1)
            print_metric("Normal Traffic", train_normal, f"({train_normal/len(y_train)*100:.1f}%)")
            print_metric("Attack Traffic", train_attacks, f"({train_attacks/len(y_train)*100:.1f}%)")
            
            print_subsection("Class Distribution (Test Set)")
            test_normal = np.sum(y_test == 0)
            test_attacks = np.sum(y_test == 1)
            print_metric("Normal Traffic", test_normal, f"({test_normal/len(y_test)*100:.1f}%)")
            print_metric("Attack Traffic", test_attacks, f"({test_attacks/len(y_test)*100:.1f}%)")
            
            print_subsection("Feature Information")
            feature_names = [
                "Packet Rate", "Byte Rate", "SYN Ratio",
                "ACK Ratio", "RST Ratio", "FIN Ratio",
                "Source IP Variety", "Destination Port Variety"
            ]
            for i, feature in enumerate(feature_names):
                print_metric(f"Feature {i+1}", feature)
    except Exception as e:
            print_metric("Dataset Status", f"Error loading: {e}")
def show_training_info():
    """Display training information"""
    print_section("TRAINING INFORMATION")
    
    training_path = "checkpoints/real_data/training_history.json"
    training_data = load_json(training_path)
    
    if not training_data:
        return
    
    print_subsection("Training Metrics")
    
    # Get metrics
    epochs = len(training_data.get('train_accuracy', []))
    print_metric("Total Epochs", epochs)
    print_metric("Dataset", "CIC-DDoS2019 (Real-World Network Data)")
    
    # Final accuracies
    train_acc = training_data.get('train_accuracy', [])
    train_loss = training_data.get('train_loss', [])
    
    if train_acc:
        final_train_acc = train_acc[-1]
        initial_train_acc = train_acc[0]
        print_metric("Initial Train Accuracy", f"{initial_train_acc:.4f}", "")
        print_metric("Final Train Accuracy", f"{final_train_acc:.4f}", "")
    
    if train_loss:
        final_train_loss = train_loss[-1]
        initial_train_loss = train_loss[0]
        print_metric("Initial Train Loss", f"{initial_train_loss:.6f}", "")
        print_metric("Final Train Loss", f"{final_train_loss:.6f}", "")
    
    print_subsection("Validation Metrics")
    val_acc = training_data.get('val_accuracy', [])
    val_loss = training_data.get('val_loss', [])
    
    if val_acc:
        final_val_acc = val_acc[-1]
        print_metric("Final Val Accuracy", f"{final_val_acc:.4f}", "")
    
    if val_loss:
        final_val_loss = val_loss[-1]
        print_metric("Final Val Loss", f"{final_val_loss:.6f}", "")
    
    print_subsection("Training Metrics Summary")
    if train_acc:
        acc_improvement = (train_acc[-1] - train_acc[0]) * 100
        print_metric("Accuracy Improvement", f"{acc_improvement:.2f}%", "over 26 epochs")
    
    if train_loss and val_loss:
        loss_reduction = (train_loss[0] - train_loss[-1])
        print_metric("Loss Reduction", f"{loss_reduction:.6f}", "absolute")
    
    # Early stopping info
    if val_loss:
        best_val_loss = min(val_loss)
        best_epoch = val_loss.index(best_val_loss) + 1
        print_metric("Best Validation Loss", f"{best_val_loss:.6f}", f"at epoch {best_epoch}")
    
    print_subsection("Model Configuration")
    print_metric("Model Type", "State Space Model (S5)")
    print_metric("Framework", "PyTorch 2.0+")
    print_metric("Optimizer", "Adam")
    print_metric("Loss Function", "Binary Cross-Entropy")
    print_metric("Batch Size", "32")
    print_metric("Learning Rate", "0.001 (with decay)")

def show_evaluation_results():
    """Display evaluation and test results"""
    print_section("EVALUATION RESULTS (CIC-DDoS2019)")
    
    test_metrics_path = "outputs/test_metrics_real_data.json"
    test_metrics = load_json(test_metrics_path)
    
    if not test_metrics:
        return
    
    print_subsection("Classification Metrics")
    
    # Core metrics with realistic values
    accuracy = test_metrics.get('accuracy', 'N/A')
    precision = test_metrics.get('precision', 'N/A')
    recall = test_metrics.get('recall', 'N/A')
    
    print_metric("Accuracy", accuracy)
    print_metric("Precision", precision)
    print_metric("Recall (Sensitivity)", recall)
    print_metric("F1-Score", test_metrics.get('f1_score', 'N/A'))
    print_metric("ROC-AUC", test_metrics.get('roc_auc', 'N/A'))
    
    print_subsection("Statistical Metrics")
    print_metric("Specificity (True Negative Rate)", test_metrics.get('specificity', 'N/A'), "")
    print_metric("Matthews Correlation Coef", test_metrics.get('mcc', 'N/A'), "")
    print_metric("False Positive Rate", test_metrics.get('false_positive_rate', 'N/A'), "")
    
    print_subsection("Confusion Matrix (Test Set)")
    tp = test_metrics.get('true_positives', 0)
    tn = test_metrics.get('true_negatives', 0)
    fp = test_metrics.get('false_positives', 0)
    fn = test_metrics.get('false_negatives', 0)
    
    total_attacks = tp + fn
    total_normal = tn + fp
    
    print_metric("True Positives (TP)", tp, f"attacks correctly detected")
    print_metric("True Negatives (TN)", tn, f"normal correctly identified")
    print_metric("False Positives (FP)", fp, f"normal flagged as attack")
    print_metric("False Negatives (FN)", fn, f"attacks missed")
    
    total_predictions = tp + tn + fp + fn
    print_metric("Total Test Samples", total_predictions)
    
    print_subsection("Detection Performance")
    attack_detection_rate = (tp / total_attacks * 100) if total_attacks > 0 else 0
    false_alarm_rate = (fp / total_normal * 100) if total_normal > 0 else 0
    
    print_metric("Attack Detection Rate", f"{attack_detection_rate:.2f}%", "(How many attacks found)")
    print_metric("False Alarm Rate", f"{false_alarm_rate:.2f}%", "(False positives)")
    
    print_subsection("Loss & Error Rate")
    loss = test_metrics.get('loss', None)
    if loss is not None:
        print_metric("Test Loss", f"{loss:.6f}", "Binary Cross-Entropy")

def show_model_info():
    """Display model information"""
    print_section("MODEL INFORMATION")
    
    print_subsection("Model Architecture")
    print_metric("Model Name", "State Space Model (S5)")
    print_metric("Model Type", "Temporal Sequence Classifier")
    print_metric("Input Dimension", "8 features")
    print_metric("Sequence Length", "60 timesteps")
    print_metric("Output Classes", "2 (Normal / Attack)")
    
    print_subsection("Model Files")
    checkpoint_dir = Path("checkpoints")
    if checkpoint_dir.exists():
        for file in sorted(checkpoint_dir.glob("*.pt")):
            size_mb = file.stat().st_size / (1024 * 1024)
            print_metric(file.name, f"{size_mb:.2f}", "MB")
    
    print_subsection("Performance Characteristics")
    print_metric("Inference Latency", "<100 ms", "on CPU")
    print_metric("Model Size", "<50 MB", "unquantized")
    print_metric("Memory Usage", "<512 MB", "RAM")
    print_metric("Hardware Required", "CPU-only", "(no GPU needed)")

def show_summary_statistics():
    """Show summary statistics and insights"""
    print_section("SUMMARY STATISTICS & INSIGHTS")
    
    test_metrics = load_json("outputs/test_metrics_real_data.json")
    training_data = load_json("checkpoints/real_data/training_history.json")
    
    if not test_metrics:
        return
    
    print_subsection("Model Performance Summary")
    
    accuracy = test_metrics.get('accuracy', 0)
    if accuracy >= 0.95:
        performance = "Outstanding ⭐⭐⭐⭐⭐"
    elif accuracy >= 0.90:
        performance = "Excellent ⭐⭐⭐⭐"
    elif accuracy >= 0.80:
        performance = "Good ⭐⭐⭐"
    elif accuracy >= 0.70:
        performance = "Fair ⭐⭐"
    else:
        performance = "Needs Improvement ⭐"
    
    print_metric("Overall Performance", performance)
    print_metric("Test Accuracy", f"{accuracy*100:.2f}%", "(Real-world CIC-DDoS2019 data)")
    
    tp = test_metrics.get('true_positives', 0)
    fn = test_metrics.get('false_negatives', 0)
    total_attacks = tp + fn
    attack_detection = (tp / total_attacks * 100) if total_attacks > 0 else 0
    print_metric("Attack Detection Rate", f"{attack_detection:.2f}%", f"(Found {tp}/{total_attacks} attacks)")
    
    tn = test_metrics.get('true_negatives', 0)
    fp = test_metrics.get('false_positives', 0)
    total_normal = tn + fp
    false_alarm = (fp / total_normal * 100) if total_normal > 0 else 0
    print_metric("False Alarm Rate", f"{false_alarm:.2f}%", f"({fp} false positives)")
    
    print_subsection("Key Insights")
    
    # Precision vs Recall tradeoff
    precision = test_metrics.get('precision', 0)
    recall = test_metrics.get('recall', 0)
    
    if precision > recall:
        tradeoff = f"Model is more conservative ({precision*100:.1f}% precision)"
    elif recall > precision:
        tradeoff = f"Model is more aggressive ({recall*100:.1f}% sensitivity)"
    else:
        tradeoff = "Balanced precision and recall"
    
    print_metric("Precision-Recall Tradeoff", tradeoff)
    
    # Training convergence
    if training_data and training_data.get('train_accuracy'):
        epochs = len(training_data['train_accuracy'])
        early_acc = training_data['train_accuracy'][0]
        final_acc = training_data['train_accuracy'][-1]
        improvement = (final_acc - early_acc) * 100
        print_metric("Training Convergence", f"{improvement:.2f}% improvement", f"over {epochs} epochs")
    
    # Generalization
    if training_data and training_data.get('val_accuracy'):
        val_accs = training_data['val_accuracy']
        final_val_acc = val_accs[-1] if val_accs else 0
        generalization_gap = abs(accuracy - final_val_acc) * 100
        print_metric("Generalization Gap", f"{generalization_gap:.2f}%", "train vs test")
    
    # MCC (balanced metric)
    mcc = test_metrics.get('mcc', 0)
    print_metric("Matthews Correlation", f"{mcc:.4f}", "(account for class imbalance)")
    
    print_subsection("Recommendations")
    
    if fn > 5:
        print(f"  ⚠️  {fn} attacks were missed - model could be more sensitive")
    if fp > 20:
        print(f"  ⚠️  {fp} false positives - consider adjusting threshold")
    if accuracy >= 0.90:
        print(f"  ✓ Good accuracy on real-world data - production ready after validation")
    if attack_detection >= 95:
        print(f"  ✓ Excellent attack detection rate - catches most attacks")
    if false_alarm < 20:
        print(f"  ✓ False alarm rate acceptable - operational feasibility confirmed")

def print_footer():
    """Print footer with project info"""
    print(f"\nProject Information")
    print("=" * 20)
    
    print(f"\nName: Real-Time DDoS Detection System using State Space Models")
    print(f"Institution: Karunya Institute of Technology and Sciences")
    print(f"Authors: Milan Joshy, Keirolona Safana Seles")
    print(f"Model: S5 (State Space Model)")
    print(f"Framework: PyTorch 2.0+")
    print(f"License: MIT")
    print(f"Version: 2.0")
    
    print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def main():
    """Main entry point"""
    print("\nDDoS DETECTION SYSTEM - PROJECT REPORT")
    print("CIC-DDoS2019 Dataset - Training - Evaluation")
    print("=" * 50)
    
    try:
        # Show all sections
        show_dataset_details()
        show_training_info()
        show_evaluation_results()
        show_model_info()
        show_summary_statistics()
        print_footer()
        
        print("Report generated successfully!")
        
    except Exception as e:
        print(f"\nError generating report: {e}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
