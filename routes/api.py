"""
Lightweight JSON API endpoints for AJAX / dynamic UI features.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import db, Vehicle, ReconTask

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
