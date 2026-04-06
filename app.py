import os
import json
from datetime import datetime, timezone, date
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for, flash,
    request, jsonify, abort
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func, extract

from config import Config
from models import db, User, Vehicle, Expense, ReconTask, Sale, EXPENSE_CATEGORIES
from forms import (
    LoginForm, UserForm, VehicleForm, ExpenseForm,
    ReconTaskForm, SaleForm
)

csrf = CSRFProtect()


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.vehicles import vehicles_bp
    from routes.expenses import expenses_bp
    from routes.recon import recon_bp
    from routes.reports import reports_bp
    from routes.users import users_bp
    from routes.sales import sales_bp
    from routes.api import api_bp
    from routes.photos import photos_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(recon_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(photos_bp)

    # Root redirect
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('vehicles.dashboard'))
        return redirect(url_for('auth.login'))

    # Custom error pages
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    # Template context helpers
    @app.context_processor
    def inject_globals():
        return dict(
            now=datetime.now(timezone.utc),
            today=date.today(),
        )

    @app.template_filter('currency')
    def currency_filter(value):
        if value is None:
            return '$0.00'
        return f'${float(value):,.2f}'

    @app.template_filter('number')
    def number_filter(value):
        if value is None:
            return '0'
        return f'{int(value):,}'

    @app.template_filter('age_class')
    def age_class_filter(days):
        if days is None:
            return ''
        if days >= 90:
            return 'danger'
        if days >= 60:
            return 'warning'
        if days >= 30:
            return 'info'
        return 'success'

    @app.template_filter('status_badge')
    def status_badge_filter(status):
        mapping = {
            'In Recon': 'status-in-recon',
            'Available': 'status-available',
            'Pending Sale': 'status-pending-sale',
            'Sold': 'status-sold',
            'Wholesale': 'status-wholesale',
            'On Hold': 'status-on-hold',
            'Junked': 'status-junked',
        }
        return mapping.get(status, 'bg-secondary')

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin if no users exist
        if not User.query.first():
            admin = User(
                username='admin',
                email='admin@carlot.local',
                role='admin',
                is_active=True,
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: username=admin password=admin123")
            print("IMPORTANT: Change the password after first login!")
    app.run(host='0.0.0.0', port=5000, debug=False)
