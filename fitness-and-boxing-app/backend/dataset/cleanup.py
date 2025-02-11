import pandas as pd

# Load your dataset
df = pd.read_csv('megaGymDataset.csv')

# Check for missing values
# Fill in missing values in 'Desc' with an empty string
df['Desc'] = df['Desc'].fillna('')

# Fill in missing values in 'Equipment' with 'No Equipment'
df['Equipment'] = df['Equipment'].fillna('No Equipment')

# Fill in missing numerical values in 'Rating' with the average rating
df['Rating'] = df['Rating'].fillna(df['Rating'].mean())

# For 'RatingDesc', we can fill missing values with 'No Rating Description'
df['RatingDesc'] = df['RatingDesc'].fillna('No Rating Description')

# Save the cleaned dataset to a new CSV file
df.to_csv('cleaned_megaGymDataset.csv', index=False)
