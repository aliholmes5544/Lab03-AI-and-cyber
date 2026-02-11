from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField, DateField, HiddenField
from wtforms.validators import DataRequired, Length, Optional


CLASSIFICATION_CHOICES = [
    ("0", "Unclassified"),
    ("1", "Confidential"),
    ("2", "Secret"),
    ("3", "Top Secret"),
]

SORT_CHOICES = [
    ("created_at", "Upload Date"),
    ("updated_at", "Last Updated"),
    ("title", "Title"),
    ("file_size", "File Size"),
    ("classification", "Classification"),
]

SORT_ORDER_CHOICES = [
    ("desc", "Descending"),
    ("asc", "Ascending"),
]

TAG_COLOR_CHOICES = [
    ("primary", "Blue"),
    ("secondary", "Gray"),
    ("success", "Green"),
    ("danger", "Red"),
    ("warning", "Yellow"),
    ("info", "Cyan"),
    ("dark", "Dark"),
]


def coerce_int_or_none(value):
    """Coerce value to int, or return None for empty strings."""
    if value == "" or value is None:
        return None
    return int(value)


class UploadForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    classification = SelectField("Classification", choices=CLASSIFICATION_CHOICES,
                                 validators=[DataRequired()])
    file = FileField("File", validators=[FileRequired()])
    submit = SubmitField("Upload")


class SearchForm(FlaskForm):
    query = StringField("Search", validators=[Optional()])
    classification = SelectField("Classification", choices=[("", "All Levels")] + CLASSIFICATION_CHOICES,
                                 validators=[Optional()])
    submit = SubmitField("Search")


class ClassificationForm(FlaskForm):
    classification = SelectField("Classification", choices=CLASSIFICATION_CHOICES,
                                 validators=[DataRequired()])
    submit = SubmitField("Update Classification")


class CommentForm(FlaskForm):
    content = TextAreaField("Comment", validators=[DataRequired(), Length(min=1, max=2000)])
    submit = SubmitField("Add Comment")


class TagForm(FlaskForm):
    name = StringField("Tag Name", validators=[DataRequired(), Length(min=1, max=50)])
    color = SelectField("Color", choices=TAG_COLOR_CHOICES, validators=[DataRequired()])
    submit = SubmitField("Create Tag")


class AddTagForm(FlaskForm):
    tag_id = SelectField("Tag", coerce=coerce_int_or_none, validators=[DataRequired()])
    submit = SubmitField("Add Tag")


class ReuploadForm(FlaskForm):
    file = FileField("New Version", validators=[FileRequired()])
    change_notes = TextAreaField("Change Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Upload New Version")


class BulkActionForm(FlaskForm):
    document_ids = HiddenField("Document IDs", validators=[DataRequired()])
    action = SelectField("Action", choices=[
        ("download", "Download as ZIP"),
        ("delete", "Delete Selected"),
    ], validators=[DataRequired()])
    submit = SubmitField("Apply")


class AdvancedSearchForm(FlaskForm):
    query = StringField("Search", validators=[Optional()])
    classification = SelectField("Classification", choices=[("", "All Levels")] + CLASSIFICATION_CHOICES,
                                 validators=[Optional()])
    sort_by = SelectField("Sort By", choices=SORT_CHOICES, validators=[Optional()])
    sort_order = SelectField("Order", choices=SORT_ORDER_CHOICES, validators=[Optional()])
    date_from = DateField("From Date", validators=[Optional()])
    date_to = DateField("To Date", validators=[Optional()])
    tag_id = SelectField("Tag", coerce=coerce_int_or_none, validators=[Optional()])
    submit = SubmitField("Search")


class ExpirationForm(FlaskForm):
    expires_at = DateField("Expiration Date", validators=[Optional()])
    submit = SubmitField("Set Expiration")
