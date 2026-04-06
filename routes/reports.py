from datetime import date, timedelta
from flask import Blueprint, render_template, request, make_response
from flask_login import login_required
from sqlalchemy import func
from models import db, Vehicle, Expense, Sale, EXPENSE_CATEGORIES
import csv
import io

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')


@reports_bp.route('/inventory')
@login_required
def inventory_report():
    status_filter = request.args.get('status', '')
    query = Vehicle.query
    if status_filter:
        query = query.filter(Vehicle.status == status_filter)
    vehicles = query.order_by(Vehicle.purchase_date.asc()).all()

    total_purchase = sum(float(v.purchase_price) for v in vehicles)
    total_recon = sum(v.recon_cost for v in vehicles)
    total_cost = sum(v.total_cost for v in vehicles)
    total_asking = sum(float(v.asking_price) for v in vehicles if v.asking_price)
    avg_days = sum(v.days_on_lot for v in vehicles) / len(vehicles) if vehicles else 0

    return render_template('reports/inventory.html',
        vehicles=vehicles,
        status_filter=status_filter,
        total_purchase=total_purchase,
        total_recon=total_recon,
        total_cost=total_cost,
        total_asking=total_asking,
        avg_days=avg_days,
    )


@reports_bp.route('/profit-loss')
@login_required
def profit_loss():
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', 0, type=int)
    # Clamp to sane ranges
    if year < 1900 or year > today.year + 1:
        year = today.year
    if month < 0 or month > 12:
        month = 0

    query = db.session.query(Vehicle).join(Sale).filter(Vehicle.status == 'Sold')

    if month:
        query = query.filter(
            func.strftime('%Y', Sale.sale_date) == str(year),
            func.strftime('%m', Sale.sale_date) == f'{month:02d}',
        )
    else:
        query = query.filter(
            func.strftime('%Y', Sale.sale_date) == str(year),
        )

    sold_vehicles = query.order_by(Sale.sale_date.desc()).all()

    total_revenue = sum(float(v.sale.sale_price) for v in sold_vehicles)
    total_cost = sum(v.total_cost for v in sold_vehicles)
    total_gross = sum(v.gross_profit for v in sold_vehicles if v.gross_profit is not None)
    avg_gross = total_gross / len(sold_vehicles) if sold_vehicles else 0

    # Available years
    years = db.session.query(
        func.strftime('%Y', Sale.sale_date)
    ).distinct().order_by(func.strftime('%Y', Sale.sale_date).desc()).all()
    available_years = [int(y[0]) for y in years if y[0]]
    if date.today().year not in available_years:
        available_years.insert(0, date.today().year)

    return render_template('reports/profit_loss.html',
        sold_vehicles=sold_vehicles,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_gross=total_gross,
        avg_gross=avg_gross,
        year=year,
        month=month,
        available_years=available_years,
    )


@reports_bp.route('/aging')
@login_required
def aging_report():
    active = Vehicle.query.filter(
        Vehicle.status.notin_(['Sold', 'Wholesale', 'Junked'])
    ).all()

    buckets = {
        '0-14 days': [],
        '15-30 days': [],
        '31-60 days': [],
        '61-90 days': [],
        '90+ days': [],
    }
    for v in active:
        d = v.days_on_lot
        if d <= 14:
            buckets['0-14 days'].append(v)
        elif d <= 30:
            buckets['15-30 days'].append(v)
        elif d <= 60:
            buckets['31-60 days'].append(v)
        elif d <= 90:
            buckets['61-90 days'].append(v)
        else:
            buckets['90+ days'].append(v)

    # Sort each bucket by days desc
    for k in buckets:
        buckets[k].sort(key=lambda v: v.days_on_lot, reverse=True)

    return render_template('reports/aging.html', buckets=buckets, active_count=len(active))


