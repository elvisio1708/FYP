import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder

class ExerciseDataset(Dataset):
    def __init__(self, dataframe, features, target):
        self.n_samples = dataframe.shape[0]
        
        self.x = dataframe[features].values
        self.y = dataframe[target].values
        
        self.x = torch.tensor(self.x, dtype=torch.float32)
        self.y = torch.tensor(self.y, dtype=torch.int64)
    
    def __getitem__(self, index):
        return self.x[index], self.y[index]
    
    def __len__(self):
        return self.n_samples

class NeuralNet(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(NeuralNet, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size) 
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, num_classes)  
    
    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        return out
    
# Load the dataset
df = pd.read_csv('cleaned_dataset.csv')

# Encode categorical variables
le = LabelEncoder()
df['Level'] = le.fit_transform(df['Level'])

# Splitting dataset
features = df.columns.difference(['Level'])
X_train, X_test, y_train, y_test = train_test_split(df[features], df['Level'], test_size=0.2, random_state=42)

# Standardize features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Prepare dataset for training
train_dataset = ExerciseDataset(pd.DataFrame(X_train_scaled, columns=features), features, y_train)
test_dataset = ExerciseDataset(pd.DataFrame(X_test_scaled, columns=features), features, y_test)

train_loader = DataLoader(dataset=train_dataset, batch_size=64, shuffle=True)
test_loader = DataLoader(dataset=test_dataset, batch_size=64, shuffle=False)

# Hyperparameters
input_size = len(features)
hidden_size = 500  # Example value
num_classes = len(df['Level'].unique())
num_epochs = 20
learning_rate = 0.001

model = NeuralNet(input_size, hidden_size, num_classes)

# Loss and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

# Train the model
for epoch in range(num_epochs):
    for i, (inputs, labels) in enumerate(train_loader):  
        # Forward pass
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        
        # Backward and optimize
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if (i+1) % 100 == 0:
            print (f'Epoch [{epoch+1}/{num_epochs}], Step [{i+1}/{len(train_loader)}], Loss: {loss.item():.4f}')

torch.save(model.state_dict(), 'exercise_model.pth')

