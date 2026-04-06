from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, Vehicle, ReconTask, User
from forms import ReconTaskForm, RECON_STAGE_CHOICES

recon_bp = Blueprint('recon', __name__)
_VALID_STAGES = {s for s, _ in RECON_STAGE_CHOICES}


def _populate_assignee_choices(form):
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    form.assigned_to_id.choices = [(0, '-- Unassigned --')] + [(u.id, u.username) for u in users]


@recon_bp.route('/vehicles/<int:vehicle_id>/recon/add', methods=['GET', 'POST'])
@login_required
def add_recon_task(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = ReconTaskForm()
    form.vehicle_id.data = vehicle_id
    _populate_assignee_choices(form)

    if request.method == 'GET':
        form.status.data = 'Pending'
        form.priority.data = 'Normal'
        # Pre-select stage from query param — validate against allowed list
        stage = request.args.get('stage', 'Inspection')
        form.stage.data = stage if stage in _VALID_STAGES else 'Inspection'

    if form.validate_on_submit():
        task = ReconTask(
            vehicle_id=vehicle_id,
            stage=form.stage.data,
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            priority=form.priority.data,
            vendor=form.vendor.data,
            assigned_to_id=form.assigned_to_id.data if form.assigned_to_id.data else None,
            estimated_cost=form.estimated_cost.data,
            actual_cost=form.actual_cost.data,
            due_date=form.due_date.data,
            completed_date=form.completed_date.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
        )
        db.session.add(task)
        db.session.commit()
        flash(f'Recon task "{task.title}" added.', 'success')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))

    return render_template('recon/form.html', form=form, vehicle=vehicle, title='Add Recon Task')


@recon_bp.route('/recon/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recon_task(task_id):
    task = ReconTask.query.get_or_404(task_id)
    if task.created_by_id != current_user.id and not current_user.is_manager_or_above():
        abort(403)
    vehicle = task.vehicle
    form = ReconTaskForm(obj=task)
    _populate_assignee_choices(form)

    if form.validate_on_submit():
        task.stage = form.stage.data
        task.title = form.title.data
        task.description = form.description.data
        task.status = form.status.data
        task.priority = form.priority.data
        task.vendor = form.vendor.data
        task.assigned_to_id = form.assigned_to_id.data if form.assigned_to_id.data else None
        task.estimated_cost = form.estimated_cost.data
        task.actual_cost = form.actual_cost.data
        task.due_date = form.due_date.data
        task.completed_date = form.completed_date.data
        task.notes = form.notes.data

        # Auto-set completed date
        if task.status == 'Done' and not task.completed_date:
            task.completed_date = date.today()

        db.session.commit()
        flash(f'Task "{task.title}" updated.', 'success')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle.id))

    return render_template('recon/form.html', form=form, vehicle=vehicle, title='Edit Recon Task')


@recon_bp.route('/recon/<int:task_id>/status', methods=['POST'])
@login_required
def update_task_status(task_id):
    task = ReconTask.query.get_or_404(task_id)
    new_status = request.form.get('status')
    if new_status in ('Pending', 'In Progress', 'Done', 'Skipped'):
        task.status = new_status
        if new_status == 'Done' and not task.completed_date:
            task.completed_date = date.today()
        db.session.commit()
        flash(f'Task status updated to {new_status}.', 'success')
    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=task.vehicle_id))


@recon_bp.route('/recon/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_recon_task(task_id):
    task = ReconTask.query.get_or_404(task_id)
    if task.created_by_id != current_user.id and not current_user.is_manager_or_above():
        abort(403)
    vehicle_id = task.vehicle_id
    db.session.delete(task)
    db.session.commit()
    flash('Recon task deleted.', 'success')
    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))
