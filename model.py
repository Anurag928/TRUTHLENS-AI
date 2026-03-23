"""
Deepfake Detection Model Architecture
This module defines the neural network model for video-based deepfake detection.
The model uses a CNN-LSTM architecture to process video sequences.
"""

import torch
import torch.nn as nn
import torchvision.models as models


class Model(nn.Module):
    """
    Video-based Deepfake Detection Model

    Architecture matches the saved checkpoint exactly:
    - CNN backbone: ResNeXt-50 32x4d (attribute: self.model)
    - LSTM: input=2048, hidden=2048, 1 layer, unidirectional (attribute: self.lstm)
    - Linear classifier: Linear(2048, num_classes) (attribute: self.linear1)

    NOTE: Do NOT change the backbone to ResNet50 or alter the LSTM/FC structure —
    doing so causes shape mismatches when loading the checkpoint weights.

    Args:
        num_classes (int): Number of output classes (default: 2)
    """

    def __init__(self, num_classes=2):
        super(Model, self).__init__()

        self.cnn_output_size = 2048

        # CNN Backbone: ResNeXt-50 32x4d — must match the training checkpoint.
        resnext = models.resnext50_32x4d(pretrained=False)
        # Remove the final FC layer; adaptive avg-pool gives [*, 2048, 1, 1].
        self.model = nn.Sequential(*list(resnext.children())[:-1])

        # LSTM: single layer, unidirectional, hidden_size=2048 — matches checkpoint.
        self.lstm = nn.LSTM(
            input_size=self.cnn_output_size,
            hidden_size=2048,
            num_layers=1,
            batch_first=True,
            bidirectional=False,
            bias=False,
        )

        # Single linear classifier — checkpoint key is 'linear1'.
        self.linear1 = nn.Linear(2048, num_classes)

    def forward(self, x):
        """
        Forward pass.

        Args:
            x: [batch_size, sequence_length, 3, 224, 224]

        Returns:
            logits: [batch_size, num_classes]
        """
        batch_size, seq_len, c, h, w = x.size()

        # Flatten batch and time dims so CNN processes all frames at once.
        x = x.view(batch_size * seq_len, c, h, w)
        cnn_features = self.model(x)                                # [B*S, 2048, 1, 1]
        cnn_features = cnn_features.view(batch_size * seq_len, -1)  # [B*S, 2048]
        cnn_features = cnn_features.view(batch_size, seq_len, -1)   # [B, S, 2048]

        # Temporal modeling — take the last LSTM output.
        lstm_out, _ = self.lstm(cnn_features)   # [B, S, 2048]
        last_output = lstm_out[:, -1, :]        # [B, 2048]

        return self.linear1(last_output)        # [B, num_classes]


class SimpleCNNModel(nn.Module):
    """
    Simplified CNN-based model for faster inference (alternative architecture)
    Uses average pooling across frames instead of LSTM
    
    Args:
        num_classes (int): Number of output classes (default: 2)
        dropout (float): Dropout probability (default: 0.3)
    """
    
    def __init__(self, num_classes=2, dropout=0.3):
        super(SimpleCNNModel, self).__init__()
        
        # CNN Backbone
        resnet = models.resnet50(pretrained=False)
        self.cnn = nn.Sequential(*list(resnet.children())[:-1])
        self.cnn_output_size = 2048
        
        # Classification head
        self.fc = nn.Sequential(
            nn.Linear(self.cnn_output_size, 512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes)
        )
        
    def forward(self, x):
        """
        Forward pass with temporal averaging
        
        Args:
            x: Input tensor of shape [batch_size, sequence_length, channels, height, width]
        
        Returns:
            Output logits of shape [batch_size, num_classes]
        """
        batch_size, seq_len, c, h, w = x.size()
        
        # Reshape to process all frames
        x = x.view(batch_size * seq_len, c, h, w)
        
        # Extract features
        features = self.cnn(x)
        features = features.view(batch_size * seq_len, -1)
        
        # Reshape and average across time
        features = features.view(batch_size, seq_len, -1)
        features = torch.mean(features, dim=1)  # [batch_size, cnn_output_size]
        
        # Classification
        output = self.fc(features)
        
        return output


if __name__ == "__main__":
    # Test the model
    print("Testing Model architecture...")
    
    # Keep the sanity-check input lightweight to avoid excessive CPU/RAM pressure.
    # Shape: [batch_size=1, seq_len=4, channels=3, height=224, width=224]
    dummy_input = torch.randn(1, 4, 3, 224, 224)
    
    # Test main model
    model = Model(num_classes=2)
    output = model(dummy_input)
    print(f"Model output shape: {output.shape}")  # Should be [2, 2]
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Test simple model
    simple_model = SimpleCNNModel(num_classes=2)
    simple_output = simple_model(dummy_input)
    print(f"\nSimpleCNNModel output shape: {simple_output.shape}")  # Should be [2, 2]
    print(f"SimpleCNNModel parameters: {sum(p.numel() for p in simple_model.parameters()):,}")
    
    print("\n✓ Model architecture test passed!")
