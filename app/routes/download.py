from flask import Blueprint, send_file, current_app, Response
from app.models.file_queue import get_queue, FileStatus
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
        completed_files = queue.get_files_by_status(FileStatus.COMPLETED)

        if not completed_files:
            return Response("No completed files to download.", status=404, mimetype='text/plain')

        # Create a zip file in memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_obj in completed_files:
                if file_obj.output_path and os.path.exists(file_obj.output_path):
                    # Use the original filename for the file in the archive
                    arcname = os.path.basename(file_obj.filename)
                    zf.write(file_obj.output_path, arcname=arcname)
                else:
                    current_app.logger.warning(f"Output file not found for {file_obj.filename}, skipping.")

        memory_file.seek(0)
        
        # Generate a filename for the zip archive
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
