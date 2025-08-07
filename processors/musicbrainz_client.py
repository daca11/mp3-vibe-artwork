#!/usr/bin/env python3
"""
MusicBrainz Client Module
Handles MusicBrainz API interactions for artwork discovery and metadata enhancement.
"""

import time
import logging
import requests
import musicbrainzngs
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

class MusicBrainzClient:
    """
    MusicBrainz API client with rate limiting and artwork discovery.
    """
    
    def __init__(self, user_agent: str = "MP3ArtworkManager/1.0", rate_limit: float = 1.0):
        """
        Initialize MusicBrainz client.
        
        Args:
            user_agent: User agent string for API requests
            rate_limit: Minimum seconds between API requests (default: 1.0)
        """
        self.rate_limit = rate_limit
        self.last_request_time = 0.0
        
        # Configure musicbrainzngs
        musicbrainzngs.set_useragent(
            app=user_agent.split('/')[0] if '/' in user_agent else user_agent,
            version=user_agent.split('/')[1] if '/' in user_agent else "1.0",
            contact="your-email@example.com"  # Should be configurable in production
        )
        
        logger.info(f"Initialized MusicBrainz client with User-Agent: {user_agent}")
    
    def _rate_limit_delay(self):
        """Ensure rate limiting compliance."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_release(self, artist: str, album: str = None, title: str = None, 
                      limit: int = 10) -> List[Dict]:
        """
        Search for releases in MusicBrainz.
        
        Args:
            artist: Artist name (required)
            album: Album name (optional)
            title: Track title (optional)
            limit: Maximum number of results to return
            
        Returns:
            List of release dictionaries with metadata and artwork info
        """
        if not artist or not artist.strip():
            logger.warning("Artist name is required for MusicBrainz search")
            return []
        
        try:
            self._rate_limit_delay()
            
            # Build search query
            query_parts = [f'artist:"{artist.strip()}"']
            
            if album and album.strip():
                query_parts.append(f'release:"{album.strip()}"')
            
            if title and title.strip():
                query_parts.append(f'recording:"{title.strip()}"')
            
            query = ' AND '.join(query_parts)
            logger.debug(f"MusicBrainz search query: {query}")
            
            # Perform search
            result = musicbrainzngs.search_releases(
                query=query,
                limit=limit
            )
            
            releases = result.get('release-list', [])
            logger.info(f"Found {len(releases)} releases for query: {query}")
            
            # Process and return results
            processed_releases = []
            for release in releases:
                processed_release = self._process_release(release)
                if processed_release:
                    processed_releases.append(processed_release)
            
            return processed_releases
            
        except musicbrainzngs.NetworkError as e:
            logger.error(f"MusicBrainz network error: {e}")
            return []
        except musicbrainzngs.ResponseError as e:
            logger.error(f"MusicBrainz API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in MusicBrainz search: {e}")
            return []
    
    def _process_release(self, release: Dict) -> Optional[Dict]:
        """
        Process a raw MusicBrainz release into our format.
        
        Args:
            release: Raw release data from MusicBrainz
            
        Returns:
            Processed release dictionary or None if invalid
        """
        try:
            release_id = release.get('id')
            if not release_id:
                return None
            
            # Extract basic metadata
            title = release.get('title', '')
            date = release.get('date', '')
            
            # Extract artist information
            artist_credits = release.get('artist-credit', [])
            artists = []
            for credit in artist_credits:
                if isinstance(credit, dict) and 'artist' in credit:
                    artist_name = credit['artist'].get('name', '')
                    if artist_name:
                        artists.append(artist_name)
                elif isinstance(credit, str):
                    artists.append(credit)
            
            artist = ', '.join(artists) if artists else 'Unknown Artist'
            
            # Prepare result
            processed = {
                'id': release_id,
                'title': title,
                'artist': artist,
                'date': date,
                'score': release.get('ext:score', 0),
                'artwork_urls': []  # Will be populated by get_artwork_urls
            }
            
            logger.debug(f"Processed release: {processed['artist']} - {processed['title']}")
            return processed
            
        except Exception as e:
            logger.warning(f"Error processing release: {e}")
            return None
    
    def get_artwork_urls(self, release_id: str) -> List[Dict]:
        """
        Get artwork URLs for a specific release from Cover Art Archive.
        
        Args:
            release_id: MusicBrainz release ID
            
        Returns:
            List of artwork dictionaries with URLs and metadata
        """
        try:
            self._rate_limit_delay()
            
            # Query Cover Art Archive
            try:
                artwork_data = musicbrainzngs.get_image_list(release_id)
            except musicbrainzngs.ResponseError as e:
                if "404" in str(e):
                    logger.debug(f"No artwork found for release {release_id}")
                    return []
                raise
            
            images = artwork_data.get('images', [])
            logger.debug(f"Found {len(images)} artwork images for release {release_id}")
            
            processed_images = []
            for image in images:
                processed_image = self._process_artwork_image(image)
                if processed_image:
                    processed_images.append(processed_image)
            
            # Sort by preference (front cover first, then by size)
            processed_images.sort(key=lambda x: (
                0 if x['is_front'] else 1,
                -x['width'] if x['width'] else 0
            ))
            
            return processed_images
            
        except Exception as e:
            logger.error(f"Error getting artwork for release {release_id}: {e}")
            return []
    
    def _process_artwork_image(self, image: Dict) -> Optional[Dict]:
        """
        Process a raw artwork image into our format.
        
        Args:
            image: Raw image data from Cover Art Archive
            
        Returns:
            Processed image dictionary or None if invalid
        """
        try:
            # Extract thumbnails and full image URLs
            thumbnails = image.get('thumbnails', {})
            image_url = image.get('image', '')
            
            # Prefer 500px thumbnail, fall back to other sizes
            thumbnail_url = (
                thumbnails.get('500') or 
                thumbnails.get('large') or 
                thumbnails.get('small') or 
                image_url
            )
            
            # Determine if this is a front cover
            types = image.get('types', [])
            is_front = 'Front' in types
            
            # Extract dimensions if available
            width = None
            height = None
            if 'width' in image and 'height' in image:
                width = image['width']
                height = image['height']
            
            processed = {
                'image_url': image_url,
                'thumbnail_url': thumbnail_url,
                'is_front': is_front,
                'types': types,
                'width': width,
                'height': height,
                'comment': image.get('comment', ''),
                'approved': image.get('approved', False)
            }
            
            return processed
            
        except Exception as e:
            logger.warning(f"Error processing artwork image: {e}")
            return None
    
    def download_artwork(self, url: str, timeout: int = 30) -> Optional[bytes]:
        """
        Download artwork from a URL.
        
        Args:
            url: Image URL to download
            timeout: Request timeout in seconds
            
        Returns:
            Image data as bytes or None if download failed
        """
        try:
            self._rate_limit_delay()
            
            logger.debug(f"Downloading artwork from: {url}")
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Invalid content type for artwork: {content_type}")
                return None
            
            # Download with size limit (10MB max)
            content = b''
            max_size = 10 * 1024 * 1024  # 10MB
            
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > max_size:
                    logger.warning(f"Artwork too large, stopping download: {url}")
                    return None
            
            logger.info(f"Downloaded artwork: {len(content)} bytes from {url}")
            return content
            
        except requests.RequestException as e:
            logger.error(f"Error downloading artwork from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading artwork: {e}")
            return None
    
    def search_and_get_artwork(self, artist: str, album: str = None, title: str = None) -> List[Dict]:
        """
        Combined search and artwork retrieval.
        
        Args:
            artist: Artist name (required)
            album: Album name (optional)
            title: Track title (optional)
            
        Returns:
            List of releases with artwork URLs populated
        """
        releases = self.search_release(artist, album, title)
        
        for release in releases:
            try:
                artwork_urls = self.get_artwork_urls(release['id'])
                release['artwork_urls'] = artwork_urls
            except Exception as e:
                logger.warning(f"Error getting artwork for release {release['id']}: {e}")
                release['artwork_urls'] = []
        
        return releases 