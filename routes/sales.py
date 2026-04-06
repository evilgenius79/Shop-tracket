from flask import Blueprint, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Vehicle, Sale
from forms import SaleForm
from routes.activity import log_activity

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/vehicles/<int:vehicle_id>/sell', methods=['POST'])
@login_required
def mark_sold(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = SaleForm()

    if form.validate_on_submit():
        if vehicle.sale:
            vehicle.sale.sale_date = form.sale_date.data
            vehicle.sale.sale_price = form.sale_price.data
            vehicle.sale.sale_type = form.sale_type.data
            vehicle.sale.notes = form.notes.data
            log_activity(vehicle_id, 'Sale updated',
                         f'Sale price: ${float(form.sale_price.data):,.2f}')
        else:
            sale = Sale(
                vehicle_id=vehicle_id,
                sale_date=form.sale_date.data,
                sale_price=form.sale_price.data,
                sale_type=form.sale_type.data,
                notes=form.notes.data,
                created_by_id=current_user.id,
            )
            db.session.add(sale)
            log_activity(vehicle_id, 'Vehicle sold',
                         f'Sale price: ${float(form.sale_price.data):,.2f}, Type: {form.sale_type.data}')

        vehicle.status = 'Sold'
        db.session.commit()

        gp = vehicle.gross_profit
        if gp is not None:
            gp_str = f'${gp:,.2f}' if gp >= 0 else f'-${abs(gp):,.2f}'
            flash(f'{vehicle.display_name} marked as sold. Gross Profit: {gp_str}', 'success')
        else:
            flash(f'{vehicle.display_name} marked as sold.', 'success')
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f'{field}: {err}', 'danger')

    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))


@sales_bp.route('/vehicles/<int:vehicle_id>/unsell', methods=['POST'])
@login_required
def unmark_sold(vehicle_id):
    if not current_user.is_manager_or_above():
        flash('Only managers can undo a sale.', 'danger')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))

    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.sale:
        db.session.delete(vehicle.sale)
    vehicle.status = 'Available'
    log_activity(vehicle_id, 'Sale reversed', 'Vehicle returned to Available')
    db.session.commit()
    flash(f'{vehicle.display_name} sale has been reversed.', 'warning')
    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))
