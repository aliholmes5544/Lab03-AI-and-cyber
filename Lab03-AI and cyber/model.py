import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import seaborn as sns


def load_and_preprocess_data():
    """Load Titanic dataset and preprocess it."""
    # Load Titanic dataset from seaborn
    df = sns.load_dataset('titanic')

    # Select relevant features
    features = ['pclass', 'sex', 'age', 'sibsp', 'parch', 'fare', 'embarked']
    target = 'survived'

    # Create a copy with selected columns
    data = df[features + [target]].copy()

    # Handle missing values
    data['age'] = data['age'].fillna(data['age'].median())
    data['fare'] = data['fare'].fillna(data['fare'].median())
    data['embarked'] = data['embarked'].fillna(data['embarked'].mode()[0])

    # Encode categorical variables
    label_encoders = {}

    # Encode 'sex'
    le_sex = LabelEncoder()
    data['sex'] = le_sex.fit_transform(data['sex'])
    label_encoders['sex'] = le_sex

    # Encode 'embarked'
    le_embarked = LabelEncoder()
    data['embarked'] = le_embarked.fit_transform(data['embarked'])
    label_encoders['embarked'] = le_embarked

    X = data[features]
    y = data[target]

    return X, y, label_encoders


def train_model():
    """Train the classification model and save it."""
    print("Loading and preprocessing data...")
    X, y, label_encoders = load_and_preprocess_data()

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train RandomForest classifier
    print("Training RandomForest classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    print(f"Training accuracy: {train_score:.4f}")
    print(f"Test accuracy: {test_score:.4f}")

    # Save model and encoders
    model_data = {
        'model': model,
        'label_encoders': label_encoders
    }
    joblib.dump(model_data, 'titanic_model.pkl')
    print("Model saved to titanic_model.pkl")

    return model, label_encoders


def load_model():
    """Load the trained model from file."""
    model_data = joblib.load('titanic_model.pkl')
    return model_data['model'], model_data['label_encoders']


def predict_survival(pclass, sex, age, sibsp, parch, fare, embarked):
    """Make a prediction for a single passenger."""
    model, label_encoders = load_model()

    # Encode categorical inputs
    sex_encoded = label_encoders['sex'].transform([sex])[0]
    embarked_encoded = label_encoders['embarked'].transform([embarked])[0]

    # Create feature array
    features = np.array([[pclass, sex_encoded, age, sibsp, parch, fare, embarked_encoded]])

    # Make prediction
    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0]

    return {
        'survived': bool(prediction),
        'probability': float(probability[1])
    }


if __name__ == '__main__':
    train_model()
