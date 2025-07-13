import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import chess
class PieceRecognizer:
    PIECE_CLASSES = {
        0: None,
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
        if model_path and os.path.exists(model_path):
            self.model = tf.keras.models.load_model(model_path)
        else:
            self.model = self.build_model()
    def build_model(self):
        model = models.Sequential([
            layers.Input(shape=(50, 50, 3)),
            layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
            layers.MaxPooling2D((2, 2)),
            layers.Flatten(),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(13, activation='softmax')
        ])
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        return model
    def preprocess_square(self, square_img):
        if square_img.shape[:2] != (50, 50):
            square_img = cv2.resize(square_img, (50, 50))
        square_img = square_img.astype(np.float32) / 255.0
        return np.expand_dims(square_img, axis=0)
    def recognize(self, square_img):
        processed_img = self.preprocess_square(square_img)
        predictions = self.model.predict(processed_img, verbose=0)
        predicted_class = np.argmax(predictions[0])
        confidence = predictions[0][predicted_class]
        if confidence > 0.7:
            return self.PIECE_CLASSES.get(predicted_class)
        return None
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=20, batch_size=32):
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
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.model.save(path)
