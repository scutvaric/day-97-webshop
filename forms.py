from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, TextAreaField, FloatField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Length, Email
from flask_wtf.file import FileField, FileAllowed


# WTForm for creating a blog post
class AddItem(FlaskForm):
    name = StringField(
        "Item name",
        render_kw={"id": "name", "maxlength": 50, "oninput": "updateCount('name', 50)"},
        validators=[
            DataRequired(),
            Length(max=50, message="Name must be at most 50 characters long.")
        ]
    )
    description = TextAreaField(
        "Item description",
        render_kw={"id": "description", "maxlength": 80, "oninput": "updateCount('description', 80)"},
        validators=[
            DataRequired(),
            Length(max=80, message="Description must be at most 80 characters long.")
        ]
    )

    image = FileField("Upload Image", validators=[DataRequired(), FileAllowed(['jpg', 'png', 'jpeg'], "Images only!")])
    price = FloatField("Price (USD)", validators=[DataRequired(), NumberRange(min=0)])
    quantity = IntegerField("Available Stock", validators=[DataRequired(), NumberRange(min=0)])

    submit = SubmitField("Submit")


# Create a form to register new users
class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


# Create a form to login existing users
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")
