from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from wtforms.widgets import ListWidget, CheckboxInput

from models.user import User

ROLE_CHOICES = [("user", "User"), ("admin", "Admin")]
CLEARANCE_CHOICES = [
    ("0", "Unclassified"),
    ("1", "Confidential"),
    ("2", "Secret"),
    ("3", "Top Secret"),
]

PERMISSION_CHOICES = [
    ("read_0", "Read Unclassified"),
    ("read_1", "Read Confidential"),
    ("read_2", "Read Secret"),
    ("read_3", "Read Top Secret"),
    ("write_0", "Write Unclassified"),
    ("write_1", "Write Confidential"),
    ("write_2", "Write Secret"),
    ("write_3", "Write Top Secret"),
]


class MultiCheckboxField(SelectMultipleField):
    """A multiple-select field displayed as checkboxes."""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class UserEditForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("New Password", validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[
        EqualTo("password", message="Passwords must match")
    ])
    role = SelectField("Role", choices=ROLE_CHOICES, validators=[DataRequired()])
    clearance = SelectField("Clearance", choices=CLEARANCE_CHOICES,
                            validators=[DataRequired()])
    is_active = BooleanField("Active")
    permissions = MultiCheckboxField("Permissions", choices=PERMISSION_CHOICES)
    grant_all_at_clearance = BooleanField("Grant all permissions at clearance level")
    submit = SubmitField("Update User")

    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        if field.data != self.original_email:
            if User.get_by_email(field.data):
                raise ValidationError("Email already registered.")


class UserAddForm(FlaskForm):
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
    role = SelectField("Role", choices=ROLE_CHOICES, validators=[DataRequired()])
    clearance = SelectField("Clearance", choices=CLEARANCE_CHOICES,
                            validators=[DataRequired()])
    permissions = MultiCheckboxField("Permissions", choices=PERMISSION_CHOICES)
    grant_all_at_clearance = BooleanField("Grant all permissions at clearance level")
    submit = SubmitField("Create User")

    def validate_username(self, field):
        if User.get_by_username(field.data):
            raise ValidationError("Username already taken.")

    def validate_email(self, field):
        if User.get_by_email(field.data):
            raise ValidationError("Email already registered.")
