from flask import Blueprint, jsonify, request, send_file, current_app, redirect
import os
from app.models.file_queue import get_queue
from app.services.image_optimizer import ImageOptimizer
import requests
from PIL import Image
from io import BytesIO

bp = Blueprint('artwork', __name__, url_prefix='/api')


@bp.route('/artwork/<file_id>', methods=['GET'])
def get_artwork_options(file_id):
    """Get all available artwork options for a file"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        artwork_options = []
        
        # Add embedded artwork options
        for artwork in file_obj.artwork_options:
            if artwork['source'] == 'embedded':
                artwork_option = {
                    'id': artwork['id'],
                    'source': 'embedded',
                    'image_path': artwork['image_path'],
                    'dimensions': artwork['dimensions'],
                    'file_size': artwork['file_size'],
                    'metadata': artwork['metadata'],
                    'preview_url': f'/api/artwork/{file_id}/preview/{artwork["id"]}',
                    'needs_optimization': artwork.get('needs_optimization', False),
                    'optimized_path': artwork.get('optimized_path'),
                    'optimized_dimensions': artwork.get('optimized_dimensions'),
                    'optimized_size': artwork.get('optimized_size')
                }
                artwork_options.append(artwork_option)
            
            # Add MusicBrainz artwork options (these would be added by processing)
            elif artwork['source'] == 'musicbrainz':
                # For MusicBrainz, the image_path is a URL
                artwork_option = {
                    'id': artwork['id'],
                    'source': 'musicbrainz',
                    'image_url': artwork['image_path'],  # This is a URL
                    'dimensions': artwork.get('dimensions'),
                    'file_size': artwork.get('file_size'),
                    'metadata': artwork.get('metadata', {}),
                    'preview_url': artwork['image_path'],  # The preview is the direct URL
                    'needs_optimization': False, # Not applicable for remote images
                }
                artwork_options.append(artwork_option)
        
        return jsonify({
            'file_id': file_id,
            'filename': file_obj.filename,
            'artwork_options': artwork_options,
            'selected_artwork': file_obj.selected_artwork,
            'total_options': len(artwork_options)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting artwork options for {file_id}: {str(e)}")
        return jsonify({'error': 'Failed to get artwork options'}), 500


@bp.route('/artwork/<file_id>/preview/<artwork_id>', methods=['GET'])
def get_artwork_preview(file_id, artwork_id):
    """Get artwork preview image"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        # Find the artwork
        artwork = None
        for art in file_obj.artwork_options:
            if art['id'] == artwork_id:
                artwork = art
                break
        
        if not artwork:
            return jsonify({'error': 'Artwork not found'}), 404
        
        # For MusicBrainz artwork, redirect to the URL
        if artwork['source'] == 'musicbrainz':
            return redirect(artwork['image_path'])

        # Determine which image to serve
        image_path = artwork.get('optimized_path') or artwork['image_path']
        
        if not os.path.exists(image_path):
            return jsonify({'error': 'Image file not found'}), 404
        
        # Create thumbnail if requested
        thumbnail = request.args.get('thumbnail', 'false').lower() == 'true'
        if thumbnail:
            optimizer = ImageOptimizer()
            try:
                thumbnail_path = optimizer.create_thumbnail(image_path)
                return send_file(thumbnail_path, mimetype='image/jpeg')
            except Exception as e:
                current_app.logger.error(f"Failed to create thumbnail: {str(e)}")
                # Fall back to original image
        
        # Determine MIME type
        mime_type = 'image/jpeg'
        if image_path.lower().endswith('.png'):
            mime_type = 'image/png'
        
        return send_file(image_path, mimetype=mime_type)
        
    except Exception as e:
        current_app.logger.error(f"Error serving artwork preview: {str(e)}")
        return jsonify({'error': 'Failed to serve artwork preview'}), 500


