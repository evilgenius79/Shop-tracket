"""
Lightweight JSON API endpoints for AJAX / dynamic UI features.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Vehicle, ReconTask, PriceHistory

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/vehicles/<int:vehicle_id>/status', methods=['POST'])
@login_required
def update_vehicle_status(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    valid = ('In Recon', 'Available', 'Pending Sale', 'Sold', 'Wholesale', 'On Hold', 'Junked')
    if new_status not in valid:
        return jsonify({'error': 'Invalid status'}), 400
    vehicle.status = new_status
    db.session.commit()
    return jsonify({'status': vehicle.status, 'stock_number': vehicle.stock_number})


@api_bp.route('/vehicles/search')
@login_required
def search_vehicles():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    like = f'%{q}%'
    results = Vehicle.query.filter(
        db.or_(
            Vehicle.make.ilike(like),
            Vehicle.model.ilike(like),
            Vehicle.stock_number.ilike(like),
            Vehicle.vin.ilike(like),
        )
    ).limit(10).all()
    return jsonify([{
        'id': v.id,
        'text': f'{v.stock_number} – {v.display_name}',
        'status': v.status,
    } for v in results])


@api_bp.route('/vehicles/<int:vehicle_id>/asking-price', methods=['POST'])
@login_required
def update_asking_price(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json(silent=True) or {}
    try:
        new_price = float(data.get('asking_price', ''))
        if new_price < 0:
            raise ValueError('negative')
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid price'}), 400

    old_price = float(vehicle.asking_price) if vehicle.asking_price else None
    vehicle.asking_price = new_price

    ph = PriceHistory(
        vehicle_id=vehicle.id,
        old_price=old_price,
        new_price=new_price,
        changed_by_id=current_user.id,
    )
    db.session.add(ph)
    db.session.commit()

    from routes.activity import log_activity
    log_activity(vehicle.id, 'Asking price changed',
                 f'${old_price:,.2f} → ${new_price:,.2f}' if old_price is not None
                 else f'Set to ${new_price:,.2f}')
    db.session.commit()

    return jsonify({'asking_price': float(vehicle.asking_price),
                    'formatted': f'${vehicle.asking_price:,.2f}'})


@api_bp.route('/vehicles/<int:vehicle_id>/note', methods=['POST'])
@login_required
def update_note(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json(silent=True) or {}
    note = data.get('note', '').strip()
    vehicle.notes = note or None
    db.session.commit()
    return jsonify({'note': vehicle.notes or ''})


@api_bp.route('/recon/<int:task_id>/status', methods=['POST'])
@login_required
def update_recon_status(task_id):
    from datetime import date
    task = ReconTask.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    valid = ('Pending', 'In Progress', 'Done', 'Skipped')
    if new_status not in valid:
        return jsonify({'error': 'Invalid status'}), 400
    task.status = new_status
    if new_status == 'Done' and not task.completed_date:
        task.completed_date = date.today()
    db.session.commit()
    return jsonify({'status': task.status, 'task_id': task.id})
