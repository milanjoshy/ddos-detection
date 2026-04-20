"""
CIC-DDoS2019 Dataset Loader and Feature Extractor
For DDoS Detection using S5 Models

This script loads the CIC-DDoS2019 dataset and extracts the 8 features
needed for the S5 model from the 80+ features available in the dataset.

Dataset Download: https://www.unb.ca/cic/datasets/ddos-2019.html
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')


class CICDDoS2019Loader:
    """
    Load and preprocess CIC-DDoS2019 dataset for S5 model training
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize loader with dataset directory
        
        Args:
            data_dir: Path to CIC-DDoS2019 dataset directory
        """
        self.data_dir = Path(data_dir)
        self.attack_types = {
            'BENIGN': 0,
            'Syn': 1,           # SYN Flood
            'UDP': 2,           # UDP Flood
            'WebDDoS': 3,       # HTTP Flood
            'DrDoS_DNS': 4,     # DNS Amplification
        }
        
    def load_csv_files(self) -> pd.DataFrame:
        """
        Load all relevant CSV files from the dataset
        
        Returns:
            Combined dataframe with all traffic
        """
        print("Loading CIC-DDoS2019 dataset...")

        # Support both CSV and Parquet files commonly present in the workspace
        dfs = []
        csv_files = list(self.data_dir.glob("*.csv"))
        parquet_files = list(self.data_dir.glob("*.parquet"))
        files = csv_files + parquet_files

        if not files:
            raise ValueError(f"No CSV or Parquet files found in {self.data_dir}")

        # Helper to map filename to a known attack type key
        def detect_attack_name(fname: str) -> Tuple[str, int]:
            name = fname.lower()
            # Common mappings
            if 'benign' in name or 'benign' in fname:
                return 'BENIGN', self.attack_types.get('BENIGN')
            if 'syn' in name:
                return 'Syn', self.attack_types.get('Syn')
            if 'udp' in name and 'udplag' not in name:
                return 'UDP', self.attack_types.get('UDP')
            if 'web' in name or 'http' in name:
                return 'WebDDoS', self.attack_types.get('WebDDoS')
            if 'dns' in name:
                return 'DrDoS_DNS', self.attack_types.get('DrDoS_DNS')
            # Fallback: return file stem as name and label -1 (unknown)
            return Path(fname).stem, -1

        for file in files:
            try:
                if file.suffix.lower() == '.parquet':
                    df = pd.read_parquet(file)
                else:
                    df = pd.read_csv(file, encoding='utf-8', low_memory=False)

                # Detect attack name from filename
                attack_name, label = detect_attack_name(file.name)

                if label is None:
                    label = -1

                # Add label and attack name
                df['attack_type'] = label
                df['attack_name'] = attack_name

                # Clean column names
                df.columns = df.columns.str.strip()

                dfs.append(df)
                print(f"  Loaded {file.name}: {len(df)} samples (as {attack_name})")

            except Exception as e:
                print(f"  Error loading {file.name}: {e}")
                    
        if not dfs:
            raise ValueError("No data files loaded!")
            
        # Combine all dataframes
        combined = pd.concat(dfs, ignore_index=True)
        print(f"\nTotal samples loaded: {len(combined)}")
        print(f"Attack distribution:\n{combined['attack_name'].value_counts()}\n")
        
        return combined
    
    def extract_8_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract the 8 features from CIC-DDoS2019's 80+ features
        
        Features to extract:
        1. Packet Rate (packets/sec)
        2. Byte Rate (KB/sec)
        3. Average Packet Size (bytes)
        4. Packet Size Std Dev (bytes)
        5. SYN Ratio (0-1)
        6. Unique Source IPs (approximated)
        7. Unique Destination Ports (approximated)
        8. Protocol Entropy (bits)
        
        Args:
            df: Raw CIC-DDoS2019 dataframe
            
        Returns:
            Dataframe with 8 extracted features + labels
        """
        print("Extracting 8 features from CIC dataset...")
        
        features = pd.DataFrame()

        # Helper to find first available column from alternatives
        def _col(series_df: pd.DataFrame, candidates: List[str], default=0):
            for c in candidates:
                if c in series_df.columns:
                    return series_df[c].fillna(0)
            # return a zero-series if nothing found
            return pd.Series(np.full(len(series_df), default), index=series_df.index)

        # 1. Packet Rate (packets/sec)
        # CIC has 'Flow Packets/s' or approximate from packet counts and duration
        if 'Flow Packets/s' in df.columns:
            features['packet_rate'] = df['Flow Packets/s'].fillna(0)
        else:
            total_packets = _col(df, ['Total Fwd Packets', 'Fwd Packets', 'TotFwdPackets', 'TotalPackets']) + _col(df, ['Total Bwd Packets', 'Bwd Packets', 'TotBwdPackets'])
            duration = _col(df, ['Flow Duration', 'Duration', 'FlowDuration'], default=1) / 1e6
            features['packet_rate'] = total_packets / (duration + 1e-8)
        
        # 2. Byte Rate (KB/sec)
        if 'Flow Bytes/s' in df.columns:
            features['byte_rate'] = df['Flow Bytes/s'].fillna(0) / 1024  # Convert to KB/s
        else:
            # Approximate
            total_bytes = _col(df, ['Total Length of Fwd Packets', 'TotLen Fwd Pkts', 'TotalLengthFwdPackets']) + _col(df, ['Total Length of Bwd Packets', 'TotLen Bwd Pkts', 'TotalLengthBwdPackets'])
            duration = _col(df, ['Flow Duration', 'Duration', 'FlowDuration'], default=1) / 1e6
            features['byte_rate'] = (total_bytes / (duration + 1e-8)) / 1024
        
        # 3. Average Packet Size (bytes)
        total_length = _col(df, ['Total Length of Fwd Packets', 'TotLen Fwd Pkts', 'TotalLengthFwdPackets']) + _col(df, ['Total Length of Bwd Packets', 'TotLen Bwd Pkts', 'TotalLengthBwdPackets'])
        total_packets = _col(df, ['Total Fwd Packets', 'Fwd Packets', 'TotFwdPackets', 'TotalPackets']) + _col(df, ['Total Bwd Packets', 'Bwd Packets', 'TotBwdPackets'])
        features['avg_packet_size'] = total_length / (total_packets + 1e-8)
        
        # 4. Packet Size Std Dev
        if 'Packet Length Std' in df.columns or 'Packet Length Std Dev' in df.columns:
            features['packet_size_std'] = _col(df, ['Packet Length Std', 'Packet Length Std Dev'])
        else:
            # Use variance if std not available
            features['packet_size_std'] = _col(df, ['Packet Length Variance', 'PacketLengthVariance']) ** 0.5
        
        # 5. SYN Ratio
        if any(c in df.columns for c in ['SYN Flag Count', 'SYN_Flags', 'SYNCount']):
            total_flags = (_col(df, ['SYN Flag Count', 'SYN_Flags', 'SYNCount']) + 
                          _col(df, ['ACK Flag Count', 'ACK_Flags', 'ACKCount']) + 
                          _col(df, ['PSH Flag Count', 'PSH_Flags', 'PSHCount']) +
                          _col(df, ['FIN Flag Count', 'FIN_Flags', 'FINCount']) +
                          _col(df, ['RST Flag Count', 'RST_Flags', 'RSTCount']))
            features['syn_ratio'] = _col(df, ['SYN Flag Count', 'SYN_Flags', 'SYNCount']) / (total_flags + 1e-8)
        else:
            # Approximate from flow features
            features['syn_ratio'] = 0.1  # Default for normal traffic
        
        # 6. Unique Source IPs (approximated)
        # CIC is flow-based, so we approximate from source/destination diversity
        # Higher values for attacks with many spoofed IPs
        if 'Fwd PSH Flags' in df.columns and 'Bwd PSH Flags' in df.columns:
            # Use push flag diversity as proxy
            features['unique_src_ips'] = (_col(df, ['Fwd PSH Flags']) + 
                                         _col(df, ['Bwd PSH Flags'])) * 10
        else:
            # Estimate based on attack type
            features['unique_src_ips'] = 50  # Will be refined later
        
        # 7. Unique Destination Ports (approximated)
        if 'Destination Port' in df.columns or 'Dst Port' in df.columns or 'DestinationPort' in df.columns:
            # Group by time and count unique ports (simplified)
            features['unique_dst_ports'] = _col(df, ['Destination Port', 'Dst Port', 'DestinationPort'], default=80)
        else:
            features['unique_dst_ports'] = 20  # Default estimate
        
        # 8. Protocol Entropy
        # Calculate from protocol distribution (simplified)
        if 'Protocol' in df.columns or 'Proto' in df.columns:
            protocol_counts = _col(df, ['Protocol', 'Proto'])
            # protocol_counts here is a series of values; compute distribution
            dist = protocol_counts.value_counts(normalize=True)
            entropy = -(dist * np.log2(dist + 1e-8)).sum()
            features['protocol_entropy'] = entropy
        else:
            # Estimate based on flow characteristics
            features['protocol_entropy'] = 1.5  # Default for mixed traffic
        
        # Add labels
        features['label'] = df['attack_type']
        features['attack_name'] = df['attack_name']
        
        # Replace infinities and NaNs
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(0)
        
        # Clip extreme values (outliers)
        for col in features.columns:
            if col not in ['label', 'attack_name']:
                q99 = features[col].quantile(0.99)
                features[col] = features[col].clip(upper=q99)
        
        print(f"Extracted features shape: {features.shape}")
        print("\nFeature statistics:")
        print(features.describe())
        
        return features
    
    def create_sequences(self, 
                        features: pd.DataFrame, 
                        sequence_length: int = 60,
                        samples_per_class: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences of specified length for training
        
        Args:
            features: Dataframe with extracted features
            sequence_length: Number of timesteps per sequence
            samples_per_class: Number of sequences per attack type
            
        Returns:
            X: Array of shape (n_samples, sequence_length, 8)
            y: Array of labels (n_samples,)
        """
        print(f"\nCreating sequences of length {sequence_length}...")
        
        X_list = []
        y_list = []
        
        for attack_type in range(5):  # 5 attack types
            # Get samples for this attack type
            mask = features['label'] == attack_type
            attack_data = features[mask].copy()
            
            if len(attack_data) < sequence_length:
                print(f"Warning: Not enough data for attack type {attack_type}")
                continue
            
            # Randomly sample sequences
            n_possible = len(attack_data) - sequence_length
            n_samples = min(samples_per_class, n_possible)
            
            for _ in range(n_samples):
                # Random starting point
                start_idx = np.random.randint(0, n_possible)
                
                # Extract sequence
                sequence = attack_data.iloc[start_idx:start_idx + sequence_length]
                
                # Get feature columns only (exclude label and name)
                feature_cols = [col for col in sequence.columns 
                               if col not in ['label', 'attack_name']]
                
                X_list.append(sequence[feature_cols].values)
                y_list.append(attack_type)
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        print(f"Created {len(X)} sequences")
        print(f"X shape: {X.shape}")
        print(f"y shape: {y.shape}")
        print(f"Class distribution: {np.bincount(y)}")
        
        return X, y
    
    def normalize_features(self, X_train: np.ndarray, X_val: np.ndarray, X_test: np.ndarray):
        """
        Normalize features using training statistics
        
        Args:
            X_train, X_val, X_test: Feature arrays
            
        Returns:
            Normalized arrays and statistics
        """
        print("\nNormalizing features...")
        
        # Compute statistics from training data
        mean = X_train.mean(axis=(0, 1), keepdims=True)
        std = X_train.std(axis=(0, 1), keepdims=True) + 1e-8
        
        # Normalize all sets
        X_train_norm = (X_train - mean) / std
        X_val_norm = (X_val - mean) / std
        X_test_norm = (X_test - mean) / std
        
        return X_train_norm, X_val_norm, X_test_norm, (mean, std)


def main():
    """
    Example usage of the CIC-DDoS2019 loader
    """
    # Path to CIC-DDoS2019 dataset (defaults to `data/CIC-DDoS2019` next to this script)
    data_dir = Path(__file__).resolve().parent / "data" / "CIC-DDoS2019"
    loader = CICDDoS2019Loader(data_dir)
    
    # Load dataset
    df = loader.load_csv_files()
    
    # Extract 8 features
    features = loader.extract_8_features(df)
    
    # Create sequences
    X, y = loader.create_sequences(features, 
                                   sequence_length=60, 
                                   samples_per_class=1000)
    
    # Split into train/val/test (70/15/15)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=42
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.176, stratify=y_temp, random_state=42  # 0.176 * 0.85 ≈ 0.15
    )
    
    # Normalize
    X_train, X_val, X_test, stats = loader.normalize_features(X_train, X_val, X_test)
    
    print("\n=== Final Dataset Shapes ===")
    print(f"Training: X={X_train.shape}, y={y_train.shape}")
    print(f"Validation: X={X_val.shape}, y={y_val.shape}")
    print(f"Test: X={X_test.shape}, y={y_test.shape}")
    
    # Save processed data
    np.savez('cic_ddos2019_processed.npz',
             X_train=X_train, y_train=y_train,
             X_val=X_val, y_val=y_val,
             X_test=X_test, y_test=y_test,
             mean=stats[0], std=stats[1])
    
    print("\nProcessed data saved to 'cic_ddos2019_processed.npz'")
    print("\nYou can now train your S5 model on this real-world data!")


if __name__ == "__main__":
    main()
