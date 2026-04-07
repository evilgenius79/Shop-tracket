import csv
import io
from datetime import date, datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from models import db, Vehicle, Expense, ReconTask, Sale, PriceHistory, EXPENSE_CATEGORIES
from forms import VehicleForm, SaleForm, PhotoUploadForm, VehicleImportForm
from routes.activity import log_activity

vehicles_bp = Blueprint('vehicles', __name__)


def _next_stock_number():
    last = db.session.query(func.max(Vehicle.stock_number)).scalar()
    if last:
        try:
            num = int(last.lstrip('S')) + 1
        except (ValueError, AttributeError):
            num = 1
    else:
        num = 1
    return f'S{num:04d}'


@vehicles_bp.route('/dashboard')
@login_required
def dashboard():
    INACTIVE = ('Sold', 'Wholesale', 'Junked')

    # Status counts via GROUP BY — no full table scan in Python
    status_rows = db.session.query(Vehicle.status, func.count(Vehicle.id)).group_by(Vehicle.status).all()
    status_counts = {s: c for s, c in status_rows}

    # Active vehicles only (needed for cost/days calculations which require Python properties)
    active = Vehicle.query.filter(Vehicle.status.notin_(INACTIVE)).all()
    sold_count = db.session.query(func.count(Vehicle.id)).filter(Vehicle.status == 'Sold').scalar() or 0

    total_inventory_cost = sum(v.total_cost for v in active)
    total_asking = sum(float(v.asking_price) for v in active if v.asking_price)
    avg_days = sum(v.days_on_lot for v in active) / len(active) if active else 0

    # Aged inventory buckets
    aged_30 = sum(1 for v in active if v.days_on_lot >= 30)
    aged_60 = sum(1 for v in active if v.days_on_lot >= 60)
    aged_90 = sum(1 for v in active if v.days_on_lot >= 90)

    # Gross profit from sold vehicles
    sold_vehicles = db.session.query(Vehicle).join(Sale).filter(Vehicle.status == 'Sold').all()
    sold_with_profit = [v for v in sold_vehicles if v.gross_profit is not None]
    total_gross_profit = sum(v.gross_profit for v in sold_with_profit)
    avg_gross_profit = total_gross_profit / len(sold_with_profit) if sold_with_profit else 0

    # Recent vehicles (last 5 added)
    recent_vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).limit(5).all()

    # Vehicles needing attention (in recon > 7 days)
    attention = [v for v in active if v.status == 'In Recon' and v.days_on_lot > 7]

    # Monthly sales for chart (last 6 months)
    monthly_sales = _monthly_sales_data(6)

    return render_template('vehicles/dashboard.html',
        status_counts=status_counts,
        active_count=len(active),
        sold_count=sold_count,
        total_inventory_cost=total_inventory_cost,
        total_asking=total_asking,
        avg_days=avg_days,
        aged_30=aged_30,
        aged_60=aged_60,
        aged_90=aged_90,
        total_gross_profit=total_gross_profit,
        avg_gross_profit=avg_gross_profit,
        recent_vehicles=recent_vehicles,
        attention_vehicles=attention,
        monthly_sales=monthly_sales,
    )


def _monthly_sales_data(months):
    results = []
    today = date.today()
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        count = db.session.query(func.count(Sale.id)).filter(
            func.strftime('%Y', Sale.sale_date) == str(y),
            func.strftime('%m', Sale.sale_date) == f'{m:02d}',
        ).scalar() or 0
        revenue = db.session.query(func.sum(Sale.sale_price)).filter(
            func.strftime('%Y', Sale.sale_date) == str(y),
            func.strftime('%m', Sale.sale_date) == f'{m:02d}',
        ).scalar() or 0
        results.append({
            'label': date(y, m, 1).strftime('%b %Y'),
            'count': count,
            'revenue': float(revenue),
        })
    return results


