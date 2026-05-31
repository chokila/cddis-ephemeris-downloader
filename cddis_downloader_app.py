#!/usr/bin/env python3
"""
CDDIS Ephemeris File Downloader
Flask backend for downloading GNSS ephemeris products from NASA CDDIS
Fixed version using GPS week and day of week path structure
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import os
import gzip
import shutil
from pathlib import Path
import re
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CDDIS_BASE_URL = "https://cddis.nasa.gov/archive/gnss/products"
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# GPS epoch for week calculation
GPS_EPOCH = datetime(1980, 1, 6)

# Product type configurations - UPDATED with actual CDDIS products
PRODUCT_TYPES = {
    "COD0MGXFIN_ORB": {
        "pattern": "COD0MGXFIN_{date}_01D_05M_ORB.SP3.gz",
        "description": "CODE Final Orbit (5 minute)"
    },
    "COD0MGXFIN_ERP": {
        "pattern": "COD0MGXFIN_{date}_01D_12H_ERP.ERP.gz",
        "description": "CODE Final ERP (12 hour)"
    },
    "COD0MGXFIN_CLK": {
        "pattern": "COD0MGXFIN_{date}_01D_30S_CLK.CLK.gz",
        "description": "CODE Final Clock (30 second)"
    },
    "IGS0OPSFIN_CLK": {
        "pattern": "IGS0OPSFIN_{date}_01D_30S_CLK.CLK.gz",
        "description": "IGS Final Clock (30 second)"
    },
    "IGS0OPSFIN_ORB": {
        "pattern": "IGS0OPSFIN_{date}_01D_15M_ORB.SP3.gz",
        "description": "IGS Final Orbit (15 minute)"
    },
    "IGS0DEMFIN_ORB": {
        "pattern": "IGS0DEMFIN_{date}_01D_05M_ORB.SP3.gz",
        "description": "IGS DEMO Orbit (5 minute)"
    },
    "IGS0DEMFIN_CLK": {
        "pattern": "IGS0DEMFIN_{date}_01D_30S_CLK.CLK.gz",
        "description": "IGS DEMO Clock (30 second)"
    }
}


def date_to_doy_string(date_obj):
    """Convert datetime to GNSS filename format YYYYDDD0000"""
    doy = date_obj.timetuple().tm_yday
    return f"{date_obj.year}{doy:03d}0000"


def get_gps_week_day(date_obj):
    """Convert datetime to GPS week and day of week
    
    GPS week starts on Sunday (day 0)
    Returns: (gps_week, day_of_week)
    """
    try:
        days_since_epoch = (date_obj.date() - GPS_EPOCH.date()).days
        gps_week = days_since_epoch // 7
        day_of_week = days_since_epoch % 7
        return gps_week, day_of_week
    except Exception as e:
        logger.error(f"Error calculating GPS week: {str(e)}")
        return None, None


def get_doy(date_obj):
    """Get day of year"""
    return date_obj.timetuple().tm_yday


def check_file_availability(date_str, username, password):
    """Check if files are available for a specific date"""
    try:
        # Parse date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Get GPS week, day of week, and DOY
        gps_week, day_of_week = get_gps_week_day(date_obj)
        doy = get_doy(date_obj)
        doy_string = date_to_doy_string(date_obj)
        
        if gps_week is None or day_of_week is None:
            return {"success": False, "error": "Error calculating GPS week"}
        
        # Build directory path using GPS week and day of week
        dir_path = f"{CDDIS_BASE_URL}/{gps_week}/"
        
        
        logger.info(f"========== FILE AVAILABILITY CHECK ==========")
        logger.info(f"Date: {date_obj.strftime('%Y-%m-%d')}")
        logger.info(f"GPS Week: {gps_week}, Day of Week: {day_of_week}")
        logger.info(f"DOY: {doy}")
        logger.info(f"Filename DOY String: {doy_string}")
        logger.info(f"Directory Path: {dir_path}")
        logger.info(f"===========================================")
        
        available_files = []
        
        # Check each product type
        for product_key, product_info in PRODUCT_TYPES.items():
            # Construct expected filename
            filename = product_info["pattern"].replace("{date}", doy_string)
            file_url = dir_path + filename
            
            logger.info(f"\nChecking: {product_key}")
            logger.info(f"  Filename: {filename}")
            logger.info(f"  URL: {file_url}")
            
            try:
                # Try HEAD request first
                logger.info(f"  Attempting HEAD request...")
                head_response = requests.head(
                    file_url,
                    auth=HTTPBasicAuth(username, password),
                    timeout=15,
                    verify=False,
                    allow_redirects=True
                )
                
                logger.info(f"  HEAD Status: {head_response.status_code}")
                
                if head_response.status_code == 401:
                    return {"success": False, "error": "Authentication failed. Invalid credentials."}
                
                if head_response.status_code == 200:
                    # File exists!
                    file_size = head_response.headers.get('Content-Length', 'Unknown')
                    if file_size != 'Unknown':
                        try:
                            file_size_mb = int(file_size) / (1024*1024)
                            file_size_str = f"{file_size_mb:.2f} MB"
                        except:
                            file_size_str = "Unknown"
                    else:
                        file_size_str = "Unknown"
                    
                    available_files.append({
                        "product": product_key,
                        "filename": filename,
                        "description": product_info["description"],
                        "url": file_url,
                        "size": file_size_str
                    })
                    logger.info(f"  ✓ FOUND: {filename} (Size: {file_size_str})")
                    
                elif head_response.status_code == 404:
                    logger.info(f"  ✗ NOT FOUND (404): {filename}")
                    
                else:
                    # Try GET request as fallback
                    logger.info(f"  HEAD returned {head_response.status_code}, trying GET...")
                    try:
                        get_response = requests.get(
                            file_url,
                            auth=HTTPBasicAuth(username, password),
                            timeout=15,
                            stream=True,
                            verify=False,
                            allow_redirects=True
                        )
                        
                        logger.info(f"  GET Status: {get_response.status_code}")
                        
                        if get_response.status_code == 200:
                            file_size = get_response.headers.get('Content-Length', 'Unknown')
                            if file_size != 'Unknown':
                                try:
                                    file_size_mb = int(file_size) / (1024*1024)
                                    file_size_str = f"{file_size_mb:.2f} MB"
                                except:
                                    file_size_str = "Unknown"
                            else:
                                file_size_str = "Unknown"
                            
                            available_files.append({
                                "product": product_key,
                                "filename": filename,
                                "description": product_info["description"],
                                "url": file_url,
                                "size": file_size_str
                            })
                            logger.info(f"  ✓ FOUND via GET: {filename} (Size: {file_size_str})")
                        else:
                            logger.info(f"  ✗ GET also failed: {filename} (Status: {get_response.status_code})")
                            
                    except Exception as get_e:
                        logger.warning(f"  GET request error: {str(get_e)}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"  ⏱ TIMEOUT: {filename}")
            except requests.exceptions.ConnectionError as ce:
                logger.error(f"  🔗 CONNECTION ERROR: {str(ce)}")
                return {"success": False, "error": f"Cannot connect to CDDIS server: {str(ce)}"}
            except Exception as e:
                logger.warning(f"  ❌ ERROR: {str(e)}")
        
        logger.info(f"\n========== RESULTS ==========")
        logger.info(f"Total files found: {len(available_files)}")
        logger.info(f"=============================\n")
        
        return {
            "success": True,
            "date": date_str,
            "gps_week": gps_week,
            "day_of_week": day_of_week,
            "doy": doy,
            "doy_string": doy_string,
            "directory": dir_path,
            "files": available_files,
            "file_count": len(available_files)
        }
        
    except Exception as e:
        logger.error(f"Error checking availability: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Error: {str(e)}"}


def check_date_range_availability(start_date_str, end_date_str, username, password):
    """Check file availability for a date range"""
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        if end_date < start_date:
            return {"success": False, "error": "End date must be after start date"}
        
        if (end_date - start_date).days > 365:
            return {"success": False, "error": "Date range cannot exceed 365 days"}
        
        all_files = {}
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            result = check_file_availability(date_str, username, password)
            
            if result["success"] and result["files"]:
                all_files[date_str] = result["files"]
                logger.info(f"Found {len(result['files'])} files for {date_str}")
            
            current_date += timedelta(days=1)
        
        return {
            "success": True,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "dates_with_files": all_files,
            "total_dates": len(all_files)
        }
        
    except Exception as e:
        logger.error(f"Error checking date range: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Error: {str(e)}"}


@app.route('/')
def index():
    """Serve the main HTML interface"""
    return render_template('index.html')


@app.route('/api/check-availability', methods=['POST'])
def api_check_availability():
    """API endpoint to check file availability"""
    data = request.json
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"})
    
    logger.info(f"\n*** NEW AVAILABILITY CHECK REQUEST ***")
    logger.info(f"User: {username}")
    
    try:
        if data.get('mode') == 'single':
            date = data.get('date')
            if not date:
                return jsonify({"success": False, "error": "Date required"})
            logger.info(f"Mode: Single date - {date}")
            result = check_file_availability(date, username, password)
        else:
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            if not start_date or not end_date:
                return jsonify({"success": False, "error": "Start and end dates required"})
            logger.info(f"Mode: Date range - {start_date} to {end_date}")
            result = check_date_range_availability(start_date, end_date, username, password)
        
        if result.get('success'):
            if data.get('mode') == 'single':
                logger.info(f"✓ Search completed: Found {result.get('file_count', 0)} files")
            else:
                logger.info(f"✓ Search completed: Found files for {result.get('total_dates', 0)} dates")
        else:
            logger.warning(f"✗ Search failed: {result.get('error', 'Unknown error')}")
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"API Error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Server error: {str(e)}"})


@app.route('/api/download', methods=['POST'])
def api_download():
    """API endpoint to download a file"""
    try:
        data = request.json
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        file_url = data.get('url')
        filename = data.get('filename')
        
        if not all([username, password, file_url, filename]):
            return jsonify({"success": False, "error": "Missing required parameters"})
        
        logger.info(f"\n*** FILE DOWNLOAD STARTED ***")
        logger.info(f"Filename: {filename}")
        logger.info(f"URL: {file_url}")
        
        try:
            response = requests.get(
                file_url,
                auth=HTTPBasicAuth(username, password),
                timeout=120,
                stream=True,
                verify=False
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 401:
                logger.error("Authentication failed")
                return jsonify({"success": False, "error": "Authentication failed"})
            
            if response.status_code != 200:
                logger.error(f"Download failed with status {response.status_code}")
                return jsonify({
                    "success": False,
                    "error": f"Download failed. Status: {response.status_code}"
                })
            
            # Save the file
            file_path = DOWNLOAD_DIR / filename
            total_size = 0
            
            logger.info(f"Saving to: {file_path}")
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            file_size_mb = total_size / (1024 * 1024)
            logger.info(f"✓ File saved successfully: {file_path}")
            logger.info(f"  Size: {file_size_mb:.2f} MB")
            
            return jsonify({
                "success": True,
                "message": f"File downloaded successfully ({file_size_mb:.2f} MB)",
                "filename": filename,
                "path": str(file_path),
                "size": f"{file_size_mb:.2f} MB"
            })
        
        except requests.exceptions.Timeout:
            logger.error(f"Download timeout: {filename}")
            return jsonify({"success": False, "error": "Download timeout. File too large or server too slow."})
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"Connection error: {str(ce)}")
            return jsonify({"success": False, "error": f"Connection error: {str(ce)}"})
        except Exception as e:
            logger.error(f"Download error: {str(e)}", exc_info=True)
            return jsonify({"success": False, "error": f"Error: {str(e)}"})
            
    except Exception as e:
        logger.error(f"API Download Error: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Server error: {str(e)}"})


@app.route('/api/downloads-list', methods=['GET'])
def api_downloads_list():
    """Get list of downloaded files"""
    try:
        files = []
        if DOWNLOAD_DIR.exists():
            for file in DOWNLOAD_DIR.iterdir():
                if file.is_file():
                    files.append({
                        "name": file.name,
                        "size": file.stat().st_size,
                        "modified": file.stat().st_mtime
                    })
        
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
