from flask import Blueprint, send_file, current_app, Response
from app.models.file_queue import get_queue, FileStatus
from app.services.mp3_output_service import MP3OutputService, MP3OutputError
import os
import io
import zipfile
from datetime import datetime

bp = Blueprint('download', __name__, url_prefix='/api')

@bp.route('/download/all', methods=['GET'])
def download_all_completed():
    """Download all completed files as a single zip archive"""
    try:
        queue = get_queue()
        # Filter for files that are complete AND have an output path
        files_to_zip = [f for f in queue.get_all_files() if f.status == FileStatus.COMPLETED and f.output_path and os.path.exists(f.output_path)]

        if not files_to_zip:
            return Response("No downloadable files found. Please generate the output files first.", status=404, mimetype='text/plain')

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_obj in files_to_zip:
                arcname = os.path.basename(file_obj.filename)
                zf.write(file_obj.output_path, arcname=arcname)

        memory_file.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"mp3-vibe-artwork-completed-{timestamp}.zip"

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )

    except Exception as e:
        current_app.logger.error(f"Failed to create zip archive for download: {str(e)}")
        return Response("Failed to generate download.", status=500, mimetype='text/plain')

# TODO: Implement individual file download endpoint in Phase 7
