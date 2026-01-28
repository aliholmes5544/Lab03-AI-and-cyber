from flask import Flask, render_template, request
import os
from model import predict_survival, train_model

app = Flask(__name__)


# Train model if it doesn't exist
if not os.path.exists('titanic_model.pkl'):
    print("Model not found. Training new model...")
    train_model()


@app.route('/')
def index():
    """Render the input form."""
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    """Process form data and return prediction."""
    try:
        # Get form data
        pclass = int(request.form['pclass'])
        sex = request.form['sex']
        age = float(request.form['age'])
        sibsp = int(request.form['sibsp'])
        parch = int(request.form['parch'])
        fare = float(request.form['fare'])
        embarked = request.form['embarked']

        # Validate inputs
        if pclass not in [1, 2, 3]:
            raise ValueError("Pclass must be 1, 2, or 3")
        if sex not in ['male', 'female']:
            raise ValueError("Sex must be 'male' or 'female'")
        if age < 0 or age > 120:
            raise ValueError("Age must be between 0 and 120")
        if sibsp < 0:
            raise ValueError("SibSp must be non-negative")
        if parch < 0:
            raise ValueError("Parch must be non-negative")
        if fare < 0:
            raise ValueError("Fare must be non-negative")
        if embarked not in ['C', 'Q', 'S']:
            raise ValueError("Embarked must be 'C', 'Q', or 'S'")

        # Make prediction
        result = predict_survival(pclass, sex, age, sibsp, parch, fare, embarked)

        return render_template(
            'index.html',
            prediction=result,
            form_data=request.form
        )

    except ValueError as e:
        return render_template(
            'index.html',
            error=str(e),
            form_data=request.form
        )
    except Exception as e:
        return render_template(
            'index.html',
            error=f"An error occurred: {str(e)}",
            form_data=request.form
        )


if __name__ == '__main__':
    app.run(debug=True)
