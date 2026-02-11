from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

from models.user import User


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired(), Length(min=3, max=64)
    ])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[
        DataRequired(), Length(min=6)
    ])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match")
    ])
    submit = SubmitField("Register")

    def validate_username(self, field):
        if User.get_by_username(field.data):
            raise ValidationError("Username already taken.")

    def validate_email(self, field):
        if User.get_by_email(field.data):
            raise ValidationError("Email already registered.")