@vehicles_bp.route('/vehicles')
@login_required
def list_vehicles():
    status_filter = request.args.get('status', '')
    search = request.args.get('q', '').strip()
    source_filter = request.args.get('source', '')
    sort = request.args.get('sort', 'newest')

    query = Vehicle.query

    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    if source_filter:
        query = query.filter(Vehicle.purchase_source == source_filter)
    if search:
        like = f'%{search}%'
        query = query.filter(or_(
            Vehicle.make.ilike(like),
            Vehicle.model.ilike(like),
            Vehicle.vin.ilike(like),
            Vehicle.stock_number.ilike(like),
            Vehicle.year.cast(db.String).ilike(like),
        ))

    if sort == 'oldest':
        query = query.order_by(Vehicle.purchase_date.asc())
    elif sort == 'price_high':
        query = query.order_by(Vehicle.purchase_price.desc())
    elif sort == 'price_low':
        query = query.order_by(Vehicle.purchase_price.asc())
    elif sort == 'make':
        query = query.order_by(Vehicle.make, Vehicle.model)
    else:
        query = query.order_by(Vehicle.created_at.desc())

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    vehicles = pagination.items

    # Status counts for filter tabs
    all_statuses = db.session.query(Vehicle.status, func.count(Vehicle.id)).group_by(Vehicle.status).all()
    status_counts = {s: c for s, c in all_statuses}
    total_count = sum(status_counts.values())

    return render_template('vehicles/list.html',
        vehicles=vehicles,
        pagination=pagination,
        status_filter=status_filter,
        search=search,
        source_filter=source_filter,
        sort=sort,
        status_counts=status_counts,
        total_count=total_count,
    )


@vehicles_bp.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    form = VehicleForm()
    if request.method == 'GET':
        form.stock_number.data = _next_stock_number()
        form.purchase_date.data = date.today()
        form.status.data = 'In Recon'

    if form.validate_on_submit():
        # Check for duplicate stock number
        existing = Vehicle.query.filter_by(stock_number=form.stock_number.data.upper()).first()
        if existing:
            flash(f'Stock number {form.stock_number.data} is already in use.', 'danger')
            return render_template('vehicles/form.html', form=form, title='Add Vehicle')

        # Check VIN if provided
        if form.vin.data:
            vin_exists = Vehicle.query.filter_by(vin=form.vin.data.upper()).first()
            if vin_exists:
                flash(f'VIN {form.vin.data} is already in the system (Stock #{vin_exists.stock_number}).', 'danger')
                return render_template('vehicles/form.html', form=form, title='Add Vehicle')

        vehicle = Vehicle(
            stock_number=form.stock_number.data.upper(),
            vin=form.vin.data.upper() if form.vin.data else None,
            year=int(form.year.data),
            make=form.make.data.title(),
            model=form.model.data.title(),
            trim=form.trim.data,
            body_type=form.body_type.data,
            color_exterior=form.color_exterior.data,
            color_interior=form.color_interior.data,
            mileage=form.mileage.data,
            transmission=form.transmission.data,
            engine=form.engine.data,
            fuel_type=form.fuel_type.data,
            drivetrain=form.drivetrain.data,
            purchase_date=form.purchase_date.data,
            purchase_price=form.purchase_price.data,
            purchase_source=form.purchase_source.data,
            purchase_source_detail=form.purchase_source_detail.data,
            title_status=form.title_status.data,
            title_received=form.title_received.data,
            title_number=form.title_number.data,
            status=form.status.data,
            lot_location=form.lot_location.data,
            asking_price=form.asking_price.data,
            condition=form.condition.data,
            features=form.features.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
        )
        db.session.add(vehicle)
        db.session.flush()  # Assign vehicle.id without committing yet

        # Auto-create purchase expense
        if vehicle.purchase_price:
            purchase_exp = Expense(
                vehicle_id=vehicle.id,
                category='Purchase',
                subcategory='Purchase Price',
                description=f'Vehicle purchase from {vehicle.purchase_source or "unknown source"}',
                amount=vehicle.purchase_price,
                expense_date=vehicle.purchase_date,
                vendor=vehicle.purchase_source_detail,
                created_by_id=current_user.id,
            )
            db.session.add(purchase_exp)

        log_activity(vehicle.id, 'Vehicle added',
                     f'Purchased for {vehicle.purchase_price} from {vehicle.purchase_source or "unknown"}')
        db.session.commit()  # Single atomic commit for vehicle + expense + log

        flash(f'Vehicle {vehicle.display_name} (#{vehicle.stock_number}) added successfully!', 'success')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle.id))

    return render_template('vehicles/form.html', form=form, title='Add Vehicle')


