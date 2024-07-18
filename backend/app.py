from flask import Flask, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from sqlalchemy.ext.hybrid import hybrid_property
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
import folium

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@granby.kbs.msu.edu/metadata"
db = SQLAlchemy(app)

# Define the Site model with geometry column
class Site(db.Model):
    __tablename__ = 'site'
    __table_args__ = {'schema': 'test'}  # Adjust schema name if necessary

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    geometry = db.Column(Geometry('POINT', srid=4326))  # Assuming POINT geometry with SRID 4326

    @hybrid_property
    def latitude(self):
        if self.geometry:
            point = to_shape(self.geometry)
            return point.y  # Latitude
        return None

    @hybrid_property
    def longitude(self):
        if self.geometry:
            point = to_shape(self.geometry)
            return point.x  # Longitude
        return None

    def __repr__(self):
        return f"<Site(id={self.id}, name={self.name}, geometry={self.geometry})>"

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

@app.route('/data', methods=['GET'])
def get_data():
    try:
        sites = Site.query.all()
        if sites:
            return jsonify([{
                'id': site.id,
                'name': site.name,
                'longitude': site.longitude,
                'latitude': site.latitude
            } for site in sites])
        else:
            return jsonify({"message": "No data found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/map', methods=['GET'])
def map_view():
    sites = Site.query.all()
    map_center = [0, 0]  # Default map center
    site_coords = []

    if sites:
        # Get the coordinates of the first site to center the map
        first_site = sites[0]
        map_center = [first_site.latitude, first_site.longitude]

        # Collect site coordinates
        for site in sites:
            if site.latitude and site.longitude:
                site_coords.append((site.latitude, site.longitude, site.name))

    # Create a Folium map
    m = folium.Map(location=map_center, zoom_start=2)

    # Add markers to the map
    for lat, lon, name in site_coords:
        folium.Marker(
            location=[lat, lon],
            popup=name,
            icon=folium.Icon(icon="info-sign")
        ).add_to(m)

    # Generate the map HTML
    map_html = m._repr_html_()

    # Render the map in a simple HTML template
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Site Map</title>
        </head>
        <body>
            <h1>Site Map</h1>
            {{ map_html|safe }}
        </body>
        </html>
    """, map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