@reports_bp.route('/expenses')
@login_required
def expense_report():
    _today = date.today()
    year = request.args.get('year', _today.year, type=int)
    if year < 1900 or year > _today.year + 1:
        year = _today.year
    category_filter = request.args.get('category', '')

    query = Expense.query.filter(
        func.strftime('%Y', Expense.expense_date) == str(year)
    )
    if category_filter:
        query = query.filter(Expense.category == category_filter)

    expenses = query.order_by(Expense.expense_date.desc()).all()

    # By category totals
    cat_totals = {}
    for exp in expenses:
        cat_totals[exp.category] = cat_totals.get(exp.category, 0) + float(exp.amount)

    # By subcategory
    sub_totals = {}
    for exp in expenses:
        key = f'{exp.category} > {exp.subcategory}'
        sub_totals[key] = sub_totals.get(key, 0) + float(exp.amount)

    total_spend = sum(float(e.amount) for e in expenses)

    years = db.session.query(
        func.strftime('%Y', Expense.expense_date)
    ).distinct().order_by(func.strftime('%Y', Expense.expense_date).desc()).all()
    available_years = [int(y[0]) for y in years if y[0]]
    if date.today().year not in available_years:
        available_years.insert(0, date.today().year)

    return render_template('reports/expenses.html',
        expenses=expenses,
        cat_totals=cat_totals,
        sub_totals=sub_totals,
        total_spend=total_spend,
        year=year,
        category_filter=category_filter,
        available_years=available_years,
        expense_categories=EXPENSE_CATEGORIES,
    )


@reports_bp.route('/performance')
@login_required
def performance_report():
    """Best/worst performers by make, model, source."""
    sold = db.session.query(Vehicle).join(Sale).filter(Vehicle.status == 'Sold').all()

    # By make
    make_stats = {}
    for v in sold:
        if v.gross_profit is None:
            continue
        make_stats.setdefault(v.make, {'count': 0, 'total_gp': 0, 'total_days': 0, 'total_cost': 0})
        make_stats[v.make]['count'] += 1
        make_stats[v.make]['total_gp'] += v.gross_profit
        make_stats[v.make]['total_days'] += v.days_on_lot
        make_stats[v.make]['total_cost'] += v.total_cost

    for make in make_stats:
        c = make_stats[make]['count']
        make_stats[make]['avg_gp'] = make_stats[make]['total_gp'] / c
        make_stats[make]['avg_days'] = make_stats[make]['total_days'] / c

    make_list = sorted(make_stats.items(), key=lambda x: x[1]['avg_gp'], reverse=True)

    # By source
    source_stats = {}
    for v in sold:
        if v.gross_profit is None:
            continue
        src = v.purchase_source or 'Unknown'
        source_stats.setdefault(src, {'count': 0, 'total_gp': 0})
        source_stats[src]['count'] += 1
        source_stats[src]['total_gp'] += v.gross_profit

    for src in source_stats:
        source_stats[src]['avg_gp'] = source_stats[src]['total_gp'] / source_stats[src]['count']

    source_list = sorted(source_stats.items(), key=lambda x: x[1]['avg_gp'], reverse=True)

    return render_template('reports/performance.html',
        make_list=make_list,
        source_list=source_list,
        sold_count=len(sold),
    )


@reports_bp.route('/export/inventory.csv')
@login_required
def export_inventory_csv():
    vehicles = Vehicle.query.order_by(Vehicle.purchase_date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Stock #', 'VIN', 'Year', 'Make', 'Model', 'Trim', 'Color',
        'Mileage', 'Purchase Date', 'Purchase Price', 'Recon Cost',
        'Total Cost', 'Asking Price', 'Status', 'Days on Lot',
        'Title Status', 'Source', 'Lot Location', 'Notes'
    ])
    for v in vehicles:
        writer.writerow([
            v.stock_number, v.vin or '', v.year, v.make, v.model, v.trim or '',
            v.color_exterior or '', v.mileage or '', v.purchase_date,
            float(v.purchase_price), v.recon_cost, v.total_cost,
            float(v.asking_price) if v.asking_price else '',
            v.status, v.days_on_lot, v.title_status or '',
            v.purchase_source or '', v.lot_location or '', v.notes or ''
        ])
    output.seek(0)
    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = f'attachment; filename=inventory_{date.today()}.csv'
    return resp


@reports_bp.route('/export/sales.csv')
@login_required
def export_sales_csv():
    vehicles = db.session.query(Vehicle).join(Sale).filter(Vehicle.status == 'Sold').order_by(Sale.sale_date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Stock #', 'Year', 'Make', 'Model', 'Purchase Date', 'Purchase Price',
        'Recon Cost', 'Total Cost', 'Sale Date', 'Sale Price', 'Sale Type',
        'Gross Profit', 'Days on Lot'
    ])
    for v in vehicles:
        writer.writerow([
            v.stock_number, v.year, v.make, v.model,
            v.purchase_date, float(v.purchase_price), v.recon_cost, v.total_cost,
            v.sale.sale_date, float(v.sale.sale_price), v.sale.sale_type or '',
            v.gross_profit or '', v.days_on_lot
        ])
    output.seek(0)
    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = f'attachment; filename=sales_{date.today()}.csv'
    return resp
