"""
State Space Model for DDoS Detection in IoT Edge Environments

This module implements a lightweight linear State Space Model (SSM) for
real-time DDoS attack detection on resource-constrained edge devices.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Optional, Dict, List


class LinearSSM(nn.Module):
    """
    Linear State Space Model for temporal sequence modeling.
    
    The model follows the continuous-time state space formulation:
        dx/dt = Ax(t) + Bu(t)
        y(t) = Cx(t) + Du(t)
    
    Discretized for practical implementation on edge devices.
    """
    
    def __init__(self, input_dim: int, state_dim: int, output_dim: int):
        """
        Initialize the Linear SSM.
        
        Args:
            input_dim: Dimension of input features (traffic statistics)
            state_dim: Dimension of hidden state (temporal memory)
            output_dim: Dimension of output (typically 1 for binary classification)
        """
        super().__init__()
        self.input_dim = input_dim
        self.state_dim = state_dim
        self.output_dim = output_dim
        
        # State transition matrix A (state_dim x state_dim)
        # Initialize with diagonal dominance for stability
        self.A = nn.Parameter(self._initialize_A())
        
        # Input matrix B (state_dim x input_dim)
        self.B = nn.Parameter(torch.randn(state_dim, input_dim) * 0.1)
        
        # Output matrix C (output_dim x state_dim)
        self.C = nn.Parameter(torch.randn(output_dim, state_dim) * 0.1)
        
        # Feedforward matrix D (output_dim x input_dim)
        self.D = nn.Parameter(torch.randn(output_dim, input_dim) * 0.1)
        
        # Discretization parameter (learnable time step)
        self.log_dt = nn.Parameter(torch.zeros(1))
        
    def _initialize_A(self) -> torch.Tensor:
        """Initialize A matrix with diagonal dominance for stability."""
        A = torch.randn(self.state_dim, self.state_dim) * 0.05
        # Make diagonal negative for stability (eigenvalues with negative real parts)
        A.diagonal().copy_(torch.rand(self.state_dim) * -0.5 - 0.5)
        return A
        
    def discretize(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Discretize continuous-time matrices using zero-order hold.
        
        Returns:
            A_bar: Discrete state transition matrix
            B_bar: Discrete input matrix
        """
        dt = torch.exp(self.log_dt).clamp(max=1.0)  # Clamp for numerical stability
        
        # Zero-order hold discretization
        # A_bar = exp(A * dt) ≈ I + A * dt (first-order approximation for efficiency)
        A_bar = torch.eye(self.state_dim, device=self.A.device) + self.A * dt
        B_bar = self.B * dt
        
        return A_bar, B_bar
    
    def forward(self, x: torch.Tensor, hidden: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through the SSM.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len, input_dim)
            hidden: Initial hidden state of shape (batch_size, state_dim)
        
        Returns:
            output: Output tensor of shape (batch_size, seq_len, output_dim)
            hidden: Final hidden state of shape (batch_size, state_dim)
        """
        batch_size, seq_len, _ = x.shape
        
        # Initialize hidden state if not provided
        if hidden is None:
            hidden = torch.zeros(batch_size, self.state_dim, device=x.device)
        
        # Discretize the continuous-time system
        A_bar, B_bar = self.discretize()
        
        outputs = []
        
        # Process sequence step by step
        for t in range(seq_len):
            x_t = x[:, t, :]  # (batch_size, input_dim)
            
            # State update: h_t = A_bar @ h_{t-1} + B_bar @ x_t
            hidden = torch.matmul(hidden, A_bar.T) + torch.matmul(x_t, B_bar.T)
            
            # Output: y_t = C @ h_t + D @ x_t
            y_t = torch.matmul(hidden, self.C.T) + torch.matmul(x_t, self.D.T)
            
            outputs.append(y_t)
        
        # Stack outputs along sequence dimension
        output = torch.stack(outputs, dim=1)  # (batch_size, seq_len, output_dim)
        
        return output, hidden


class AttentionPooling(nn.Module):
    """Attention-based pooling for sequence aggregation."""
    
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_len, hidden_dim)
        Returns:
            pooled: (batch_size, hidden_dim)
        """
        # Compute attention weights
        attn_weights = self.attention(x)  # (batch_size, seq_len, 1)
        attn_weights = torch.softmax(attn_weights, dim=1)
        
        # Weighted sum
        pooled = torch.sum(x * attn_weights, dim=1)  # (batch_size, hidden_dim)
        return pooled


