"""
State Space Model for DDoS Detection in IoT Edge Environments

This module implements a DDoS detection system using the S5
(Simplified Structured State Space) model as the sequence backbone.

Backbone:  s5-pytorch  (pip install s5-pytorch)
           S5Block = S5 operator + LayerNorm + FFN-GLU + residual connection
           Paper: "Simplified State Space Layers for Sequence Modeling"
                  Smith, Warrington, Linderman — ICLR 2023 (Oral)

Drop-in change from the original:
    LinearSSM  →  S5Block (one per layer)

Everything else — AttentionPooling, DDoSDetector heads, QuantizedDDoSDetector,
all public method signatures, input/output shapes — is unchanged so that
trainer.py, realtime_detector.py, demo.py, etc. work with zero edits.

Requirements
------------
    pip install s5-pytorch          # the S5 / S5Block classes
    Python >= 3.10                  # s5-pytorch uses match/case
    PyTorch >= 2.0                  # s5-pytorch uses torch.vmap
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Optional, Dict, List

# ---------------------------------------------------------------------------
# S5 import — the only external dependency that changed
# ---------------------------------------------------------------------------
from s5 import S5Block          # S5 operator + LayerNorm + GLU-FFN + residual


# ===========================================================================
# AttentionPooling  (UNCHANGED)
# ===========================================================================
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
        attn_weights = self.attention(x)                # (B, T, 1)
        attn_weights = torch.softmax(attn_weights, dim=1)
        pooled = torch.sum(x * attn_weights, dim=1)     # (B, hidden_dim)
        return pooled


# ===========================================================================
# DDoSDetector  — backbone swapped to S5Block
# ===========================================================================
class DDoSDetector(nn.Module):
    """
    DDoS Detection Model using S5 (Simplified Structured State Space).

    Architecture per layer:
        input_proj (only layer 0):  Linear(input_dim -> state_dim)
        S5Block:                    S5 + LayerNorm + FFN-GLU + residual
                                    input & output dim = state_dim

    Then the shared classification / confidence / attack-type heads are
    identical to the original LinearSSM version.
    """

    def __init__(
        self,
        input_dim: int = 8,
        state_dim: int = 32,          # d_model for every S5Block
        hidden_dim: int = 64,         # width of the MLP classification heads
        num_layers: int = 2,          # number of S5Block layers
        dropout: float = 0.1,
        use_attention: bool = True,
        s5_state_dim: int = 64        # internal S5 state dimension (d_state)
    ):
        """
        Args:
            input_dim:      Number of traffic features per time step (8).
            state_dim:      Dimension flowing through S5 blocks (= d_model).
            hidden_dim:     Width of the MLP heads after pooling.
            num_layers:     How many S5Block layers to stack.
            dropout:        Dropout probability (applied between blocks).
            use_attention:  Use attention pooling (True) or last-step (False).
            s5_state_dim:   Internal recurrent state size inside each S5Block
                            (the "d_state" argument). Larger = more memory,
                            richer dynamics. 64 is a safe default for edge.
        """
        super().__init__()

        self.input_dim = input_dim
        self.state_dim = state_dim
        self.use_attention = use_attention

        # ------------------------------------------------------------------
        # 1. Input projection  (input_dim -> state_dim)
        # S5Block requires input & output to share the same dimension
        # (d_model). Our raw features are 8-d; state_dim is 32.
        # A single Linear + LayerNorm bridges that gap.
        # ------------------------------------------------------------------
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, state_dim),
            nn.LayerNorm(state_dim)
        )

        # ------------------------------------------------------------------
        # 2. Stack of S5Blocks
        #    S5Block(d_model, d_state, bidir=False)
        #      d_model  – input & output feature dim (= state_dim)
        #      d_state  – internal recurrent state dim
        #      bidir    – False -> causal (past only), critical for real-time
        # ------------------------------------------------------------------
        self.s5_blocks = nn.ModuleList([
            S5Block(state_dim, s5_state_dim, bidir=False)
            for _ in range(num_layers)
        ])

        # Dropout between blocks (S5Block already has its own internal
        # LayerNorm, so we do NOT add extra LayerNorms here).
        self.dropout = nn.Dropout(dropout)

        # ------------------------------------------------------------------
        # 3. Attention pooling (optional)
        # ------------------------------------------------------------------
        if use_attention:
            self.attention_pool = AttentionPooling(state_dim)

        # ------------------------------------------------------------------
        # 4. Classification heads  (UNCHANGED from original)
        # ------------------------------------------------------------------
        # Binary: is this an attack?
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

        # Confidence estimation
        self.confidence_head = nn.Sequential(
            nn.Linear(state_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )

        # Multi-class attack type  (Normal / SYN / UDP / HTTP / DNS-Amp)
        self.attack_type_classifier = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 5)
        )

    # ----------------------------------------------------------------------
    # forward  — only the backbone section changed
    # ----------------------------------------------------------------------
    def forward(
        self,
        x: torch.Tensor,
        return_confidence: bool = True,
        return_attack_type: bool = False
    ) -> Dict:
        """
        Args:
            x: (batch_size, seq_len, input_dim)          e.g. (32, 60, 8)
            return_confidence: include confidence scores in output
            return_attack_type: include attack-type logits in output

        Returns:
            Dictionary with keys matching the original model exactly.
        """
        # --- 1. Project input features to state_dim -------------------------
        x = self.input_proj(x)          # (B, T, state_dim)

        # --- 2. Pass through S5Block stack ----------------------------------
        for block in self.s5_blocks:
            x = block(x)               # (B, T, state_dim)  — residual is
                                        #   handled inside S5Block
            x = self.dropout(x)

        # --- 3. Pool the sequence into a single vector ----------------------
        if self.use_attention:
            final_state = self.attention_pool(x)   # (B, state_dim)
        else:
            final_state = x[:, -1, :]              # (B, state_dim)

        # --- 4. Heads (identical to original) -------------------------------
        # Per-timestep logits (kept for compatibility with trainer)
        logits = self.classifier(x).squeeze(-1)    # (B, T)

        # Final single prediction from the pooled state
        final_pred_logits = self.classifier(
            final_state.unsqueeze(1)
        )                                          # (B, 1, 1)
        final_prediction = final_pred_logits.squeeze(-1).squeeze(-1)  # (B,)

        result = {
            'logits':           logits,
            'final_prediction': final_prediction,
            'hidden_state':     final_state
        }

        if return_confidence:
            result['confidence'] = self.confidence_head(final_state).squeeze(-1)

        if return_attack_type:
            result['attack_type_logits'] = self.attack_type_classifier(final_state)

        return result

    # ----------------------------------------------------------------------
    # predict  (UNCHANGED)
    # ----------------------------------------------------------------------
    def predict(self, x: torch.Tensor, threshold: float = 0.5) -> Dict:
        """
        Args:
            x: (batch_size, seq_len, input_dim)
            threshold: classification threshold

        Returns:
            Dictionary with is_attack, attack_probability, confidence,
            attack_type, attack_type_probs — same keys as original.
        """
        self.eval()
        with torch.no_grad():
            output = self.forward(x, return_confidence=True, return_attack_type=True)

            predictions  = (output['final_prediction'] > threshold).long()
            attack_types = torch.argmax(output['attack_type_logits'], dim=1)

            return {
                'is_attack':            predictions,
                'attack_probability':   output['final_prediction'],
                'confidence':           output['confidence'],
                'attack_type':          attack_types,
                'attack_type_probs':    torch.softmax(output['attack_type_logits'], dim=1)
            }

    # ----------------------------------------------------------------------
    # get_model_size  (UNCHANGED)
    # ----------------------------------------------------------------------
    def get_model_size(self) -> Dict[str, float]:
        """Calculate model size in MB."""
        param_size   = sum(p.nelement() * p.element_size() for p in self.parameters())
        buffer_size  = sum(b.nelement() * b.element_size() for b in self.buffers())
        size_mb      = (param_size + buffer_size) / 1024 / 1024

        return {
            'total_mb':        size_mb,
            'params_mb':       param_size  / 1024 / 1024,
            'buffers_mb':      buffer_size / 1024 / 1024,
            'num_parameters':  sum(p.numel() for p in self.parameters())
        }


# ===========================================================================
# QuantizedDDoSDetector  (UNCHANGED)
# ===========================================================================
class QuantizedDDoSDetector(nn.Module):
    """Quantized wrapper for edge deployment."""

    def __init__(self, model: DDoSDetector):
        super().__init__()
        self.model = model

    @staticmethod
    def quantize_model(model: DDoSDetector) -> 'QuantizedDDoSDetector':
        """Apply INT8 dynamic quantization."""
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
