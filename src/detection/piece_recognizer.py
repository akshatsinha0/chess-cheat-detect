# src/detection/piece_recognizer.py

import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import chess

class PieceRecognizer:
    """
    CNN-based chess piece recognition system.
    Recognizes chess pieces from square images.
    """
    
    # Mapping from class index to chess piece
    PIECE_CLASSES = {
        0: None,  # Empty square
        1: chess.Piece(chess.PAWN, chess.WHITE),
        2: chess.Piece(chess.KNIGHT, chess.WHITE),
        3: chess.Piece(chess.BISHOP, chess.WHITE),
        4: chess.Piece(chess.ROOK, chess.WHITE),
        5: chess.Piece(chess.QUEEN, chess.WHITE),
        6: chess.Piece(chess.KING, chess.WHITE),
        7: chess.Piece(chess.PAWN, chess.BLACK),
        8: chess.Piece(chess.KNIGHT, chess.BLACK),
        9: chess.Piece(chess.BISHOP, chess.BLACK),
        10: chess.Piece(chess.ROOK, chess.BLACK),
        11: chess.Piece(chess.QUEEN, chess.BLACK),
        12: chess.Piece(chess.KING, chess.BLACK)
    }
    
    def __init__(self, model_path=None):
        """
        Initialize the piece recognizer.
        Args:
            model_path (str): Path to trained model. If None, creates new model.
        """
        if model_path and os.path.exists(model_path):
            self.model = tf.keras.models.load_model(model_path)
        else:
            self.model = self.build_model()
            
    def build_model(self):
        """
        Build a CNN model for piece recognition.
        Returns:
            tf.keras.Model: Compiled CNN model.
        """
        model = models.Sequential([
            layers.Input(shape=(50, 50, 3)),
            
            # Convolutional layers
            layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            
            # Dense layers
            layers.Flatten(),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(13, activation='softmax')  # 13 classes (12 pieces + empty)
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def preprocess_square(self, square_img):
        """
        Preprocess a square image for piece recognition.
        Args:
            square_img (ndarray): Input square image.
        Returns:
            ndarray: Preprocessed image ready for model input.
        """
        # Resize to 50x50 if needed
        if square_img.shape[:2] != (50, 50):
            square_img = cv2.resize(square_img, (50, 50))
        
        # Normalize pixel values
        square_img = square_img.astype(np.float32) / 255.0
        
        # Add batch dimension
        return np.expand_dims(square_img, axis=0)
    
    def recognize(self, square_img):
        """
        Recognize a chess piece from a square image.
        Args:
            square_img (ndarray): Square image from the board.
        Returns:
            chess.Piece or None: Recognized piece or None if empty.
        """
        # Preprocess the image
        processed_img = self.preprocess_square(square_img)
        
        # Get prediction
        predictions = self.model.predict(processed_img, verbose=0)
        predicted_class = np.argmax(predictions[0])
        confidence = predictions[0][predicted_class]
        
        # Return piece if confidence is high enough
        if confidence > 0.7:  # Confidence threshold
            return self.PIECE_CLASSES.get(predicted_class)
        return None
    
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=20, batch_size=32):
        """
        Train the piece recognition model.
        Args:
            X_train: Training images
            y_train: Training labels (one-hot encoded)
            X_val: Validation images
            y_val: Validation labels
            epochs: Number of training epochs
            batch_size: Batch size for training
        """
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
        
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=validation_data,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
                tf.keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.5)
            ]
        )
        
        return history
    
    def save_model(self, path):
        """Save the trained model."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.model.save(path)
