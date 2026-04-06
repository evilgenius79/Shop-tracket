from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, Vehicle, Expense, EXPENSE_CATEGORIES
from forms import ExpenseForm
from routes.activity import log_activity

# Flat set of all valid category|subcategory pairs for input validation
_VALID_CAT_SUBS = {
    f'{cat}|{sub}' for cat, subs in EXPENSE_CATEGORIES for sub in subs
}

expenses_bp = Blueprint('expenses', __name__)


@expenses_bp.route('/vehicles/<int:vehicle_id>/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = ExpenseForm()
    form.vehicle_id.data = vehicle_id

    if request.method == 'GET':
        form.expense_date.data = date.today()

    if form.validate_on_submit():
        cat_sub = form.category_sub.data
        if cat_sub not in _VALID_CAT_SUBS:
            flash('Invalid expense category selected.', 'danger')
            return render_template('expenses/form.html', form=form, vehicle=vehicle, title='Add Expense')
        category, subcategory = cat_sub.split('|', 1)

        expense = Expense(
            vehicle_id=vehicle_id,
            category=category,
            subcategory=subcategory,
            description=form.description.data,
            amount=form.amount.data,
            vendor=form.vendor.data,
            expense_date=form.expense_date.data,
            invoice_number=form.invoice_number.data,
            created_by_id=current_user.id,
        )
        db.session.add(expense)
        log_activity(vehicle_id, 'Expense added',
                     f'{category} > {subcategory}: ${float(form.amount.data):,.2f}')
        db.session.commit()
        flash(f'Expense of ${float(expense.amount):,.2f} added.', 'success')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))

    return render_template('expenses/form.html', form=form, vehicle=vehicle, title='Add Expense')


@expenses_bp.route('/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    # Only the creator or a manager/admin can edit
    if expense.created_by_id != current_user.id and not current_user.is_manager_or_above():
        abort(403)
    vehicle = expense.vehicle
    form = ExpenseForm(obj=expense)
    form.vehicle_id.data = vehicle.id

    if request.method == 'GET':
        form.category_sub.data = f'{expense.category}|{expense.subcategory}'

    if form.validate_on_submit():
        cat_sub = form.category_sub.data
        if cat_sub not in _VALID_CAT_SUBS:
            flash('Invalid expense category selected.', 'danger')
            return render_template('expenses/form.html', form=form, vehicle=vehicle, title='Edit Expense')
        category, subcategory = cat_sub.split('|', 1)

        expense.category = category
        expense.subcategory = subcategory
        expense.description = form.description.data
        expense.amount = form.amount.data
        expense.vendor = form.vendor.data
        expense.expense_date = form.expense_date.data
        expense.invoice_number = form.invoice_number.data
        db.session.commit()
        flash('Expense updated.', 'success')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle.id))

    return render_template('expenses/form.html', form=form, vehicle=vehicle, title='Edit Expense')


@expenses_bp.route('/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    vehicle_id = expense.vehicle_id
    # Only the creator or a manager/admin can delete
    if expense.created_by_id != current_user.id and not current_user.is_manager_or_above():
        abort(403)
    # Don't allow deleting the auto-generated purchase price entry
    if expense.category == 'Purchase' and expense.subcategory == 'Purchase Price':
        flash('The purchase price expense is managed through the vehicle edit form.', 'warning')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))
    log_activity(vehicle_id, 'Expense deleted',
                 f'{expense.category} > {expense.subcategory}: ${float(expense.amount):,.2f}')
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'success')
    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))
