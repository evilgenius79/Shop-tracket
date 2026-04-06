from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from models import db, User
from forms import UserForm

users_bp = Blueprint('users', __name__, url_prefix='/users')


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


@users_bp.route('/')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.username).all()
    return render_template('users/list.html', users=users)


@users_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash('Password is required for new users.', 'danger')
            return render_template('users/form.html', form=form, title='Add User')

        if User.query.filter_by(username=form.username.data).first():
            flash(f'Username "{form.username.data}" is already taken.', 'danger')
            return render_template('users/form.html', form=form, title='Add User')

        if User.query.filter_by(email=form.email.data).first():
            flash(f'Email "{form.email.data}" is already in use.', 'danger')
            return render_template('users/form.html', form=form, title='Add User')

        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            is_active=form.is_active.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} created.', 'success')
        return redirect(url_for('users.list_users'))

    return render_template('users/form.html', form=form, title='Add User')


@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)

    if form.validate_on_submit():
        # Check username conflict
        conflict = User.query.filter(
            User.username == form.username.data,
            User.id != user.id
        ).first()
        if conflict:
            flash('That username is taken.', 'danger')
            return render_template('users/form.html', form=form, title='Edit User', user=user)

        # Guard: prevent demoting the last active admin BEFORE making any changes
        if user.role == 'admin' and form.role.data != 'admin':
            admin_count = User.query.filter_by(role='admin', is_active=True).count()
            if admin_count <= 1:
                flash('Cannot demote the only active admin account.', 'danger')
                return render_template('users/form.html', form=form, title='Edit User', user=user)

        # Guard: prevent deactivating the last active admin
        if user.is_active and not form.is_active.data and user.role == 'admin':
            admin_count = User.query.filter_by(role='admin', is_active=True).count()
            if admin_count <= 1:
                flash('Cannot deactivate the only active admin account.', 'danger')
                return render_template('users/form.html', form=form, title='Edit User', user=user)

        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.is_active = form.is_active.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash(f'User {user.username} updated.', 'success')
        return redirect(url_for('users.list_users'))

    return render_template('users/form.html', form=form, title='Edit User', user=user)


@users_bp.route('/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate yourself.', 'danger')
        return redirect(url_for('users.list_users'))
    user.is_active = not user.is_active
    db.session.commit()
    state = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {state}.', 'success')
    return redirect(url_for('users.list_users'))


@users_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Allow any user to change their own password."""
    from forms import PasswordChangeForm
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('users/profile.html', form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password updated successfully.', 'success')
        return redirect(url_for('users.profile'))
    return render_template('users/profile.html', form=form)