@vehicles_bp.route('/vehicles/<int:vehicle_id>')
@login_required
def vehicle_detail(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    expenses = vehicle.expenses.order_by(Expense.expense_date.desc()).all()
    recon_tasks = vehicle.recon_tasks.order_by(ReconTask.created_at.asc()).all()

    # Group expenses by category
    expense_by_cat = {}
    for exp in expenses:
        cat = exp.category
        expense_by_cat.setdefault(cat, {'total': 0, 'items': []})
        expense_by_cat[cat]['total'] += float(exp.amount)
        expense_by_cat[cat]['items'].append(exp)

    # Recon tasks by stage
    STAGES = ['Inspection', 'Mechanical', 'Body & Paint', 'Interior', 'Final QC']
    recon_by_stage = {stage: [] for stage in STAGES}
    for task in recon_tasks:
        if task.stage in recon_by_stage:
            recon_by_stage[task.stage].append(task)
        else:
            recon_by_stage.setdefault(task.stage, []).append(task)

    sale_form = SaleForm()
    sale_form.vehicle_id.data = vehicle.id
    if not vehicle.sale:
        sale_form.sale_date.data = date.today()

    photo_form = PhotoUploadForm()
    photos = vehicle.photos.order_by('sort_order').all()
    activity_logs = vehicle.activity_logs.limit(50).all()
    price_history = vehicle.price_changes.all()

    return render_template('vehicles/detail.html',
        vehicle=vehicle,
        expenses=expenses,
        expense_by_cat=expense_by_cat,
        recon_by_stage=recon_by_stage,
        recon_stages=STAGES,
        sale_form=sale_form,
        photo_form=photo_form,
        photos=photos,
        activity_logs=activity_logs,
        price_history=price_history,
        expense_categories=EXPENSE_CATEGORIES,
    )


@vehicles_bp.route('/vehicles/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = VehicleForm(obj=vehicle)

    if request.method == 'GET':
        form.year.data = str(vehicle.year)

    if form.validate_on_submit():
        # Check stock number conflict (excluding self)
        existing = Vehicle.query.filter(
            Vehicle.stock_number == form.stock_number.data.upper(),
            Vehicle.id != vehicle.id
        ).first()
        if existing:
            flash(f'Stock number {form.stock_number.data} is already in use.', 'danger')
            return render_template('vehicles/form.html', form=form, title='Edit Vehicle', vehicle=vehicle)

        # Check VIN conflict
        if form.vin.data:
            vin_exists = Vehicle.query.filter(
                Vehicle.vin == form.vin.data.upper(),
                Vehicle.id != vehicle.id
            ).first()
            if vin_exists:
                flash(f'VIN {form.vin.data} belongs to Stock #{vin_exists.stock_number}.', 'danger')
                return render_template('vehicles/form.html', form=form, title='Edit Vehicle', vehicle=vehicle)

        old_purchase = float(vehicle.purchase_price)
        new_purchase = float(form.purchase_price.data)
        old_asking = float(vehicle.asking_price) if vehicle.asking_price else None
        new_asking = float(form.asking_price.data) if form.asking_price.data else None

        vehicle.stock_number = form.stock_number.data.upper()
        vehicle.vin = form.vin.data.upper() if form.vin.data else None
        vehicle.year = int(form.year.data)
        vehicle.make = form.make.data.title()
        vehicle.model = form.model.data.title()
        vehicle.trim = form.trim.data
        vehicle.body_type = form.body_type.data
        vehicle.color_exterior = form.color_exterior.data
        vehicle.color_interior = form.color_interior.data
        vehicle.mileage = form.mileage.data
        vehicle.transmission = form.transmission.data
        vehicle.engine = form.engine.data
        vehicle.fuel_type = form.fuel_type.data
        vehicle.drivetrain = form.drivetrain.data
        vehicle.purchase_date = form.purchase_date.data
        vehicle.purchase_price = form.purchase_price.data
        vehicle.purchase_source = form.purchase_source.data
        vehicle.purchase_source_detail = form.purchase_source_detail.data
        vehicle.title_status = form.title_status.data
        vehicle.title_received = form.title_received.data
        vehicle.title_number = form.title_number.data
        vehicle.status = form.status.data
        vehicle.lot_location = form.lot_location.data
        vehicle.asking_price = form.asking_price.data
        vehicle.condition = form.condition.data
        vehicle.features = form.features.data
        vehicle.notes = form.notes.data
        vehicle.updated_at = datetime.now(timezone.utc)

        # Update purchase expense if purchase price changed
        if old_purchase != new_purchase:
            purchase_exp = vehicle.expenses.filter_by(category='Purchase', subcategory='Purchase Price').first()
            if purchase_exp:
                purchase_exp.amount = new_purchase
                purchase_exp.expense_date = vehicle.purchase_date

        # Log asking price change to price history
        if old_asking != new_asking:
            ph = PriceHistory(
                vehicle_id=vehicle.id,
                old_price=old_asking,
                new_price=new_asking,
                changed_by_id=current_user.id,
            )
            db.session.add(ph)
            log_activity(vehicle.id, 'Asking price changed',
                         f'${old_asking:,.2f} → ${new_asking:,.2f}' if old_asking and new_asking
                         else f'Set to ${new_asking:,.2f}' if new_asking else 'Cleared')
        else:
            log_activity(vehicle.id, 'Vehicle updated',
                         f'Status: {vehicle.status}, Asking: {vehicle.asking_price}')
        db.session.commit()
        flash(f'Vehicle {vehicle.display_name} updated.', 'success')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle.id))

    return render_template('vehicles/form.html', form=form, title='Edit Vehicle', vehicle=vehicle)


