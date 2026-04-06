from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')  # admin, manager, staff
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    vehicles_added = db.relationship('Vehicle', foreign_keys='Vehicle.created_by_id', backref='creator', lazy='dynamic')
    expenses_added = db.relationship('Expense', backref='creator', lazy='dynamic')
    recon_tasks = db.relationship('ReconTask', foreign_keys='ReconTask.assigned_to_id', backref='assignee', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_manager_or_above(self):
        return self.role in ('admin', 'manager')

    def __repr__(self):
        return f'<User {self.username}>'


class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    stock_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    vin = db.Column(db.String(17), unique=True, nullable=True, index=True)

    # Basic Info
    year = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    trim = db.Column(db.String(50))
    body_type = db.Column(db.String(30))  # Sedan, SUV, Truck, Van, Coupe, etc.

    # Details
    color_exterior = db.Column(db.String(30))
    color_interior = db.Column(db.String(30))
    mileage = db.Column(db.Integer)
    transmission = db.Column(db.String(20))  # Automatic, Manual, CVT
    engine = db.Column(db.String(50))
    fuel_type = db.Column(db.String(20))  # Gas, Diesel, Hybrid, Electric
    drivetrain = db.Column(db.String(10))  # FWD, RWD, AWD, 4WD

    # Acquisition
    purchase_date = db.Column(db.Date, nullable=False)
    purchase_price = db.Column(db.Numeric(10, 2), nullable=False)
    purchase_source = db.Column(db.String(30))  # Auction, Private, Dealer, Trade-In, Wholesale
    purchase_source_detail = db.Column(db.String(100))  # e.g. "Manheim Atlanta"

    # Title & Documentation
    title_status = db.Column(db.String(30), default='Clean')  # Clean, Salvage, Rebuilt, Lien, Missing
    title_received = db.Column(db.Boolean, default=False)
    title_number = db.Column(db.String(50))

    # Status & Location
    status = db.Column(db.String(20), nullable=False, default='In Recon')
    # Statuses: In Recon, Available, Pending Sale, Sold, Wholesale, On Hold, Junked
    lot_location = db.Column(db.String(50))  # Row A, Bay 3, etc.

    # Pricing
    asking_price = db.Column(db.Numeric(10, 2))

    # Condition & Notes
    condition = db.Column(db.String(20))  # Excellent, Good, Fair, Poor
    notes = db.Column(db.Text)
    features = db.Column(db.Text)  # Comma-separated features: "Leather, Sunroof, Nav"

    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    expenses = db.relationship('Expense', backref='vehicle', lazy='dynamic', cascade='all, delete-orphan')
    recon_tasks = db.relationship('ReconTask', backref='vehicle', lazy='dynamic', cascade='all, delete-orphan')
    sale = db.relationship('Sale', backref='vehicle', uselist=False, cascade='all, delete-orphan')
    photos = db.relationship('VehiclePhoto', backref='vehicle', lazy='dynamic',
                             order_by='VehiclePhoto.sort_order', cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='vehicle', lazy='dynamic',
                                    order_by='ActivityLog.created_at.desc()', cascade='all, delete-orphan')

    @property
    def days_on_lot(self):
        if self.status == 'Sold' and self.sale:
            end_date = self.sale.sale_date
        else:
            end_date = datetime.now(timezone.utc).date()
        return (end_date - self.purchase_date).days

    @property
    def total_cost(self):
        # purchase_price column is the source of truth; exclude the mirrored purchase expense
        recon_total = sum(
            float(e.amount) for e in self.expenses
            if not (e.category == 'Purchase' and e.subcategory == 'Purchase Price')
        )
        return float(self.purchase_price) + recon_total

    @property
    def recon_cost(self):
        return sum(
            float(e.amount) for e in self.expenses
            if not (e.category == 'Purchase' and e.subcategory == 'Purchase Price')
        )

    @property
    def gross_profit(self):
        if self.sale:
            return float(self.sale.sale_price) - self.total_cost
        return None

    @property
    def days_in_recon(self):
        """Days from purchase until the last recon task was marked Done, or today if still in recon."""
        done_tasks = [t for t in self.recon_tasks if t.status == 'Done' and t.completed_date]
        if done_tasks:
            last_done = max(t.completed_date for t in done_tasks)
            return (last_done - self.purchase_date).days
        if self.status == 'In Recon':
            return self.days_on_lot
        return None

    @property
    def primary_photo(self):
        primary = self.photos.filter_by(is_primary=True).first()
        return primary or self.photos.first()

    @property
    def display_name(self):
        return f"{self.year} {self.make} {self.model}"

    def __repr__(self):
        return f'<Vehicle {self.stock_number} {self.display_name}>'


EXPENSE_CATEGORIES = [
    ('Mechanical', [
        'Oil & Fluids', 'Brakes', 'Tires', 'Battery', 'Engine', 'Transmission',
        'Suspension', 'Exhaust', 'AC/Heat', 'Electrical', 'Belts & Hoses',
        'Steering', 'Cooling System', 'Fuel System', 'Other Mechanical'
    ]),
    ('Body & Paint', [
        'Paint', 'Dent Repair', 'Body Panels', 'Bumper Repair', 'Glass/Windshield',
        'Rust Repair', 'Frame Work', 'Other Body Work'
    ]),
    ('Interior', [
        'Detailing', 'Upholstery', 'Carpet', 'Headliner', 'Dashboard',
        'Seats', 'Odor Treatment', 'Window Tinting', 'Other Interior'
    ]),
    ('Tires & Wheels', [
        'Tires', 'Wheels/Rims', 'Alignment', 'Balancing', 'TPMS Sensors'
    ]),
    ('Transportation', [
        'Towing', 'Transport Fee', 'Fuel', 'Driver Fee'
    ]),
    ('Documentation', [
        'Title Fee', 'DMV/Registration', 'Inspection Fee', 'History Report', 'Notary'
    ]),
    ('Advertising', [
        'AutoTrader', 'Cars.com', 'Facebook Marketplace', 'Craigslist',
        'Photography', 'Online Listing', 'Print Ad', 'Other Advertising'
    ]),
    ('Miscellaneous', [
        'Keys/Locksmith', 'Floor Mats', 'License Plates', 'Touch-up Kit', 'Other'
    ]),
]

EXPENSE_CATEGORY_FLAT = ['Purchase Price'] + [
    sub for _, subs in EXPENSE_CATEGORIES for sub in subs
]


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)  # Top-level category
    subcategory = db.Column(db.String(50))               # Specific subcategory
    description = db.Column(db.String(200))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    vendor = db.Column(db.String(100))
    expense_date = db.Column(db.Date, nullable=False)
    invoice_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<Expense {self.category} ${self.amount}>'


