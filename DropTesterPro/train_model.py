import os
import cv2
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

# --- Configuration ---
IMG_WIDTH = 128
IMG_HEIGHT = 128
BATCH_SIZE = 32
EPOCHS = 20 # Number of times the model sees the entire dataset
TRAINING_DIR = "training_data"
MODEL_SAVE_PATH = "bottle_drop_model.h5"

def load_data(data_dir):
    """Loads images and labels from the training_data directory."""
    images = []
    labels = []
    class_names = sorted(os.listdir(data_dir))
    
    if len(class_names) != 2:
        print(f"Error: Expected 2 class folders (e.g., PASS, FAIL), but found {len(class_names)}.")
        return None, None

    label_map = {name.upper(): i for i, name in enumerate(class_names)}
    print(f"Class mapping: {label_map}")

    for class_name in class_names:
        class_path = os.path.join(data_dir, class_name)
        if not os.path.isdir(class_path):
            continue
        
        label = label_map[class_name.upper()]
        
        for img_name in os.listdir(class_path):
            img_path = os.path.join(class_path, img_name)
            try:
                img = cv2.imread(img_path)
                if img is None:
                    print(f"Warning: Could not read image {img_path}. Skipping.")
                    continue
                
                # The model will analyze pairs of images (before/after) side-by-side
                # So we resize to a wide format
                img = cv2.resize(img, (IMG_WIDTH * 2, IMG_HEIGHT))
                images.append(img)
                labels.append(label)
            except Exception as e:
                print(f"Warning: Error processing {img_path}: {e}. Skipping.")

    if not images:
        return None, None

    return np.array(images), np.array(labels)

def build_model():
    """Builds and compiles the CNN model."""
    model = tf.keras.models.Sequential([
        # Input layer: Normalize pixel values from 0-255 to 0-1
        tf.keras.layers.Rescaling(1./255, input_shape=(IMG_HEIGHT, IMG_WIDTH * 2, 3)),
        
        # Convolutional layers to learn features
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D(2, 2),
        
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D(2, 2),
        
        tf.keras.layers.Conv2D(128, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D(2, 2),
        
        # Flatten the results to feed into a dense layer
        tf.keras.layers.Flatten(),
        
        # Dense (fully connected) layers
        tf.keras.layers.Dense(512, activation='relu'),
        tf.keras.layers.Dropout(0.5), # Dropout to prevent overfitting
        
        # Output layer: 1 neuron with sigmoid for binary classification (PASS/FAIL)
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    model.compile(optimizer='adam',
                  loss='binary_crossentropy',
                  metrics=['accuracy'])
    
    return model

if __name__ == "__main__":
    print("--- Starting AI Model Training ---")
    
    if not os.path.exists(TRAINING_DIR):
        print(f"Error: Training directory '{TRAINING_DIR}' not found.")
        exit()

    # 1. Load Data
    print("Step 1: Loading and preprocessing images...")
    images, labels = load_data(TRAINING_DIR)
    
    if images is None or labels is None or len(images) < 20:
        print("Error: Not enough valid images found to start training. Need at least 10 per class.")
        exit()
        
    print(f"Loaded {len(images)} images.")

    # 2. Split Data
    print("Step 2: Splitting data into training and validation sets...")
    X_train, X_val, y_train, y_val = train_test_split(
        images, labels, test_size=0.2, random_state=42, stratify=labels
    )
    print(f"Training set: {len(X_train)} images. Validation set: {len(X_val)} images.")

    # 3. Build Model
    print("Step 3: Building the neural network...")
    model = build_model()
    model.summary()

    # 4. Train Model
    print(f"\nStep 4: Starting training for {EPOCHS} epochs...")
    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_val, y_val),
        verbose=1
    )

    # 5. Save Model
    print("\nStep 5: Saving the trained model...")
    model.save(MODEL_SAVE_PATH)
    
    print(f"--- Training Complete! ---")
    print(f"Model saved successfully to '{MODEL_SAVE_PATH}'")
    
    # Evaluate final accuracy
    final_loss, final_acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"Final validation accuracy: {final_acc*100:.2f}%")