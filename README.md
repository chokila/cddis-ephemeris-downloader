# 📡 CDDIS Ephemeris File Downloader

A modern web application for easily downloading GNSS ephemeris products from NASA's CDDIS (Crustal Dynamics Data Information System) archive.

## Features

✅ **Multiple Search Options**
- Search by single date
- Search by date range
- Real-time file availability checking

✅ **Supported Products**
- CODE Final Orbit (COD0MGXFIN ORB) - 5 minute resolution
- CODE Final ERP (COD0MGXFIN ERP) - 12 hour resolution
- CODE Final Clock (COD0MGXFIN CLK) - 30 second resolution
- IGS Final Clock (IGS0OPSFIN CLK) - 30 second resolution
- IGS Final Orbit (IGS0OPSFIN ORB) - 15 minute resolution

✅ **User-Friendly Interface**
- Clean, modern design
- Real-time search feedback
- Individual file download buttons
- Download status tracking
- Authentication support

## Requirements

- Python 3.8+
- pip (Python package installer)
- Internet connection with access to CDDIS server
- CDDIS account (free registration at https://cddis.nasa.gov/)

## Installation

### 1. Clone or Download Files

Make sure you have the following files:
```
cddis_downloader_app.py
templates/index.html
requirements.txt
```

### 2. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

### Start the Flask Server

```bash
# Windows
python cddis_downloader_app.py

# macOS/Linux
python3 cddis_downloader_app.py
```

You should see output like:
```
 * Serving Flask app 'cddis_downloader_app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### Open in Browser

1. Open your web browser (Chrome, Firefox, Safari, Edge, etc.)
2. Navigate to: `http://localhost:5000`
3. The application interface will load

## Usage Guide

### Step 1: Enter Credentials

1. Enter your CDDIS username and password
2. If you don't have an account, register at https://cddis.nasa.gov/

### Step 2: Select Search Mode

**Option A: Single Date**
1. Select "Single Date" radio button
2. Pick a date from the calendar
3. Click "Check Availability"

**Option B: Date Range**
1. Select "Date Range" radio button
2. Pick start and end dates
3. Click "Check Availability"
   - Maximum range: 365 days
   - All dates with available files will be shown

### Step 3: View Available Files

The application will:
- Display all available files for the selected date(s)
- Show file descriptions
- Indicate product types and resolutions
- Display statistics (number of files, dates, etc.)

### Step 4: Download Files

1. Click the "⬇ Download" button next to each file
2. The file will be downloaded to the `downloads/` directory
3. Status message confirms successful download
4. Button changes to "✓ Downloaded" when complete

## File Name Format

Files follow the naming pattern:
```
PRODUCT_DATE_RESOLUTION_TYPE.EXTENSION.gz

Examples:
- COD0MGXFIN_20261270000_01D_05M_ORB.SP3.gz
- IGS0OPSFIN_20261270000_01D_15M_ORB.SP3.gz
```

Where:
- `DATE`: Format is YYYYDDDHHMMSS (Year, Day of Year, Hour, Minute, Second)
- `01D`: 1 day data span
- `05M`, `12H`, `30S`: Time resolution
- Files are gzip compressed (.gz)

## Downloaded Files Location

Downloaded files are saved in:
```
./downloads/
```

To access them:
1. Navigate to the application directory
2. Open the `downloads` folder
3. Files are stored as-is (compressed .gz format)

## Decompressing Files

To decompress the downloaded files:

### On Windows
- Use 7-Zip, WinRAR, or other extraction tools
- Right-click > Extract

### On macOS/Linux
```bash
# Extract single file
gunzip filename.gz

# Extract all files in directory
gunzip downloads/*.gz
```

## Supported Products and Resolutions

| Product | Type | Resolution | Description |
|---------|------|-----------|-------------|
| CODE | ORB | 5 minute | Final orbit product |
| CODE | ERP | 12 hour | Earth rotation parameters |
| CODE | CLK | 30 second | Clock corrections |
| IGS | ORB | 15 minute | Final orbit product |
| IGS | CLK | 30 second | Clock corrections |

## Data Directory Structure at CDDIS

The application accesses files at:
```
https://cddis.nasa.gov/archive/gnss/products/{YEAR}/{DOY}/
```

Where:
- `YEAR`: 4-digit year (e.g., 2026)
- `DOY`: 3-digit day of year (001-366)

## Troubleshooting

### Authentication Failed
- Verify username and password are correct
- Check CDDIS website for account status
- Ensure no extra spaces in credentials

### No Files Found
- Check if the date is within the CDDIS archive range
- Try nearby dates
- Files may not be available for all dates

### Download Fails
- Check internet connection
- Verify CDDIS server is accessible
- Try downloading again after a few moments
- Check available disk space

### Port Already in Use
If port 5000 is in use, modify the last line of `cddis_downloader_app.py`:
```python
# Change port from 5000 to another (e.g., 8000)
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)
```

## Advanced Usage

### Batch Download Scripts

To automate downloads, create a Python script:

```python
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

username = "your_username"
password = "your_password"
base_url = "https://cddis.nasa.gov/archive/gnss/products"

# Download files for a specific date range
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 1, 31)

current = start_date
while current <= end_date:
    year = current.year
    doy = current.timetuple().tm_yday
    
    filename = f"COD0MGXFIN_{year}{doy:03d}0000_01D_05M_ORB.SP3.gz"
    url = f"{base_url}/{year}/{doy:03d}/{filename}"
    
    response = requests.get(url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        with open(f"downloads/{filename}", "wb") as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
    
    current += timedelta(days=1)
```

## Security Notes

- Credentials are only sent to CDDIS server (https)
- Credentials are NOT stored locally
- Use strong passwords
- Close browser/application when finished

## System Requirements

| Component | Requirement |
|-----------|------------|
| Memory | 512 MB minimum |
| Disk Space | Depends on file downloads (typically 10-50 MB per file) |
| Internet | Stable connection recommended |
| Browser | Any modern browser (Chrome, Firefox, Safari, Edge) |

## Performance Tips

1. **Single Date Queries**: Faster and recommended for one-time downloads
2. **Date Ranges**: May take longer for ranges > 30 days
3. **Off-peak Downloads**: Download during off-peak hours for better speed
4. **Batch Processing**: Use scripting for large automated downloads

## File Sizes (Approximate)

- Orbit files (SP3): 10-15 MB (compressed)
- Clock files (CLK): 2-5 MB (compressed)
- ERP files (ERP): 1-2 MB (compressed)

Uncompressed files are typically 3-4x larger.

## Support and Documentation

- **CDDIS Documentation**: https://cddis.nasa.gov/
- **GNSS Products Info**: https://cddis.nasa.gov/products/
- **Code Analysis Center**: https://www.aiub.unibe.ch/

## License

This application is provided as-is for educational and research purposes.

## Version

Version: 1.0.0
Last Updated: 2026

---

**Happy downloading! 📡🛰️**
