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
        completed_files = queue.get_files_by_status(FileStatus.COMPLETED)

        if not completed_files:
            return Response("No completed files to download.", status=404, mimetype='text/plain')

        output_service = MP3OutputService()
        memory_file = io.BytesIO()

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_obj in completed_files:
                try:
                    # If output path doesn't exist, generate it
                    if not file_obj.output_path or not os.path.exists(file_obj.output_path):
                        if not file_obj.selected_artwork:
                            current_app.logger.warning(f"No artwork selected for {file_obj.filename}, skipping.")
                            continue
                        
                        current_app.logger.info(f"Generating output for {file_obj.filename} before zipping.")
                        result = output_service.process_file_with_selection(file_obj)
                        file_obj.output_path = result['output_path']
                        queue.update_file(file_obj.id, output_path=result['output_path'])

                    # Add to zip
                    if file_obj.output_path and os.path.exists(file_obj.output_path):
                        arcname = os.path.basename(file_obj.filename)
                        zf.write(file_obj.output_path, arcname=arcname)
                    else:
                        current_app.logger.warning(f"Output file still not found for {file_obj.filename} after attempting generation, skipping.")
                
                except MP3OutputError as e:
                    current_app.logger.error(f"Failed to generate output for {file_obj.filename} during zip creation: {str(e)}")
                    # Optionally, add a text file to the zip indicating the error
                    zf.writestr(f"{os.path.basename(file_obj.filename)}-ERROR.txt", f"Failed to process this file: {str(e)}")


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
