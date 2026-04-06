from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from models import db, User
from forms import LoginForm


def _is_safe_redirect(target):
    """Return True only if the redirect target is a safe relative path on this host."""
    if not target:
        return False
    parsed = urlparse(target)
    # Reject anything with a scheme (http://) or netloc (//evil.com)
    if parsed.scheme or parsed.netloc:
        return False
    # Reject paths with multiple leading slashes (////evil.com browser quirks)
    if target.startswith('//'):
        return False
    return True

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('vehicles.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Contact an admin.', 'danger')
                return redirect(url_for('auth.login'))
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            if not _is_safe_redirect(next_page):
                next_page = url_for('vehicles.dashboard')
            return redirect(next_page)
        flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
