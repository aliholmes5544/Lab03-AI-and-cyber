# Titanic Survival Predictor

A machine learning web application that predicts whether a passenger would have survived the Titanic disaster based on their characteristics.

## Features

- Predict survival probability using RandomForest Classifier
- Bilingual support (English / Arabic)
- Light and Dark theme modes
- Interactive modals with visual feedback
- Responsive design

## Technologies

- **Backend**: Python, Flask
- **ML Model**: Scikit-learn RandomForest
- **Frontend**: HTML, CSS, JavaScript

## Usage

1. Install dependencies:
   ```
   pip install flask scikit-learn pandas numpy
   ```

2. Run the application:
   ```
   python app.py
   ```

3. Open http://localhost:5000 in your browser

## Input Features

- Passenger Class (1st, 2nd, 3rd)
- Sex (Male/Female)
- Age
- Fare
- Siblings/Spouses aboard
- Parents/Children aboard
- Port of Embarkation (Southampton, Cherbourg, Queenstown)

## License

MIT License
