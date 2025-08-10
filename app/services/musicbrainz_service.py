"""
MusicBrainz API Service for MP3 Artwork Manager
Handles searching for releases and retrieving cover art from MusicBrainz and Cover Art Archive
"""
import musicbrainzngs
import requests
import tempfile
import os
import time
from flask import current_app
from urllib.parse import urljoin
import json


class MusicBrainzError(Exception):
    """Custom exception for MusicBrainz service errors"""
    pass


class MusicBrainzService:
    """Service for interacting with MusicBrainz API and Cover Art Archive"""
    
    def __init__(self):
        # Configure musicbrainzngs
        user_agent = current_app.config.get('MUSICBRAINZ_USER_AGENT', 'MP3ArtworkManager/1.0')
        musicbrainzngs.set_useragent(
            app="MP3 Artwork Manager",
            version="1.0",
            contact="https://github.com/mp3-artwork-manager"
        )
        
        # Rate limiting settings
        self.rate_limit_delay = current_app.config.get('MUSICBRAINZ_RATE_LIMIT', 1.0)
        self.timeout = current_app.config.get('MUSICBRAINZ_TIMEOUT', 10)
        self.last_request_time = 0
        
        # Cover Art Archive base URL
        self.coverart_base_url = "https://coverartarchive.org"
        
        current_app.logger.info("MusicBrainz service initialized")
    
    def _rate_limit(self):
        """Ensure we don't exceed MusicBrainz rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            current_app.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_releases(self, artist, title, album=None, limit=10):
        """
        Search for releases on MusicBrainz
        Returns list of release dictionaries
        """
        try:
            self._rate_limit()
            
            # Build fuzzy search query without field prefixes
            query_parts = []
            if artist:
                query_parts.append(artist)
            if title:
                query_parts.append(title)
            if album:
                query_parts.append(album)
            
            if not query_parts:
                current_app.logger.warning("No search terms provided for MusicBrainz search")
                return []
            
            query = " ".join(query_parts)
            current_app.logger.info(f"Searching MusicBrainz for: {query}")
            
            # Search for releases
            result = musicbrainzngs.search_releases(
                query=query,
                limit=limit,
                offset=0
            )
            
            releases = []
            if 'release-list' in result:
                for release in result['release-list']:
                    release_info = self._parse_release(release)
                    if release_info:
                        releases.append(release_info)
            
            current_app.logger.info(f"Found {len(releases)} releases for query: {query}")
            return releases
            
        except Exception as e:
            error_msg = f"MusicBrainz search failed: {str(e)}"
            current_app.logger.error(error_msg)
            raise MusicBrainzError(error_msg)
    
    def _parse_release(self, release):
        """Parse MusicBrainz release data into our format"""
        try:
            release_id = release.get('id')
            if not release_id:
                return None
            
            # Get basic release info
            title = release.get('title', 'Unknown Title')
            
            # Get artist info
            artist_name = 'Unknown Artist'
            if 'artist-credit' in release:
                artists = []
                for credit in release['artist-credit']:
                    if isinstance(credit, dict) and 'artist' in credit:
                        artists.append(credit['artist'].get('name', ''))
                    elif isinstance(credit, str):
                        artists.append(credit)
                artist_name = ''.join(artists)
            
            # Get additional info
            date = release.get('date', '')
            country = release.get('country', '')
            
            # Calculate score based on available information
            score = 50  # Base score
            if date:
                score += 20
            if country:
                score += 10
            if 'artist-credit' in release:
                score += 20
            
            return {
                'id': release_id,
                'title': title,
                'artist': artist_name,
                'date': date,
                'country': country,
                'score': score,
                'source': 'musicbrainz'
            }
            
        except Exception as e:
            current_app.logger.error(f"Error parsing release: {str(e)}")
            return None
    
    def get_cover_art(self, release_id):
        """
        Get cover art URLs for a MusicBrainz release
        Returns list of artwork dictionaries
        """
        try:
            self._rate_limit()
            
            # Try to get cover art from Cover Art Archive
            coverart_url = f"{self.coverart_base_url}/release/{release_id}"
            
            current_app.logger.info(f"Fetching cover art for release {release_id}")
            
            response = requests.get(coverart_url, timeout=self.timeout)
            
            if response.status_code == 404:
                current_app.logger.info(f"No cover art found for release {release_id}")
                return []
            
            if response.status_code != 200:
                current_app.logger.warning(f"Cover Art Archive returned status {response.status_code}")
                return []
            
            data = response.json()
            artwork_list = []
            
            if 'images' in data:
                for i, image in enumerate(data['images']):
                    artwork_info = self._parse_cover_art(image, release_id, i)
                    if artwork_info:
                        artwork_list.append(artwork_info)
            
            current_app.logger.info(f"Found {len(artwork_list)} cover art images for release {release_id}")
            return artwork_list
            
        except requests.RequestException as e:
            error_msg = f"Failed to fetch cover art for {release_id}: {str(e)}"
            current_app.logger.error(error_msg)
            raise MusicBrainzError(error_msg)
        except Exception as e:
            error_msg = f"Error processing cover art for {release_id}: {str(e)}"
            current_app.logger.error(error_msg)
            raise MusicBrainzError(error_msg)
    
    def _parse_cover_art(self, image_data, release_id, index):
        """Parse cover art data from Cover Art Archive"""
        try:
            # Get image URLs - prefer larger sizes
            image_url = None
            thumbnails = image_data.get('thumbnails', {})
            
            # Priority order: large, 500, 250, small, original
            for size in ['large', '500', '250', 'small']:
                if size in thumbnails:
                    image_url = thumbnails[size]
                    break
            
            if not image_url and 'image' in image_data:
                image_url = image_data['image']
            
            if not image_url:
                return None
            
            # Determine image type
            image_types = image_data.get('types', [])
            is_front = 'Front' in image_types
            is_back = 'Back' in image_types
            
            # Determine primary type
            primary_type = 'Front' if is_front else ('Back' if is_back else 'Other')
            
            artwork_info = {
                'source': 'musicbrainz',
                'release_id': release_id,
                'image_url': image_url,
                'types': image_types,
                'primary_type': primary_type,
                'is_front': is_front,
                'is_back': is_back,
                'approved': image_data.get('approved', False),
                'comment': image_data.get('comment', ''),
                'index': index
            }
            
            # Add thumbnail URLs if available
            if thumbnails:
                artwork_info['thumbnails'] = thumbnails
            
            return artwork_info
            
        except Exception as e:
            current_app.logger.error(f"Error parsing cover art image: {str(e)}")
            return None
    
    def download_artwork(self, artwork_info, output_path=None):
        """
        Download artwork from URL to local file
        Returns path to downloaded file
        """
        try:
            image_url = artwork_info.get('image_url')
            if not image_url:
                raise MusicBrainzError("No image URL provided")
            
            if output_path is None:
                # Generate temporary file
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix='_musicbrainz.jpg',
                    dir=current_app.config['TEMP_FOLDER']
                )
                output_path = temp_file.name
                temp_file.close()
            
            current_app.logger.info(f"Downloading artwork from {image_url}")
            
            # Download the image
            response = requests.get(image_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Write to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            current_app.logger.info(f"Downloaded artwork to {output_path} ({file_size} bytes)")
            
            return {
                'success': True,
                'local_path': output_path,
                'file_size': file_size,
                'source_url': image_url,
                'artwork_info': artwork_info
            }
            
        except Exception as e:
            error_msg = f"Failed to download artwork: {str(e)}"
            current_app.logger.error(error_msg)
            
            # Clean up partial download
            if output_path and os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass
            
            raise MusicBrainzError(error_msg)
    
    def search_and_get_artwork(self, artist, title, album=None, max_results=5):
        """
        Complete workflow: search for releases and get their cover art
        Returns list of artwork options
        """
        try:
            current_app.logger.info(f"Starting artwork search for: {artist} - {title}")
            
            # Search for releases
            releases = self.search_releases(artist, title, album, limit=max_results)
            
            if not releases:
                current_app.logger.info("No releases found")
                return []
            
            all_artwork = []
            
            # Get cover art for each release
            for release in releases:
                try:
                    cover_art = self.get_cover_art(release['id'])
                    
                    # Add release info to each artwork
                    for artwork in cover_art:
                        artwork.update({
                            'release_title': release['title'],
                            'release_artist': release['artist'],
                            'release_date': release['date'],
                            'release_score': release['score']
                        })
                        all_artwork.append(artwork)
                        
                except Exception as e:
                    current_app.logger.error(f"Failed to get cover art for release {release['id']}: {str(e)}")
                    continue
            
            # Sort by release score and front cover preference
            all_artwork.sort(key=lambda x: (x.get('release_score', 0), x.get('is_front', False)), reverse=True)
            
            current_app.logger.info(f"Found {len(all_artwork)} artwork options")
            return all_artwork
            
        except Exception as e:
            error_msg = f"Artwork search workflow failed: {str(e)}"
            current_app.logger.error(error_msg)
            raise MusicBrainzError(error_msg)
    
    def batch_download_artwork(self, artwork_list, output_dir=None):
        """
        Download multiple artworks
        Returns list of download results
        """
        if output_dir is None:
            output_dir = current_app.config['TEMP_FOLDER']
        
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(current_app.root_path, '..', output_dir)
            
        results = []
        
        for i, artwork in enumerate(artwork_list):
            try:
                # Generate output filename
                filename = f"musicbrainz_{artwork.get('release_id', 'unknown')}_{i}.jpg"
                output_path = os.path.join(output_dir, filename)
                
                result = self.download_artwork(artwork, output_path)
                results.append(result)
                
            except Exception as e:
                current_app.logger.error(f"Failed to download artwork {i}: {str(e)}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'artwork_info': artwork
                })
        
        successful = sum(1 for r in results if r.get('success', False))
        current_app.logger.info(f"Batch download completed: {successful}/{len(artwork_list)} successful")
        
        return results
    
    def test_connection(self):
        """Test MusicBrainz API connection"""
        try:
            # Simple test query
            result = musicbrainzngs.search_artists("test", limit=1)
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