class DDoSDetector(nn.Module):
    """
    Complete DDoS Detection Model using State Space Model.
    
    This model processes temporal network traffic statistics and outputs
    attack probabilities with confidence scores.
    """
    
    def __init__(
        self,
        input_dim: int = 8,
        state_dim: int = 32,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.1,
        use_attention: bool = True
    ):
        """
        Initialize the DDoS Detector.
        
        Args:
            input_dim: Number of traffic features per time step
            state_dim: Dimension of SSM hidden state
            hidden_dim: Dimension of feedforward layers
            num_layers: Number of SSM layers
            dropout: Dropout probability
            use_attention: Whether to use attention pooling
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.state_dim = state_dim
        self.use_attention = use_attention
        
        # Input normalization
        self.input_norm = nn.LayerNorm(input_dim)
        
        # Stack of SSM layers
        self.ssm_layers = nn.ModuleList([
            LinearSSM(
                input_dim=input_dim if i == 0 else state_dim,
                state_dim=state_dim,
                output_dim=state_dim
            )
            for i in range(num_layers)
        ])
        
        # Layer normalization for each SSM layer
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(state_dim) for _ in range(num_layers)
        ])
        
        # Dropout layers
        self.dropout = nn.Dropout(dropout)
        
        # Attention pooling (optional)
        if use_attention:
            self.attention_pool = AttentionPooling(state_dim)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        # Confidence estimation head
        self.confidence_head = nn.Sequential(
            nn.Linear(state_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        # Attack type classifier (multi-class for different DDoS types)
        self.attack_type_classifier = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 5)  # 5 attack types: Normal, SYN Flood, UDP Flood, HTTP Flood, DNS Amplification
        )
    
    def forward(self, x: torch.Tensor, return_confidence: bool = True, return_attack_type: bool = False) -> Dict:
        """
        Forward pass for DDoS detection.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len, input_dim)
            return_confidence: Whether to compute confidence scores
            return_attack_type: Whether to classify attack type
        
        Returns:
            Dictionary containing predictions and metadata
        """
        # Normalize input
        x = self.input_norm(x)
        
        # Pass through SSM layers
        hidden = None
        for i, (ssm, norm) in enumerate(zip(self.ssm_layers, self.layer_norms)):
            x, hidden = ssm(x, hidden)
            x = norm(x)
            x = self.dropout(x)
        
        # Get final time step representation
        if self.use_attention:
            final_state = self.attention_pool(x)  # (batch_size, state_dim)
        else:
            final_state = x[:, -1, :]  # (batch_size, state_dim)
        
        # Compute attack probabilities for all time steps
        logits = self.classifier(x)  # (batch_size, seq_len, 1)
        logits = logits.squeeze(-1)  # (batch_size, seq_len)
        
        # Final prediction
        final_prediction = self.classifier(final_state.unsqueeze(1)).squeeze()  # (batch_size,)
        
        result = {
            'logits': logits,
            'final_prediction': final_prediction,
            'hidden_state': final_state
        }
        
        # Compute confidence if requested
        if return_confidence:
            confidence = self.confidence_head(final_state).squeeze(-1)  # (batch_size,)
            result['confidence'] = confidence
        
        # Classify attack type if requested
        if return_attack_type:
            attack_logits = self.attack_type_classifier(final_state)  # (batch_size, 5)
            result['attack_type_logits'] = attack_logits
        
        return result
    
    def predict(self, x: torch.Tensor, threshold: float = 0.5) -> Dict:
        """
        Make predictions on input data.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len, input_dim)
            threshold: Classification threshold
        
        Returns:
            Dictionary with predictions and metadata
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(x, return_confidence=True, return_attack_type=True)
            
            # Binary predictions
            predictions = (output['final_prediction'] > threshold).long()
            
            # Attack type predictions
            attack_types = torch.argmax(output['attack_type_logits'], dim=1)
            
            return {
                'is_attack': predictions,
                'attack_probability': output['final_prediction'],
                'confidence': output['confidence'],
                'attack_type': attack_types,
                'attack_type_probs': torch.softmax(output['attack_type_logits'], dim=1)
            }
    
    def get_model_size(self) -> Dict[str, float]:
        """Calculate model size in MB."""
        param_size = 0
        for param in self.parameters():
            param_size += param.nelement() * param.element_size()
        
        buffer_size = 0
        for buffer in self.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        
        size_mb = (param_size + buffer_size) / 1024 / 1024
        
        return {
            'total_mb': size_mb,
            'params_mb': param_size / 1024 / 1024,
            'buffers_mb': buffer_size / 1024 / 1024,
            'num_parameters': sum(p.numel() for p in self.parameters())
        }


class QuantizedDDoSDetector(nn.Module):
    """
    Quantized version of DDoS Detector for even more efficient edge deployment.
    """
    
    def __init__(self, model: DDoSDetector):
        super().__init__()
        self.model = model
        
    @staticmethod
    def quantize_model(model: DDoSDetector) -> 'QuantizedDDoSDetector':
        """Apply dynamic quantization to the model."""
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {nn.Linear},
            dtype=torch.qint8
        )
        return QuantizedDDoSDetector(quantized_model)
    
    def forward(self, x: torch.Tensor, **kwargs) -> Dict:
        return self.model(x, **kwargs)
    
    def predict(self, x: torch.Tensor, threshold: float = 0.5) -> Dict:
        return self.model.predict(x, threshold)