@vehicles_bp.route('/vehicles/<int:vehicle_id>/clone', methods=['POST'])
@login_required
def clone_vehicle(vehicle_id):
    original = Vehicle.query.get_or_404(vehicle_id)
    new_stock = _next_stock_number()

    clone = Vehicle(
        stock_number=new_stock,
        vin=None,  # VIN must be unique; dealer will enter separately
        year=original.year,
        make=original.make,
        model=original.model,
        trim=original.trim,
        body_type=original.body_type,
        color_exterior=original.color_exterior,
        color_interior=original.color_interior,
        transmission=original.transmission,
        engine=original.engine,
        fuel_type=original.fuel_type,
        drivetrain=original.drivetrain,
        purchase_date=date.today(),
        purchase_price=original.purchase_price,
        purchase_source=original.purchase_source,
        purchase_source_detail=original.purchase_source_detail,
        title_status=original.title_status,
        title_received=False,
        status='In Recon',
        condition=original.condition,
        features=original.features,
        notes=f'Cloned from #{original.stock_number}',
        created_by_id=current_user.id,
    )
    db.session.add(clone)
    db.session.flush()

    # Auto-create purchase expense for the clone
    purchase_exp = Expense(
        vehicle_id=clone.id,
        category='Purchase',
        subcategory='Purchase Price',
        description=f'Vehicle purchase (cloned from #{original.stock_number})',
        amount=clone.purchase_price,
        expense_date=clone.purchase_date,
        created_by_id=current_user.id,
    )
    db.session.add(purchase_exp)
    log_activity(clone.id, 'Vehicle cloned', f'Cloned from #{original.stock_number}')
    db.session.commit()

    flash(f'Vehicle cloned as #{new_stock}. Please update VIN, mileage, and purchase price.', 'success')
    return redirect(url_for('vehicles.edit_vehicle', vehicle_id=clone.id))


@vehicles_bp.route('/vehicles/bulk-status', methods=['POST'])
@login_required
def bulk_status():
    vehicle_ids = request.form.getlist('vehicle_ids')
    new_status = request.form.get('new_status', '').strip()
    valid_statuses = {'In Recon', 'Available', 'Pending Sale', 'On Hold', 'Wholesale', 'Junked'}

    if not vehicle_ids:
        flash('No vehicles selected.', 'warning')
        return redirect(url_for('vehicles.list_vehicles'))
    if new_status not in valid_statuses:
        flash('Invalid status selected.', 'danger')
        return redirect(url_for('vehicles.list_vehicles'))

    updated = 0
    for vid in vehicle_ids:
        try:
            v = Vehicle.query.get(int(vid))
        except (ValueError, TypeError):
            continue
        if v and v.status != 'Sold':  # Never bulk-change a sold vehicle
            old_status = v.status
            v.status = new_status
            log_activity(v.id, 'Status changed (bulk)', f'{old_status} → {new_status}')
            updated += 1

    db.session.commit()
    flash(f'{updated} vehicle(s) updated to "{new_status}".', 'success')
    return redirect(url_for('vehicles.list_vehicles'))


