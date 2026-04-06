import re
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import (
    StringField, PasswordField, SelectField, TextAreaField,
    DecimalField, IntegerField, DateField, BooleanField, HiddenField, MultipleFileField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Optional, NumberRange, ValidationError
)
from models import EXPENSE_CATEGORIES


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')


class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    # Optional on edit (leave blank to keep current), required min 6 chars if provided
    password = PasswordField('Password', validators=[Optional(), Length(min=6, max=128,
        message='Password must be at least 6 characters.')])
    confirm_password = PasswordField('Confirm Password', validators=[EqualTo('password',
        message='Passwords do not match.')])
    role = SelectField('Role', choices=[
        ('staff', 'Staff'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ])
    is_active = BooleanField('Active', default=True)


CURRENT_YEAR = 2026
YEAR_CHOICES = [(str(y), str(y)) for y in range(CURRENT_YEAR + 1, 1979, -1)]

BODY_TYPES = [
    ('', '-- Select --'),
    ('Sedan', 'Sedan'), ('Coupe', 'Coupe'), ('Hatchback', 'Hatchback'),
    ('Wagon', 'Wagon'), ('SUV', 'SUV'), ('Crossover', 'Crossover'),
    ('Minivan', 'Minivan'), ('Van', 'Van'), ('Pickup Truck', 'Pickup Truck'),
    ('Convertible', 'Convertible'), ('Sports Car', 'Sports Car'),
    ('Box Truck', 'Box Truck'), ('Other', 'Other'),
]

TRANSMISSION_CHOICES = [
    ('', '-- Select --'),
    ('Automatic', 'Automatic'), ('Manual', 'Manual'),
    ('CVT', 'CVT'), ('Semi-Auto', 'Semi-Auto'), ('Unknown', 'Unknown'),
]

FUEL_CHOICES = [
    ('', '-- Select --'),
    ('Gasoline', 'Gasoline'), ('Diesel', 'Diesel'), ('Hybrid', 'Hybrid'),
    ('Plug-in Hybrid', 'Plug-in Hybrid'), ('Electric', 'Electric'),
    ('Flex Fuel', 'Flex Fuel'), ('Other', 'Other'),
]

DRIVETRAIN_CHOICES = [
    ('', '-- Select --'),
    ('FWD', 'FWD - Front Wheel Drive'), ('RWD', 'RWD - Rear Wheel Drive'),
    ('AWD', 'AWD - All Wheel Drive'), ('4WD', '4WD - Four Wheel Drive'),
    ('4x4', '4x4'),
]

SOURCE_CHOICES = [
    ('', '-- Select --'),
    ('Auction', 'Auction'), ('Wholesale', 'Wholesale'), ('Private Seller', 'Private Seller'),
    ('Trade-In', 'Trade-In'), ('Dealer', 'Dealer'), ('Repo', 'Repossession'),
    ('Estate', 'Estate Sale'), ('Other', 'Other'),
]

TITLE_STATUS_CHOICES = [
    ('Clean', 'Clean'), ('Salvage', 'Salvage'), ('Rebuilt', 'Rebuilt'),
    ('Flood', 'Flood Damage'), ('Lemon', 'Lemon Law Buyback'),
    ('Lien', 'Lien Present'), ('Missing', 'Missing/Applied For'),
    ('Bonded', 'Bonded'), ('Other', 'Other'),
]

VEHICLE_STATUS_CHOICES = [
    ('In Recon', 'In Recon'),
    ('Available', 'Available for Sale'),
    ('Pending Sale', 'Pending Sale'),
    ('Sold', 'Sold'),
    ('Wholesale', 'Wholesaled'),
    ('On Hold', 'On Hold'),
    ('Junked', 'Junked/Crushed'),
]

CONDITION_CHOICES = [
    ('', '-- Select --'),
    ('Excellent', 'Excellent'), ('Good', 'Good'),
    ('Fair', 'Fair'), ('Poor', 'Poor'),
]


class VehicleForm(FlaskForm):
    # Core Identity
    stock_number = StringField('Stock #', validators=[DataRequired(), Length(1, 20)])
    vin = StringField('VIN', validators=[Optional(), Length(0, 17)])

    def validate_vin(self, field):
        if field.data:
            vin = field.data.strip().upper()
            if len(vin) != 17:
                raise ValidationError('VIN must be exactly 17 characters.')
            # I, O, Q are not valid VIN characters per ISO 3779
            if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
                raise ValidationError('VIN contains invalid characters (I, O, and Q are not used in VINs).')
    year = SelectField('Year', choices=YEAR_CHOICES, validators=[DataRequired()])
    make = StringField('Make', validators=[DataRequired(), Length(1, 50)])
    model = StringField('Model', validators=[DataRequired(), Length(1, 50)])
    trim = StringField('Trim / Edition', validators=[Optional(), Length(0, 50)])
    body_type = SelectField('Body Type', choices=BODY_TYPES, validators=[Optional()])

    # Details
    color_exterior = StringField('Exterior Color', validators=[Optional(), Length(0, 30)])
    color_interior = StringField('Interior Color', validators=[Optional(), Length(0, 30)])
    mileage = IntegerField('Mileage', validators=[Optional(), NumberRange(min=0)])
    transmission = SelectField('Transmission', choices=TRANSMISSION_CHOICES, validators=[Optional()])
    engine = StringField('Engine', validators=[Optional(), Length(0, 50)])
    fuel_type = SelectField('Fuel Type', choices=FUEL_CHOICES, validators=[Optional()])
    drivetrain = SelectField('Drivetrain', choices=DRIVETRAIN_CHOICES, validators=[Optional()])

    # Acquisition
    purchase_date = DateField('Purchase Date', validators=[DataRequired()])
    purchase_price = DecimalField('Purchase Price ($)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    purchase_source = SelectField('Source', choices=SOURCE_CHOICES, validators=[Optional()])
    purchase_source_detail = StringField('Source Detail (e.g. Manheim Atlanta)', validators=[Optional(), Length(0, 100)])

    # Title
    title_status = SelectField('Title Status', choices=TITLE_STATUS_CHOICES, validators=[Optional()])
    title_received = BooleanField('Title In Hand')
    title_number = StringField('Title Number', validators=[Optional(), Length(0, 50)])

    # Status & Pricing
    status = SelectField('Status', choices=VEHICLE_STATUS_CHOICES, validators=[DataRequired()])
    lot_location = StringField('Lot Location', validators=[Optional(), Length(0, 50)])
    asking_price = DecimalField('Asking Price ($)', validators=[Optional(), NumberRange(min=0)], places=2)
    condition = SelectField('Condition', choices=CONDITION_CHOICES, validators=[Optional()])

    # Notes
    features = TextAreaField('Features / Options (one per line)', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])


def build_expense_choices():
    choices = [('', '-- Select Category --')]
    for category, subs in EXPENSE_CATEGORIES:
        for sub in subs:
            choices.append((f'{category}|{sub}', f'{category} > {sub}'))
    return choices


class ExpenseForm(FlaskForm):
    vehicle_id = HiddenField('Vehicle ID')
    category_sub = SelectField('Category', choices=build_expense_choices(), validators=[DataRequired()])
    description = StringField('Description', validators=[Optional(), Length(0, 200)])
    amount = DecimalField('Amount ($)', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    vendor = StringField('Vendor / Shop', validators=[Optional(), Length(0, 100)])
    expense_date = DateField('Date', validators=[DataRequired()])
    invoice_number = StringField('Invoice #', validators=[Optional(), Length(0, 50)])


RECON_STAGE_CHOICES = [
    ('Inspection', 'Inspection & Assessment'),
    ('Mechanical', 'Mechanical Repairs'),
    ('Body & Paint', 'Body & Paint'),
    ('Interior', 'Interior & Detailing'),
    ('Final QC', 'Final QC / Ready Check'),
]

PRIORITY_CHOICES = [
    ('Low', 'Low'),
    ('Normal', 'Normal'),
    ('High', 'High'),
    ('Urgent', 'Urgent'),
]

TASK_STATUS_CHOICES = [
    ('Pending', 'Pending'),
    ('In Progress', 'In Progress'),
    ('Done', 'Done'),
    ('Skipped', 'Skipped'),
]


class ReconTaskForm(FlaskForm):
    vehicle_id = HiddenField('Vehicle ID')
    stage = SelectField('Stage', choices=RECON_STAGE_CHOICES, validators=[DataRequired()])
    title = StringField('Task Title', validators=[DataRequired(), Length(1, 100)])
    description = TextAreaField('Description / Work Needed', validators=[Optional()])
    status = SelectField('Status', choices=TASK_STATUS_CHOICES, validators=[DataRequired()])
    priority = SelectField('Priority', choices=PRIORITY_CHOICES, validators=[Optional()])
    vendor = StringField('Vendor / Shop', validators=[Optional(), Length(0, 100)])
    assigned_to_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    estimated_cost = DecimalField('Estimated Cost ($)', validators=[Optional(), NumberRange(min=0)], places=2)
    actual_cost = DecimalField('Actual Cost ($)', validators=[Optional(), NumberRange(min=0)], places=2)
    due_date = DateField('Due Date', validators=[Optional()])
    completed_date = DateField('Completed Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])


class SaleForm(FlaskForm):
    vehicle_id = HiddenField('Vehicle ID')
    sale_date = DateField('Sale Date', validators=[DataRequired()])
    sale_price = DecimalField('Sale Price ($)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    sale_type = SelectField('Sale Type', choices=[
        ('Retail', 'Retail'), ('Wholesale', 'Wholesale'),
        ('Auction', 'Auction'), ('Trade', 'Trade'),
    ])
    notes = TextAreaField('Notes', validators=[Optional()])


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6, message='Password must be at least 6 characters.')])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords do not match.')])


class PhotoUploadForm(FlaskForm):
    photos = MultipleFileField('Photos', validators=[DataRequired()])
    caption = StringField('Caption', validators=[Optional(), Length(0, 100)])