class ReconTask(db.Model):
    __tablename__ = 'recon_tasks'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    stage = db.Column(db.String(30), nullable=False)
    # Stages: Inspection, Mechanical, Body & Paint, Interior/Detail, Final QC

    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Done, Skipped
    priority = db.Column(db.String(10), default='Normal')  # Low, Normal, High, Urgent
    vendor = db.Column(db.String(100))
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    estimated_cost = db.Column(db.Numeric(10, 2))
    actual_cost = db.Column(db.Numeric(10, 2))
    due_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    creator = db.relationship('User', foreign_keys=[created_by_id], overlaps='recon_tasks')

    def __repr__(self):
        return f'<ReconTask {self.stage}: {self.title}>'


class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, unique=True)
    sale_date = db.Column(db.Date, nullable=False)
    sale_price = db.Column(db.Numeric(10, 2), nullable=False)
    sale_type = db.Column(db.String(30))  # Retail, Wholesale, Auction, Trade
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<Sale vehicle_id={self.vehicle_id} price=${self.sale_price}>'


class VehiclePhoto(db.Model):
    __tablename__ = 'vehicle_photos'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(100))
    is_primary = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    @property
    def url(self):
        return f'/static/uploads/vehicles/{self.vehicle_id}/{self.filename}'

    def __repr__(self):
        return f'<VehiclePhoto {self.filename}>'


class ActivityLog(db.Model):
    __tablename__ = 'activity_log'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f'<ActivityLog vehicle_id={self.vehicle_id} action={self.action}>'