@vehicles_bp.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    if not current_user.is_manager_or_above():
        abort(403)
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    name = vehicle.display_name
    stock = vehicle.stock_number
    db.session.delete(vehicle)
    db.session.commit()
    flash(f'{name} (#{stock}) has been deleted.', 'success')
    return redirect(url_for('vehicles.list_vehicles'))


@vehicles_bp.route('/vehicles/<int:vehicle_id>/sticker')
@login_required
def vehicle_sticker(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    vehicle_url = request.host_url.rstrip('/') + url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id)
    return render_template('vehicles/sticker.html', vehicle=vehicle, vehicle_url=vehicle_url)


@vehicles_bp.route('/vehicles/import', methods=['GET', 'POST'])
@login_required
def import_vehicles():
    form = VehicleImportForm()
    results = None

    if form.validate_on_submit():
        raw = form.csv_file.data.read().decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(raw))
        required_cols = {'year', 'make', 'model', 'purchase_date', 'purchase_price'}

        if not required_cols.issubset({c.strip().lower() for c in (reader.fieldnames or [])}):
            flash(f'CSV must have columns: {", ".join(sorted(required_cols))}', 'danger')
            return render_template('vehicles/import.html', form=form, results=None)

        results = {'added': [], 'skipped': [], 'errors': []}

        for i, row in enumerate(reader, start=2):
            row = {k.strip().lower(): (v or '').strip() for k, v in row.items()}
            stock = row.get('stock_number', '').upper() or _next_stock_number()

            # Skip duplicate stock numbers
            if Vehicle.query.filter_by(stock_number=stock).first():
                results['skipped'].append(f'Row {i}: stock #{stock} already exists')
                continue

            try:
                yr = int(row['year'])
                price = float(row['purchase_price'].replace(',', '').replace('$', ''))
                pdate = date.fromisoformat(row['purchase_date'])
            except (ValueError, KeyError) as e:
                results['errors'].append(f'Row {i}: {e}')
                continue

            v = Vehicle(
                stock_number=stock,
                vin=row.get('vin', '').upper() or None,
                year=yr,
                make=row.get('make', '').title(),
                model=row.get('model', '').title(),
                trim=row.get('trim') or None,
                body_type=row.get('body_type') or None,
                color_exterior=row.get('color_exterior') or None,
                mileage=int(row['mileage'].replace(',', '')) if row.get('mileage') else None,
                transmission=row.get('transmission') or None,
                engine=row.get('engine') or None,
                fuel_type=row.get('fuel_type') or None,
                drivetrain=row.get('drivetrain') or None,
                purchase_date=pdate,
                purchase_price=price,
                purchase_source=row.get('purchase_source') or None,
                status=row.get('status') or 'In Recon',
                lot_location=row.get('lot_location') or None,
                asking_price=float(row['asking_price'].replace(',', '').replace('$', ''))
                             if row.get('asking_price') else None,
                notes=row.get('notes') or None,
                created_by_id=current_user.id,
            )
            db.session.add(v)
            db.session.flush()

            exp = Expense(
                vehicle_id=v.id,
                category='Purchase', subcategory='Purchase Price',
                description=f'Vehicle purchase from {v.purchase_source or "unknown"}',
                amount=price, expense_date=pdate, created_by_id=current_user.id,
            )
            db.session.add(exp)
            log_activity(v.id, 'Vehicle imported', f'Imported from CSV by {current_user.username}')
            results['added'].append(f'#{stock} — {v.display_name}')

        db.session.commit()
        flash(f"Import complete: {len(results['added'])} added, "
              f"{len(results['skipped'])} skipped, {len(results['errors'])} errors.", 'info')

    return render_template('vehicles/import.html', form=form, results=results)
