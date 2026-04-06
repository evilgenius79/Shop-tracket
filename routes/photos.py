import os
import uuid
from flask import Blueprint, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Vehicle, VehiclePhoto
from forms import PhotoUploadForm
from routes.activity import log_activity

photos_bp = Blueprint('photos', __name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_PHOTOS_PER_VEHICLE = 30


def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _vehicle_upload_dir(vehicle_id):
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vehicles', str(vehicle_id))
    os.makedirs(path, exist_ok=True)
    return path


@photos_bp.route('/vehicles/<int:vehicle_id>/photos/upload', methods=['POST'])
@login_required
def upload_photos(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    files = request.files.getlist('photos')

    if not files or all(f.filename == '' for f in files):
        flash('No files selected.', 'warning')
        return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))

    existing_count = vehicle.photos.count()
    saved = 0

    for file in files:
        if not file or file.filename == '':
            continue
        if not _allowed(file.filename):
            flash(f'"{file.filename}" is not an allowed image type (jpg, png, gif, webp).', 'warning')
            continue
        if existing_count + saved >= MAX_PHOTOS_PER_VEHICLE:
            flash(f'Maximum {MAX_PHOTOS_PER_VEHICLE} photos per vehicle reached.', 'warning')
            break

        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f'{uuid.uuid4().hex}.{ext}'
        save_path = os.path.join(_vehicle_upload_dir(vehicle_id), unique_name)
        file.save(save_path)

        is_primary = (existing_count + saved == 0)
        photo = VehiclePhoto(
            vehicle_id=vehicle_id,
            filename=unique_name,
            caption=request.form.get('caption', '').strip() or None,
            is_primary=is_primary,
            sort_order=existing_count + saved,
            created_by_id=current_user.id,
        )
        db.session.add(photo)
        saved += 1

    if saved:
        db.session.commit()
        log_activity(vehicle_id, 'Photos uploaded', f'{saved} photo(s) added')
        flash(f'{saved} photo(s) uploaded.', 'success')

    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))


@photos_bp.route('/photos/<int:photo_id>/delete', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = VehiclePhoto.query.get_or_404(photo_id)
    vehicle_id = photo.vehicle_id

    if photo.created_by_id != current_user.id and not current_user.is_manager_or_above():
        abort(403)

    # Remove file from disk
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vehicles',
                        str(vehicle_id), photo.filename)
    if os.path.exists(path):
        os.remove(path)

    was_primary = photo.is_primary
    db.session.delete(photo)
    db.session.flush()

    # Promote the next photo to primary if this was primary
    if was_primary:
        next_photo = VehiclePhoto.query.filter_by(vehicle_id=vehicle_id).order_by(VehiclePhoto.sort_order).first()
        if next_photo:
            next_photo.is_primary = True

    db.session.commit()
    log_activity(vehicle_id, 'Photo deleted', photo.filename)
    flash('Photo deleted.', 'success')
    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))


@photos_bp.route('/photos/<int:photo_id>/set-primary', methods=['POST'])
@login_required
def set_primary_photo(photo_id):
    photo = VehiclePhoto.query.get_or_404(photo_id)
    vehicle_id = photo.vehicle_id

    # Clear existing primary
    VehiclePhoto.query.filter_by(vehicle_id=vehicle_id, is_primary=True).update({'is_primary': False})
    photo.is_primary = True
    db.session.commit()
    flash('Primary photo updated.', 'success')
    return redirect(url_for('vehicles.vehicle_detail', vehicle_id=vehicle_id))