@bp.route('/artwork/<file_id>/select', methods=['POST'])
def select_artwork(file_id):
    """Select artwork for a file"""
    try:
        data = request.get_json()
        if not data or 'artwork_id' not in data:
            return jsonify({'error': 'No artwork_id provided'}), 400
        
        artwork_id = data['artwork_id']
        
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        # Find the artwork to be selected
        selected_artwork_obj = None
        for art in file_obj.artwork_options:
            if art['id'] == artwork_id:
                selected_artwork_obj = art
                break

        if not selected_artwork_obj:
            return jsonify({'error': 'Artwork not found'}), 404

        # If the selected artwork is from MusicBrainz, we don't need to optimize
        if selected_artwork_obj['source'] != 'musicbrainz':
            # Check if optimization is needed before selecting
            optimizer = ImageOptimizer()
            image_info = optimizer.get_image_info(selected_artwork_obj['image_path'])

            if image_info.get('needs_optimization', False):
                try:
                    # Optimize the image
                    optimization_result = optimizer.optimize_image(selected_artwork_obj['image_path'])
                    
                    # Update the artwork object with optimization data
                    selected_artwork_obj['optimized_path'] = optimization_result['output_path']
                    selected_artwork_obj['optimized_dimensions'] = optimization_result['final_dimensions']
                    selected_artwork_obj['optimized_size'] = optimization_result['final_size']
                    selected_artwork_obj['needs_optimization'] = False # Mark as optimized
                    
                    current_app.logger.info(f"Optimized artwork {artwork_id} for file {file_obj.filename}")

                except Exception as e:
                    current_app.logger.error(f"Failed to optimize artwork {artwork_id} on selection: {str(e)}")
                    # Continue without optimization if it fails
        
        # Now, select the artwork (which may have been updated)
        if file_obj.select_artwork(artwork_id):
            # Save the queue with the selection
            queue._save_queue()
            
            current_app.logger.info(f"Selected artwork {artwork_id} for file {file_obj.filename}")
            
            return jsonify({
                'message': 'Artwork selected successfully',
                'file_id': file_id,
                'selected_artwork_id': artwork_id,
                'selected_artwork': file_obj.selected_artwork
            }), 200
        else:
            return jsonify({'error': 'Artwork not found'}), 404
        
    except Exception as e:
        current_app.logger.error(f"Error selecting artwork: {str(e)}")
        return jsonify({'error': 'Failed to select artwork'}), 500


