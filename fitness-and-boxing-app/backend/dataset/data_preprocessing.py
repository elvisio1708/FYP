import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
import pandas as pd
import numpy as np

# Load the dataset
df = pd.read_csv('cleaned_megaGymDataset.csv')

# Basic cleaning: Remove rows with missing values in 'Equipment' column
df = df.dropna(subset=['Equipment'])

# Optional: More sophisticated cleaning based on your earlier steps

# Encode categorical features as dummy variables
categorical_features = ['Type', 'BodyPart', 'Equipment']
df_processed = pd.get_dummies(df[categorical_features])

# Assuming 'Level' is your target and it's categorical
y = df['Level']
le = LabelEncoder()
y_encoded = le.fit_transform(y)  # Convert 'Level' to numerical form

# Splitting the dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(df_processed, y_encoded, test_size=0.2, random_state=42)