@bp.route('/artwork/<file_id>/compare', methods=['GET'])
def compare_artwork(file_id):
    """Get artwork comparison data with detailed information"""
    try:
        queue = get_queue()
        file_obj = queue.get_file(file_id)
        
        if not file_obj:
            return jsonify({'error': 'File not found'}), 404
        
        comparison_data = {
            'file_info': {
                'id': file_id,
                'filename': file_obj.filename,
                'metadata': file_obj.metadata
            },
            'artwork_options': []
        }
        
        optimizer = ImageOptimizer()
        
        for artwork in file_obj.artwork_options:
            try:
                # Get detailed image info
                if artwork['source'] == 'musicbrainz':
                    try:
                        # Fetch image from URL
                        response = requests.get(artwork['image_path'], timeout=10)
                        response.raise_for_status()
                        
                        image_data = response.content
                        file_size = len(image_data)
                        
                        # Get dimensions
                        img = Image.open(BytesIO(image_data))
                        dimensions = {'width': img.width, 'height': img.height}
                        aspect_ratio = img.width / img.height if img.height > 0 else 0
                        
                        # Get format
                        image_format = img.format or "JPEG" # Fallback to JPEG

                        artwork_detail = {
                            'id': artwork['id'],
                            'source': artwork['source'],
                            'preview_url': artwork['image_path'],
                            'thumbnail_url': artwork['image_path'],
                            'dimensions': dimensions,
                            'file_size': file_size,
                            'format': image_format,
                            'aspect_ratio': aspect_ratio,
                            'needs_optimization': False,
                            'metadata': artwork.get('metadata', {}),
                            'is_optimized': False,
                            'optimization_savings': None
                        }

                    except requests.exceptions.RequestException as e:
                        current_app.logger.warning(f"Failed to fetch MusicBrainz image {artwork['image_path']}: {e}")
                        artwork_detail = {
                            'id': artwork['id'],
                            'source': artwork['source'],
                            'preview_url': artwork['image_path'],
                            'thumbnail_url': artwork['image_path'],
                            'dimensions': None,
                            'file_size': None,
                            'format': "N/A",
                            'aspect_ratio': None,
                            'needs_optimization': False,
                            'metadata': artwork.get('metadata', {}),
                            'is_optimized': False,
                            'optimization_savings': None,
                            'error': f"Failed to fetch: {e}"
                        }
                    except Exception as e:
                        current_app.logger.error(f"Error processing MusicBrainz image {artwork['image_path']}: {e}")
                        continue

                    comparison_data['artwork_options'].append(artwork_detail)
                    continue

                image_path = artwork.get('optimized_path') or artwork['image_path']
                
                if os.path.exists(image_path):
                    image_info = optimizer.get_image_info(image_path)
                    
                    artwork_detail = {
                        'id': artwork['id'],
                        'source': artwork['source'],
                        'preview_url': f'/api/artwork/{file_id}/preview/{artwork["id"]}',
                        'thumbnail_url': f'/api/artwork/{file_id}/preview/{artwork["id"]}?thumbnail=true',
                        'dimensions': image_info['dimensions'],
                        'file_size': image_info['file_size'],
                        'file_size_mb': image_info['file_size_mb'],
                        'format': image_info['format'],
                        'aspect_ratio': image_info['aspect_ratio'],
                        'needs_optimization': image_info['needs_optimization'],
                        'metadata': artwork.get('metadata', {}),
                        'is_optimized': bool(artwork.get('optimized_path')),
                        'optimization_savings': None
                    }
                    
                    # Calculate optimization savings if optimized
                    if artwork.get('optimized_path') and artwork.get('file_size'):
                        original_size = artwork['file_size']
                        optimized_size = image_info['file_size']
                        savings = original_size - optimized_size
                        artwork_detail['optimization_savings'] = {
                            'original_size': original_size,
                            'optimized_size': optimized_size,
                            'bytes_saved': savings,
                            'percent_saved': (savings / original_size * 100) if original_size > 0 else 0
                        }
                    
                    comparison_data['artwork_options'].append(artwork_detail)
                    
            except Exception as e:
                current_app.logger.error(f"Error processing artwork {artwork['id']}: {str(e)}")
                continue
        
        # Sort by source (embedded first) and quality
        comparison_data['artwork_options'].sort(
            key=lambda x: (x['source'] != 'embedded', -(x['file_size'] if isinstance(x['file_size'], int) else 0))
        )
        
        return jsonify(comparison_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting comparison data: {str(e)}")
        return jsonify({'error': 'Failed to get comparison data'}), 500


@bp.route('/artwork/bulk-select', methods=['POST'])
def bulk_select_artwork():
    """Apply artwork selection to multiple files"""
    try:
        data = request.get_json()
        if not data or 'selections' not in data:
            return jsonify({'error': 'No selections provided'}), 400
        
        selections = data['selections']  # [{file_id: str, artwork_id: str}, ...]
        
        queue = get_queue()
        results = []
        
        for selection in selections:
            file_id = selection.get('file_id')
            artwork_id = selection.get('artwork_id')
            
            if not file_id or not artwork_id:
                results.append({'file_id': file_id, 'success': False, 'error': 'Missing file_id or artwork_id'})
                continue
            
            file_obj = queue.get_file(file_id)
            if not file_obj:
                results.append({'file_id': file_id, 'success': False, 'error': 'File not found'})
                continue
            
            if file_obj.select_artwork(artwork_id):
                results.append({'file_id': file_id, 'success': True, 'selected_artwork_id': artwork_id})
            else:
                results.append({'file_id': file_id, 'success': False, 'error': 'Artwork not found'})
        
        # Save all changes
        queue._save_queue()
        
        successful = sum(1 for r in results if r['success'])
        
        return jsonify({
            'message': f'Bulk selection completed: {successful}/{len(selections)} successful',
            'results': results,
            'successful_count': successful,
            'total_count': len(selections)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in bulk selection: {str(e)}")
        return jsonify({'error': 'Bulk selection failed'}), 500
